from math import isfinite

from django.conf import settings
from django.core.checks import Error, register


@register()
def check_thresholds(app_configs, **kwargs):
    errors = []
    latency = settings.PERFORMANCE_LATENCY_WARNING_MS
    failure = settings.PERFORMANCE_FAILURE_WARNING_PERCENT
    if not isfinite(latency) or latency < 0:
        errors.append(Error("PERFORMANCE_LATENCY_WARNING_MS must be finite and >= 0.", id="monitoring.E001"))
    if not isfinite(failure) or not 0 <= failure <= 100:
        errors.append(Error("PERFORMANCE_FAILURE_WARNING_PERCENT must be between 0 and 100.", id="monitoring.E002"))
    return errors
