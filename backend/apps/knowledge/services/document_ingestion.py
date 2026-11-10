"""Load local PDF documents into Document and Chunk rows."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from ..models import Document
    from .embedding_generation import EmbeddingGenerator


@dataclass
class RawPage:
    """Extracted text and its optional source page number."""

    text: str
    page_number: int | None = None


def read_pdf(path: Path) -> list[RawPage]:
    """Extract text from each page in a local PDF."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return [RawPage(page.extract_text() or "", index + 1) for index, page in enumerate(reader.pages)]


def ingest_pages(
    pages: list[RawPage],
    title: str,
    source_path: str = "",
    state: str = "",
    edition: str = "",
    embedder: "EmbeddingGenerator | None" = None,
) -> "Document":
    """Clean, chunk, embed, and save pages as one document."""
    from ..models import Chunk, Document
    from .embedding_generation import get_embedder
    from .preprocessing import chunk_pages

    text_chunks = chunk_pages(pages)
    if not text_chunks:
        raise ValueError(f"No usable text found in {title}.")

    embedder = embedder or get_embedder()
    vectors = embedder.embed_documents([chunk.text for chunk in text_chunks])
    if len(vectors) != len(text_chunks):
        raise RuntimeError("The embedding provider returned an unexpected number of vectors.")

    with transaction.atomic():
        if source_path:
            Document.objects.filter(source_path=source_path).delete()
        document = Document.objects.create(title=title, state=state, edition=edition,
                                           source_path=source_path)
        Chunk.objects.bulk_create(
            [
                Chunk(document=document, position=i, page=chunk.page, text=chunk.text, embedding=vector)
                for i, (chunk, vector) in enumerate(zip(text_chunks, vectors))
            ]
        )
    return document


def ingest_pdf(
    path: Path,
    title: str | None = None,
    state: str = "",
    edition: str = "",
    embedder: "EmbeddingGenerator | None" = None,
) -> "Document":
    """Ingest a local PDF, replacing an existing document at the same path."""
    path = Path(path)
    document_title = title or path.stem.replace("_", " ").replace("-", " ")
    return ingest_pages(
        read_pdf(path),
        title=document_title,
        source_path=str(path.resolve()),
        state=state,
        edition=edition,
        embedder=embedder,
    )
