from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.knowledge.services.document_ingestion import ingest_pdf
from apps.knowledge.services.file_ingestion import ingest_text_file

SUPPORTED_EXTENSIONS = {".md", ".pdf", ".txt"}


class Command(BaseCommand):
    help = "Load local PDF, text, and Markdown files into the knowledge base."

    def add_arguments(self, parser):
        parser.add_argument("paths", nargs="*", help="Supported files or folders to ingest.")
        parser.add_argument("--state", default="", help='e.g. "Georgia"')
        parser.add_argument("--edition", default="", help='e.g. "2026"')
        parser.add_argument("--title", default=None, help="Title (only when ingesting one file).")

    def handle(self, *args, **options):
        paths = [Path(p) for p in options["paths"]] or [settings.KNOWLEDGE_DATA_DIR]
        files = []
        for path in paths:
            if path.is_dir():
                files.extend(sorted(
                    p for p in path.iterdir()
                    if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
                ))
            elif path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(path)
            elif path.is_file():
                raise CommandError(f"Unsupported file type: {path.suffix or '(no extension)'}")
            else:
                raise CommandError(f"Not found: {path}")
        if not files:
            raise CommandError(f"No supported files found in: {', '.join(map(str, paths))}")
        if options["title"] and len(files) > 1:
            raise CommandError("--title can only be used with a single file.")

        for file in files:
            self.stdout.write(f"Ingesting {file.name} ...")
            try:
                ingestion_method = ingest_pdf if file.suffix.lower() == ".pdf" else ingest_text_file
                document = ingestion_method(
                    file.resolve(),
                    title=options["title"],
                    state=options["state"],
                    edition=options["edition"],
                )
            except Exception as error:  # noqa: BLE001 - surface any provider/parse error
                raise CommandError(f"{file.name}: {error}") from error
            self.stdout.write(self.style.SUCCESS(f"  {document.title}: {document.chunks.count()} chunks"))
