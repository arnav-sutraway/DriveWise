"""Split document text into overlapping chunks that can be embedded and retrieved."""

import html
import re
import unicodedata
from dataclasses import dataclass

from .document_ingestion import RawPage

CHUNK_WORDS = 220
OVERLAP_WORDS = 40


def clean_text(text: str) -> str:
    """Normalize Unicode and whitespace and remove control characters."""
    normalized = unicodedata.normalize("NFKC", html.unescape(text))
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n").replace("\u00ad", "")
    normalized = "".join(
        character
        for character in normalized
        if character in "\n\t" or not unicodedata.category(character).startswith("C")
    )
    lines = [re.sub(r"[^\S\n]+", " ", line).strip() for line in normalized.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


@dataclass
class TextChunk:
    text: str
    page: int | None


def chunk_pages(
    pages: list[RawPage],
    chunk_words: int = CHUNK_WORDS,
    overlap_words: int = OVERLAP_WORDS,
) -> list[TextChunk]:
    """Split pages into ~chunk_words windows that overlap by overlap_words.

    Each chunk remembers the page it starts on so the prompt can label it.
    """
    chunks: list[TextChunk] = []
    words: list[str] = []
    fresh = 0  # words added since the last emitted chunk
    start_page: int | None = None

    for page in pages:
        page_words = clean_text(page.text).split()
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
