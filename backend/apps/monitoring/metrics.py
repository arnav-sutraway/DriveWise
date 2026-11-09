"""Request-local timing, flushed as aggregates once a chat response is ready."""

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import lru_cache, wraps
from importlib import import_module
from time import perf_counter

from django.db import transaction
from django.db.models import F
from django.db.models.functions import Greatest
from django.utils import timezone

from apps.knowledge.services.embedding_generation import ConfigurationError

from .models import PerformanceBucket

logger = logging.getLogger(__name__)

LATENCY_BOUNDS_MS = (
    100, 250, 500, 1000, 2000, 3000, 5000, 7500, 10000,
    15000, 30000, 60000, 90000, 120000, 180000, 300000,
)
STAGES = {"embedding": "Question embedding", "retrieval": "Passage retrieval", "generation": "Answer generation"}
FAILURES = {
    "configuration": "Configuration",
    "provider": "Provider / connection",
    "timeout": "Timeout",
    "unexpected": "Unexpected error",
}


@dataclass
class Measurement:
    observations: list[tuple[str, str, float]] = field(default_factory=list)
    failure: str | None = None


_current: ContextVar[Measurement | None] = ContextVar("chat_performance", default=None)


@lru_cache(maxsize=1)
def _transport_errors():
    """GenAI versions use either httpx or httpx2; recognize both if installed."""
    timeouts, requests = [TimeoutError], [ConnectionError]
    for module_name in ("httpx", "httpx2"):
        try:
            module = import_module(module_name)
        except ImportError:
            continue
        timeouts.append(module.TimeoutException)
        requests.append(module.RequestError)
    return tuple(timeouts), tuple(requests)


def failure_kind(error):
    if isinstance(error, ConfigurationError):
        return "configuration"
    timeouts, requests = _transport_errors()
    if isinstance(error, timeouts):
        return "timeout"
    from google.genai.errors import APIError

    if isinstance(error, APIError):
        return "timeout" if error.code in (408, 504) else "provider"
    if isinstance(error, requests):
        return "provider"
    return "unexpected"


def note_failure(error):
    measurement = _current.get()
    if measurement is not None:
        measurement.failure = failure_kind(error)


@contextmanager
def time_stage(stage):
    measurement = _current.get()
    if measurement is None:
        yield
        return
    started = perf_counter()
    outcome = "success"
    try:
        yield
    except Exception as error:
        outcome = failure_kind(error)
        measurement.failure = outcome
        raise
    finally:
        measurement.observations.append((stage, outcome, (perf_counter() - started) * 1000))


def save_observations(observations, completed_at):
    """Atomic increments preserve concurrent updates; one transaction per response."""
    minute = completed_at.replace(second=0, microsecond=0)
    with transaction.atomic():
        for stage, outcome, duration_ms in observations:
            upper = next((bound for bound in LATENCY_BOUNDS_MS if duration_ms <= bound), 0)
            key = dict(minute=minute, stage=stage, outcome=outcome, upper_bound_ms=upper)
            updates = dict(samples=F("samples") + 1, total_ms=F("total_ms") + duration_ms,
                           max_ms=Greatest(F("max_ms"), duration_ms))
            # Start with a write to avoid a read-to-write lock upgrade on SQLite.
            if not PerformanceBucket.objects.filter(**key).update(**updates):
                bucket, _ = PerformanceBucket.objects.get_or_create(**key)
                PerformanceBucket.objects.filter(pk=bucket.pk).update(**updates)


def monitor_chat(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        measurement = Measurement()
        token = _current.set(measurement)
        started = perf_counter()
        outcome = "unexpected"
        try:
            response = view(request, *args, **kwargs)
            if response.status_code < 400:
                outcome = "success"
            elif response.status_code < 500:
                outcome = "invalid"
            else:
                outcome = measurement.failure or "unexpected"
            return response
        except Exception as error:
            outcome = failure_kind(error)
            raise
        finally:
            duration_ms = (perf_counter() - started) * 1000
            _current.reset(token)
            measurement.observations.append(("request", outcome, duration_ms))
            try:
                save_observations(measurement.observations, timezone.now())
            except Exception as error:
                # Keep telemetry failure separate from the learner's response.
                # Do not include exception payloads, prompts, or provider secrets.
                logger.warning("Performance metrics could not be saved (%s).", type(error).__name__)

    return wrapped
