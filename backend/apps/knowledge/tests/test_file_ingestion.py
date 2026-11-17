from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from apps.knowledge.services import file_ingestion
from apps.knowledge.services.document_ingestion import RawPage
from apps.knowledge.services.file_ingestion import ingest_text_upload, parse_text_upload


def test_parse_text_upload_decodes_bom_and_cleans_content():
    pages = parse_text_upload(
        BytesIO("\ufeff  Yield\u00a0to the right.\x00".encode("utf-8")),
        "right_of_way.TXT",
    )

    assert pages == [RawPage("Yield to the right.")]


def test_parse_text_upload_accepts_text_streams():
    pages = parse_text_upload(StringIO("Stop   at the line."), "manual.md")

    assert pages == [RawPage("Stop at the line.")]


@pytest.mark.parametrize("filename", ["manual.pdf", "manual.csv", "manual"])
def test_parse_text_upload_rejects_unsupported_extensions(filename):
    with pytest.raises(ValueError, match="Unsupported text file type"):
        parse_text_upload(BytesIO(b"text"), filename)


def test_parse_text_upload_rejects_invalid_utf8():
    with pytest.raises(ValueError, match="UTF-8"):
        parse_text_upload(BytesIO(b"\xff"), "manual.txt")


def test_parse_text_upload_enforces_size_limit(monkeypatch):
    monkeypatch.setattr(file_ingestion, "MAX_TEXT_FILE_BYTES", 4)

    with pytest.raises(ValueError, match="exceeds"):
        parse_text_upload(BytesIO(b"12345"), "manual.txt")


def test_ingest_text_upload_passes_clean_pages_and_metadata_to_pipeline(monkeypatch):
    captured = {}

    def fake_ingest_pages(pages, **kwargs):
        captured["pages"] = pages
        captured.update(kwargs)
        return "saved document"

    monkeypatch.setattr(file_ingestion, "ingest_pages", fake_ingest_pages)
    result = ingest_text_upload(
        BytesIO("  Yield\u0000 to the right.  ".encode("utf-8")),
        "right_of_way.txt",
        state="Georgia",
        edition="2026",
    )

    assert result == "saved document"
    assert captured["pages"] == [RawPage("Yield to the right.")]
    assert captured["title"] == "right of way"
    assert captured["source_path"] == "upload:right_of_way.txt"
    assert captured["state"] == "Georgia"
    assert captured["edition"] == "2026"


def test_ingest_text_file_reads_a_local_path(monkeypatch):
    captured = {}

    def fake_ingest_pages(pages, **kwargs):
        captured["pages"] = pages
        captured.update(kwargs)
        return "saved document"

    monkeypatch.setattr(file_ingestion, "ingest_pages", fake_ingest_pages)
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        source = Path(temp_dir) / "driver_manual.md"
        source.write_text(" Stop   before proceeding. ", encoding="utf-8")

        result = file_ingestion.ingest_text_file(source)

        assert result == "saved document"
        assert captured["pages"] == [RawPage("Stop before proceeding.")]
        assert captured["source_path"] == str(source.resolve())
