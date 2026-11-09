"""Split document text into overlapping chunks that can be embedded and retrieved."""

from dataclasses import dataclass

from .document_ingestion import RawPage

CHUNK_WORDS = 220
OVERLAP_WORDS = 40


@dataclass
class TextChunk:
    text: str
    page: int | None


def chunk_pages(pages: list[RawPage], chunk_words: int = CHUNK_WORDS,
                overlap_words: int = OVERLAP_WORDS) -> list[TextChunk]:
    """Split pages into ~chunk_words windows that overlap by overlap_words.

    Each chunk remembers the page it starts on so the prompt can label it.
    """
    chunks: list[TextChunk] = []
    words: list[str] = []
    fresh = 0  # words added since the last emitted chunk
    start_page: int | None = None

    for page in pages:
        page_words = page.text.split()
        if not words:
            start_page = page.page_number
        for word in page_words:
            words.append(word)
            fresh += 1
            if len(words) >= chunk_words:
                chunks.append(TextChunk(" ".join(words), start_page))
                words = words[chunk_words - overlap_words:]
                fresh = 0
                start_page = page.page_number

    if fresh and len(words) >= 15:
        chunks.append(TextChunk(" ".join(words), start_page))
    return chunks
