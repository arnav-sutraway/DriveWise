"""Turn cited passages into links: the local copy the coach read, plus the official original.

Official URLs live in data/manuals/source_links.json ({"<file name>": "https://..."}) and are
read when an answer is built, so adding or fixing a link needs no re-ingest. Documents ingested
from the web (`ingest_url`) already store their https URL as source_path.
"""

import json
import logging
from pathlib import Path

from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)

SOURCE_LINKS_FILE = "source_links.json"
LOCAL_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".md": "text/plain; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
}


def _official_links() -> dict[str, str]:
    path = Path(settings.KNOWLEDGE_DATA_DIR) / SOURCE_LINKS_FILE
    try:
        links = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as error:
        logger.warning("Could not read %s: %s", path, error)
        return {}
    return {name: url for name, url in links.items()
            if isinstance(name, str) and isinstance(url, str) and url.startswith("https://")}


def official_url(document, links: dict[str, str] | None = None) -> str:
    """The public original of a document, or "" when none is known."""
    if document.source_path.startswith("https://"):
        return document.source_path
    links = _official_links() if links is None else links
    return links.get(Path(document.source_path).name, "")


def local_file(document) -> Path | None:
    """The ingested file, only if it is a supported file inside the knowledge data folder."""
    if not document.source_path or document.source_path.startswith(("http://", "https://")):
        return None
    path = Path(document.source_path).resolve()
    data_dir = Path(settings.KNOWLEDGE_DATA_DIR).resolve()
    if path.suffix.lower() not in LOCAL_CONTENT_TYPES or not path.is_relative_to(data_dir):
        return None
    return path if path.is_file() else None


def describe_sources(retrieved, cited: list[int]) -> list[dict]:
    """One entry per cited passage number (1-based), in number order."""
    links = _official_links()
    sources = []
    for number in sorted(set(cited)):
        if not 1 <= number <= len(retrieved):
            continue
        chunk = retrieved[number - 1].chunk
        document = chunk.document
        official = official_url(document, links)
        url = official or None
        path = local_file(document)
        if path:
            url = reverse("document-file", args=[document.pk])
            if path.suffix.lower() == ".pdf" and chunk.page:
                url += f"#page={chunk.page}"  # Browser PDF viewers open at this page.
        sources.append({
            "number": number,
            "title": document.title,
            "page": chunk.page,
            "url": url,
            "official_url": official or None,
        })
    return sources
