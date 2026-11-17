"""Fetch and parse public HTTPS pages for knowledge-base ingestion."""

from __future__ import annotations

import ipaddress
import json
import socket
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from email.message import Message
from html.parser import HTMLParser
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from django.core.exceptions import ImproperlyConfigured

from .document_ingestion import RawPage, ingest_pages
from .preprocessing import clean_text

if TYPE_CHECKING:
    from ..models import Document
    from .embedding_generation import EmbeddingGenerator

MAX_RESPONSE_BYTES = 5 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 10
SUPPORTED_CONTENT_TYPES = {"application/json", "text/html", "text/plain"}
IGNORED_HTML_TAGS = {"aside", "button", "footer", "header", "nav", "noscript", "script", "style", "svg"}
BLOCK_HTML_TAGS = {
    "article",
    "br",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "li",
    "main",
    "p",
    "section",
}


@dataclass(frozen=True)
class WebPage:
    """Readable page text and its source metadata."""

    url: str
    title: str
    text: str


class _VisibleTextParser(HTMLParser):
    """Extract readable body text and the document title from HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._in_title = False
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in IGNORED_HTML_TAGS:
            self._ignored_depth += 1
        elif tag == "title":
            self._in_title = True
        elif not self._ignored_depth and tag in BLOCK_HTML_TAGS:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in IGNORED_HTML_TAGS and self._ignored_depth:
            self._ignored_depth -= 1
        elif tag == "title":
            self._in_title = False
        elif not self._ignored_depth and tag in BLOCK_HTML_TAGS:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        elif not self._ignored_depth:
            self.text_parts.append(data)


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(
        self,
        request: Request,
        file: object,
        code: int,
        message: str,
        headers: Message,
        new_url: str,
    ) -> None:
        return None


def _validate_url(url: str, allowed_hosts: Sequence[str]) -> str:
    """Validate an allowlisted HTTPS host and reject non-public DNS results."""
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("Only absolute HTTPS URLs can be ingested.")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Credentials and non-standard HTTPS ports are not allowed.")

    hostname = parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()
    permitted_hosts = {
        host.strip().rstrip(".").encode("idna").decode("ascii").lower()
        for host in allowed_hosts
        if host.strip()
    }
    if not permitted_hosts:
        raise ImproperlyConfigured(
            "Set KNOWLEDGE_ALLOWED_HOSTS to the HTTPS hosts permitted for ingestion."
        )
    if hostname not in permitted_hosts:
        raise ValueError(f"Host {hostname!r} is not in the ingestion allowlist.")

    addresses = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    if not addresses:
        raise ValueError(f"Host {hostname!r} did not resolve to an IP address.")
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0].split("%", 1)[0])
        if not ip.is_global:
            raise ValueError(f"Host {hostname!r} resolves to a non-public IP address.")
    return url


def _decode_response(body: bytes, content_type: str, charset: str | None) -> tuple[str, str]:
    """Decode HTML, plain text, or JSON response content."""
    if content_type not in SUPPORTED_CONTENT_TYPES:
        raise ValueError(f"Unsupported response content type: {content_type or '(missing)'}")
    try:
        decoded = body.decode(charset or "utf-8")
    except (LookupError, UnicodeDecodeError) as error:
        raise ValueError("The fetched page is not valid text in its declared encoding.") from error

    if content_type == "application/json":
        try:
            payload = json.loads(decoded)
        except json.JSONDecodeError as error:
            raise ValueError("The fetched API response is not valid JSON.") from error
        text_values = [value for value in _string_values(payload) if value.strip()]
        return "", clean_text("\n".join(text_values))
    if content_type == "text/html":
        return extract_html_text(decoded)
    return "", clean_text(decoded)


def _string_values(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _string_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _string_values(item)


def extract_html_text(html: str) -> tuple[str, str]:
    """Return a cleaned page title and visible text, excluding page chrome."""
    parser = _VisibleTextParser()
    parser.feed(html)
    parser.close()
    title = clean_text(" ".join(parser.title_parts))
    text = clean_text(" ".join(parser.text_parts))
    return title, text


def _open_url(url: str, timeout: float):
    request = Request(url, headers={"Accept": "text/html, text/plain, application/json"})
    return build_opener(ProxyHandler({}), _NoRedirectHandler()).open(request, timeout=timeout)


def fetch_web_page(
    url: str,
    allowed_hosts: Sequence[str],
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = MAX_RESPONSE_BYTES,
) -> WebPage:
    """Fetch one allowlisted public HTTPS page without following redirects."""
    if timeout <= 0:
        raise ValueError("The network timeout must be greater than zero.")
    if max_bytes <= 0:
        raise ValueError("The response size limit must be greater than zero.")
    _validate_url(url, allowed_hosts)

    try:
        with _open_url(url, timeout) as response:
            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                try:
                    declared_size = int(content_length)
                except ValueError as error:
                    raise ValueError("The fetched page has an invalid Content-Length.") from error
                if declared_size > max_bytes:
                    raise ValueError(f"The fetched page exceeds the {max_bytes}-byte limit.")

            body = response.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise ValueError(f"The fetched page exceeds the {max_bytes}-byte limit.")
            content_type = response.headers.get_content_type().lower()
            charset = response.headers.get_content_charset()
    except HTTPError as error:
        if 300 <= error.code < 400:
            raise ValueError("Redirects are not followed for web ingestion.") from error
        raise ValueError(f"Web ingestion returned HTTP {error.code}.") from error
    except URLError as error:
        raise ValueError(f"Could not fetch the web page: {error.reason}") from error

    title, text = _decode_response(body, content_type, charset)
    if not text:
        raise ValueError("The fetched page contains no readable text.")

    if not title:
        path_title = PurePosixPath(urlsplit(url).path).stem.replace("-", " ").replace("_", " ")
        title = path_title or urlsplit(url).hostname or url
    return WebPage(url=url, title=title, text=text)


def ingest_web_url(
    url: str,
    allowed_hosts: Sequence[str] | None = None,
    title: str | None = None,
    state: str = "",
    edition: str = "",
    embedder: EmbeddingGenerator | None = None,
) -> Document:
    """Fetch, preprocess, and store one allowlisted public web page."""
    if allowed_hosts is None:
        from django.conf import settings

        allowed_hosts = settings.KNOWLEDGE_ALLOWED_HOSTS
    page = fetch_web_page(url, allowed_hosts)
    return ingest_pages(
        [RawPage(page.text)],
        title=title or page.title,
        source_path=page.url,
        state=state,
        edition=edition,
        embedder=embedder,
    )
