"""Summaries over minute aggregates; no individual request history is retained."""

from collections import defaultdict
from datetime import timedelta
from math import ceil

from django.conf import settings
from django.db.models import Avg, Count, Max, Sum
from django.utils import timezone

from .metrics import FAILURES, LATENCY_BOUNDS_MS, STAGES
from .models import PerformanceBucket, UsageLog


def format_ms(value):
    return f"{value / 1000:.2f} s" if value >= 1000 else f"{value:.0f} ms"


def summarize(rows):
    samples = sum(row["samples"] for row in rows)
    if not samples:
        return {"samples": 0, "average": "—", "maximum": "—", "p95": "—", "p95_upper_ms": None}
    histogram = defaultdict(int)
    for row in rows:
        histogram[row["upper_bound_ms"]] += row["samples"]
    rank, seen, upper = ceil(samples * 0.95), 0, 0
    for upper in sorted(histogram, key=lambda bound: bound or float("inf")):
        seen += histogram[upper]
        if seen >= rank:
            break
    return {
        "samples": samples,
        "average": format_ms(sum(row["total_ms"] for row in rows) / samples),
        "maximum": format_ms(max(row["max_ms"] for row in rows)),
        "p95": f"≤ {format_ms(upper)}" if upper else f"> {format_ms(LATENCY_BOUNDS_MS[-1])}",
        "p95_upper_ms": upper or float("inf"),
    }


def performance_report(minutes, now=None):
    now = now or timezone.now()
    # Include the current minute and the preceding minutes, never a partial old bucket.
    start = now.replace(second=0, microsecond=0) - timedelta(minutes=minutes - 1)
    rows = list(
        PerformanceBucket.objects.filter(minute__gte=start, minute__lte=now)
        .values("stage", "outcome", "upper_bound_ms")
        .annotate(samples=Sum("samples"), total_ms=Sum("total_ms"), max_ms=Max("max_ms"))
    )
    requests = [row for row in rows if row["stage"] == "request" and row["outcome"] != "invalid"]
    overall = summarize(requests)
    failure_count = sum(row["samples"] for row in requests if row["outcome"] in FAILURES)
    rate = failure_count / overall["samples"] * 100 if overall["samples"] else None
    failures = [
        {"label": label, "count": sum(row["samples"] for row in requests if row["outcome"] == outcome)}
        for outcome, label in FAILURES.items()
    ]
    stages = [
        {"label": label, **summarize([row for row in rows if row["stage"] == stage])}
        for stage, label in STAGES.items()
    ]
    latency_limit = settings.PERFORMANCE_LATENCY_WARNING_MS
    failure_limit = settings.PERFORMANCE_FAILURE_WARNING_PERCENT
    warnings = []
    if overall["samples"]:
        if latency_limit and overall["p95_upper_ms"] > latency_limit:
            warnings.append("The p95 latency band exceeds the configured warning threshold.")
        if failure_limit and rate >= failure_limit:
            warnings.append("The system failure rate has reached the configured warning threshold.")
    if not overall["samples"]:
        status, status_class = "No data", "neutral"
    elif warnings:
        status, status_class = "Threshold exceeded", "warning"
    elif failure_count:
        status, status_class = "Failures observed", "warning"
    elif not latency_limit and not failure_limit:
        status, status_class = "Collecting baseline", "neutral"
    else:
        status, status_class = "Within configured thresholds", "good"
    return {
        "overall": overall, "failures": failures, "stages": stages,
        "failure_rate": f"{rate:.1f}%" if rate is not None else "—",
        "status": status, "status_class": status_class, "warnings": warnings,
        "start": start, "updated_at": now,
        "latency_limit": format_ms(latency_limit) if latency_limit else "Not set — baseline mode",
        "failure_limit": f"{failure_limit:g}%" if failure_limit else "Not set — baseline mode",
    }


def usage_report(hours, now=None, limit=100):
    """Query count, average response time, and the most recent individual requests."""
    now = now or timezone.now()
    start = now - timedelta(hours=hours)
    logs = UsageLog.objects.filter(created_at__gt=start, created_at__lte=now)
    totals = logs.aggregate(count=Count("id"), average=Avg("response_ms"))
    return {
        "total_queries": totals["count"],
        "average": format_ms(totals["average"]) if totals["count"] else "—",
        "logs": [
            {"created_at": log.created_at, "response": format_ms(log.response_ms),
             "outcome": FAILURES.get(log.outcome, "Success")}
            for log in logs[:limit]
        ],
        "start": start, "updated_at": now,
    }
