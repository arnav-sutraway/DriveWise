from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.monitoring.models import PerformanceBucket


class Command(BaseCommand):
    help = "Remove performance aggregates older than the retention period (default: 7 days)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=7)

    def handle(self, *args, **options):
        if options["days"] < 1:
            raise CommandError("--days must be at least 1.")
        cutoff = timezone.now() - timedelta(days=options["days"])
        deleted, _ = PerformanceBucket.objects.filter(minute__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f"Removed {deleted} old performance aggregates."))
