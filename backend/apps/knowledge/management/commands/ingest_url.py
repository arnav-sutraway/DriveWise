from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError

from apps.knowledge.services.web_ingestion import ingest_web_url


class Command(BaseCommand):
    help = "Fetch and ingest one HTTPS page from KNOWLEDGE_ALLOWED_HOSTS."

    def add_arguments(self, parser):
        parser.add_argument("url", help="HTTPS page URL to ingest.")
        parser.add_argument("--title", default=None, help="Override the page title.")
        parser.add_argument("--state", default="", help="Optional state label.")
        parser.add_argument("--edition", default="", help="Optional edition label.")

    def handle(self, *args, **options):
        self.stdout.write(f"Fetching {options['url']} ...")
        try:
            document = ingest_web_url(
                options["url"],
                title=options["title"],
                state=options["state"],
                edition=options["edition"],
            )
        except (ImproperlyConfigured, ValueError, OSError) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(
            self.style.SUCCESS(f"{document.title}: {document.chunks.count()} chunks")
        )
