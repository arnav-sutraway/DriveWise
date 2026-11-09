from django.db import models


class PerformanceBucket(models.Model):
    """One aggregate, never a query record. No prompts, answers, or user identifiers."""

    minute = models.DateTimeField(db_index=True)
    stage = models.CharField(max_length=16)
    outcome = models.CharField(max_length=16)
    # Upper bound of a non-cumulative latency bucket; zero means overflow.
    upper_bound_ms = models.PositiveIntegerField()
    samples = models.PositiveBigIntegerField(default=0)
    total_ms = models.FloatField(default=0)
    max_ms = models.FloatField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["minute", "stage", "outcome", "upper_bound_ms"],
                name="unique_performance_bucket",
            ),
        ]
