"""Parse local text and Markdown uploads for the knowledge base."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO, TextIO

from .document_ingestion import RawPage, ingest_pages
from .preprocessing import clean_text

if TYPE_CHECKING:
    from ..models import Document
    from .embedding_generation import EmbeddingGenerator

MAX_TEXT_FILE_BYTES = 10 * 1024 * 1024
SUPPORTED_TEXT_SUFFIXES = {".md", ".txt"}


def parse_text_upload(upload: BinaryIO | TextIO, filename: str) -> list[RawPage]:
    """Parse a UTF-8 text or Markdown upload into a single page."""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_TEXT_SUFFIXES:
        raise ValueError(f"Unsupported text file type: {suffix or '(no extension)'}")

    content = upload.read(MAX_TEXT_FILE_BYTES + 1)
    if isinstance(content, str):
        encoded = content.encode("utf-8")
        text = content
    elif isinstance(content, bytes):
        encoded = content
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ValueError(f"{filename} must use UTF-8 encoding.") from error
    else:
        raise TypeError("The uploaded file must provide text or bytes.")

    if len(encoded) > MAX_TEXT_FILE_BYTES:
        raise ValueError(f"{filename} exceeds the {MAX_TEXT_FILE_BYTES}-byte text-file limit.")

    return [RawPage(clean_text(text))]


def ingest_text_upload(
    upload: BinaryIO | TextIO,
    filename: str,
    title: str | None = None,
    state: str = "",
    edition: str = "",
    embedder: EmbeddingGenerator | None = None,
) -> Document:
    """Parse and ingest a UTF-8 text or Markdown upload."""
    path = Path(filename)
    document_title = title or path.stem.replace("_", " ").replace("-", " ")
    source_path = f"upload:{path.name}"
    return ingest_pages(
        parse_text_upload(upload, filename),
        title=document_title,
        source_path=source_path,
        state=state,
        edition=edition,
        embedder=embedder,
    )


def ingest_text_file(
    path: Path,
    title: str | None = None,
    state: str = "",
    edition: str = "",
    embedder: EmbeddingGenerator | None = None,
) -> Document:
    """Read and ingest a local UTF-8 text or Markdown file."""
    path = Path(path)
    with path.open("rb") as upload:
        pages = parse_text_upload(upload, path.name)

    document_title = title or path.stem.replace("_", " ").replace("-", " ")
    return ingest_pages(
        pages,
        title=document_title,
        source_path=str(path.resolve()),
        state=state,
        edition=edition,
        embedder=embedder,
    )
