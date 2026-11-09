import logging

from django.contrib import admin
from django.db import DatabaseError
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET

from .reporting import performance_report

logger = logging.getLogger(__name__)


@require_GET
def performance(request):
    # The URL wraps this view in admin.site.admin_view (active staff + no caching).
    minutes = 60 if request.GET.get("window") == "60" else 15
    context = {**admin.site.each_context(request), "title": "Chatbot performance", "minutes": minutes}
    status = 200
    try:
        context.update(performance_report(minutes))
    except DatabaseError:
        logger.warning("Performance dashboard could not read metrics.")
        context["unavailable"] = True
        status = 503
    return TemplateResponse(request, "monitoring/performance.html", context, status=status)
