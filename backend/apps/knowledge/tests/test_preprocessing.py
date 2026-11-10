import pytest

from apps.knowledge.services.document_ingestion import RawPage
from apps.knowledge.services.preprocessing import chunk_pages, clean_text


def test_clean_text_normalizes_unicode_entities_and_whitespace():
    assert clean_text("  Cafe\u0301&nbsp;\tguide\r\n\r\n\r\n\u0000Safe\u00adty  ") == (
        "Café guide\n\nSafety"
    )


def test_clean_text_removes_control_characters_and_preserves_paragraphs():
    assert clean_text("Yield\u0007 to the right.\n\nCheck for pedestrians.") == (
        "Yield to the right.\n\nCheck for pedestrians."
    )


def test_chunk_pages_cleans_text_before_chunking():
    source = "  ".join(["Stop\u0000", "before the line."] + [f"word{i}" for i in range(13)])
    chunks = chunk_pages([RawPage(source, 7)])

    assert len(chunks) == 1
    assert chunks[0].text == "Stop before the line. " + " ".join(f"word{i}" for i in range(13))
    assert chunks[0].page == 7


def test_clean_text_rejects_non_string_input():
    with pytest.raises(TypeError):
        clean_text(None)  # type: ignore[arg-type]
