"""Load driver's manual PDFs into Document + Chunk rows so the chatbot can search them."""

from dataclasses import dataclass
from pathlib import Path

from django.db import transaction


@dataclass
class RawPage:
    text: str
    page_number: int | None = None


def read_pdf(path: Path) -> list[RawPage]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return [RawPage(page.extract_text() or "", index + 1) for index, page in enumerate(reader.pages)]


def ingest_pages(pages: list[RawPage], title: str, source_path: str = "", state: str = "",
                 edition: str = "", embedder=None):
    """Chunk, embed, and save pages as one Document. Replaces any document with the same source_path."""
    from ..models import Chunk, Document
    from .embedding_generation import get_embedder
    from .preprocessing import chunk_pages

    text_chunks = chunk_pages(pages)
    if not text_chunks:
        raise ValueError(f"No usable text found in {title}. Is it a scanned PDF?")

    embedder = embedder or get_embedder()
    vectors = embedder.embed_documents([chunk.text for chunk in text_chunks])

    with transaction.atomic():
        if source_path:
            Document.objects.filter(source_path=source_path).delete()
        document = Document.objects.create(title=title, state=state, edition=edition,
                                           source_path=source_path)
        Chunk.objects.bulk_create([
            Chunk(document=document, position=i, page=c.page, text=c.text, embedding=vector)
            for i, (c, vector) in enumerate(zip(text_chunks, vectors))
        ])
    return document


def ingest_pdf(path: Path, title: str | None = None, state: str = "", edition: str = "", embedder=None):
    path = Path(path)
    return ingest_pages(read_pdf(path), title=title or path.stem.replace("_", " ").replace("-", " "),
                        source_path=str(path), state=state, edition=edition, embedder=embedder)
