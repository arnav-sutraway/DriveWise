from email.message import Message
from urllib.error import HTTPError

import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.knowledge.services import web_ingestion
from apps.knowledge.services.document_ingestion import RawPage
from apps.knowledge.services.web_ingestion import (
    WebPage,
    extract_html_text,
    fetch_web_page,
    ingest_web_url,
)

URL = "https://manuals.example.org/rules"
ALLOWED_HOSTS = ["manuals.example.org"]
PUBLIC_DNS_RESULT = (None, None, None, None, ("8.8.8.8", 443))


class FakeResponse:
    def __init__(self, body, content_type="text/html; charset=utf-8", content_length=None):
        self._body = body
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, size=-1):
        return self._body[:size] if size >= 0 else self._body


def allow_public_dns(monkeypatch):
    monkeypatch.setattr(
        web_ingestion.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [PUBLIC_DNS_RESULT],
    )


def test_extract_html_text_uses_title_and_skips_non_content():
    title, text = extract_html_text(
        "<html><head><title> Traffic&nbsp;Rules </title>"
        "<style>.hidden { display:none }</style></head>"
        "<body><nav>Navigation</nav><main><h1>Stop</h1>"
        "<p>Yield to pedestrians.</p><script>ignore()</script></main></body></html>"
    )

    assert title == "Traffic Rules"
    assert text == "Stop\n\nYield to pedestrians."
    assert "Navigation" not in text
    assert "ignore" not in text


def test_fetch_web_page_parses_html_and_uses_allowlisted_host(monkeypatch):
    allow_public_dns(monkeypatch)
    monkeypatch.setattr(
        web_ingestion,
        "_open_url",
        lambda url, timeout: FakeResponse(
            b"<html><title>Driver Guide</title><p>Stop and yield to pedestrians.</p></html>"
        ),
    )

    page = fetch_web_page(URL, ALLOWED_HOSTS)

    assert page == WebPage(URL, "Driver Guide", "Stop and yield to pedestrians.")


def test_fetch_web_page_extracts_text_from_json(monkeypatch):
    allow_public_dns(monkeypatch)
    monkeypatch.setattr(
        web_ingestion,
        "_open_url",
        lambda url, timeout: FakeResponse(
            b'{"title":"Right of way","items":[{"text":"Yield to the driver on your right."}]}',
            "application/json",
        ),
    )

    page = fetch_web_page(URL, ALLOWED_HOSTS)

    assert page.title == "rules"
    assert page.text == "Right of way\nYield to the driver on your right."


def test_fetch_web_page_rejects_unallowlisted_host_before_resolving(monkeypatch):
    monkeypatch.setattr(
        web_ingestion.socket,
        "getaddrinfo",
        lambda *args, **kwargs: pytest.fail("unallowlisted host must not be resolved"),
    )

    with pytest.raises(ValueError, match="not in the ingestion allowlist"):
        fetch_web_page(URL, ["other.example.org"])


def test_fetch_web_page_requires_an_allowlist():
    with pytest.raises(ImproperlyConfigured, match="KNOWLEDGE_ALLOWED_HOSTS"):
        fetch_web_page(URL, [])


def test_fetch_web_page_rejects_private_dns_results(monkeypatch):
    monkeypatch.setattr(
        web_ingestion.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("127.0.0.1", 443))],
    )

    with pytest.raises(ValueError, match="non-public IP"):
        fetch_web_page(URL, ALLOWED_HOSTS)


@pytest.mark.parametrize(
    "url",
    [
        "http://manuals.example.org/rules",
        "https://user@manuals.example.org/rules",
        "https://manuals.example.org:444/rules",
    ],
)
def test_fetch_web_page_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        fetch_web_page(url, ALLOWED_HOSTS)


def test_fetch_web_page_rejects_redirects(monkeypatch):
    allow_public_dns(monkeypatch)
    redirect = HTTPError(URL, 302, "Found", {}, None)

    def raise_redirect(*args):
        raise redirect

    monkeypatch.setattr(web_ingestion, "_open_url", raise_redirect)

    with pytest.raises(ValueError, match="Redirects are not followed"):
        fetch_web_page(URL, ALLOWED_HOSTS)


def test_fetch_web_page_rejects_oversized_content(monkeypatch):
    allow_public_dns(monkeypatch)
    monkeypatch.setattr(
        web_ingestion,
        "_open_url",
        lambda *args: FakeResponse(b"12345", "text/plain", content_length=5),
    )

    with pytest.raises(ValueError, match="exceeds the 4-byte limit"):
        fetch_web_page(URL, ALLOWED_HOSTS, max_bytes=4)


def test_fetch_web_page_enforces_limit_when_content_length_is_missing(monkeypatch):
    allow_public_dns(monkeypatch)
    monkeypatch.setattr(
        web_ingestion,
        "_open_url",
        lambda *args: FakeResponse(b"12345", "text/plain"),
    )

    with pytest.raises(ValueError, match="exceeds the 4-byte limit"):
        fetch_web_page(URL, ALLOWED_HOSTS, max_bytes=4)


def test_fetch_web_page_rejects_unsupported_content_type(monkeypatch):
    allow_public_dns(monkeypatch)
    monkeypatch.setattr(
        web_ingestion,
        "_open_url",
        lambda *args: FakeResponse(b"binary", "application/octet-stream"),
    )

    with pytest.raises(ValueError, match="Unsupported response content type"):
        fetch_web_page(URL, ALLOWED_HOSTS)


def test_ingest_web_url_passes_clean_page_and_metadata_to_pipeline(monkeypatch):
    captured = {}

    def fake_ingest_pages(pages, **kwargs):
        captured["pages"] = pages
        captured.update(kwargs)
        return "saved document"

    monkeypatch.setattr(web_ingestion, "fetch_web_page", lambda *args: WebPage(URL, "Manual", "Yield safely."))
    monkeypatch.setattr(web_ingestion, "ingest_pages", fake_ingest_pages)

    result = ingest_web_url(URL, ALLOWED_HOSTS, state="Georgia", edition="2026")

    assert result == "saved document"
    assert captured["pages"] == [RawPage("Yield safely.")]
    assert captured["title"] == "Manual"
    assert captured["source_path"] == URL
    assert captured["state"] == "Georgia"
    assert captured["edition"] == "2026"
