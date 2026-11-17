import json
import logging

from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from apps.chat.services.rag import answer_question
from apps.chat.services.visualizations import visualization_for_question
from apps.knowledge.models import Document
from apps.knowledge.services.embedding_generation import ConfigurationError
from apps.knowledge.services.sources import LOCAL_CONTENT_TYPES, local_file
from apps.monitoring.metrics import monitor_chat, note_failure

from .ratelimit import rate_limit

logger = logging.getLogger(__name__)

MAX_QUESTION_LENGTH = 1000


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})


@csrf_exempt
@rate_limit
@monitor_chat
@require_POST
def chat(request):
    """POST {"message": "..."} -> {"answer": str, "grounded": bool}."""
    try:
        payload = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"detail": "Request body must be JSON."}, status=400)

    message = payload.get("message") if isinstance(payload, dict) else None
    if not isinstance(message, str) or not message.strip():
        return JsonResponse({"detail": "Send a non-empty \"message\" string."}, status=400)
    message = message.strip()
    if len(message) > MAX_QUESTION_LENGTH:
        return JsonResponse(
            {"detail": f"Questions must be under {MAX_QUESTION_LENGTH} characters."}, status=400)

    try:
        result = answer_question(message)
    except ConfigurationError as error:
        note_failure(error)
        return JsonResponse({"detail": f"Chatbot is not configured: {error}"}, status=503)
    except Exception as error:  # noqa: BLE001 - provider/network failure
        note_failure(error)
        logger.exception("Chat request failed")
        return JsonResponse(
            {"detail": "The coach couldn't answer right now. Please try again."}, status=502)

    return JsonResponse({
        "answer": result.answer,
        "grounded": result.grounded,
        "sources": result.sources,
        "visualization": visualization_for_question(message, grounded=result.grounded),
    })


@require_GET
def document_file(request, document_id):
    """Serve the ingested copy of a knowledge-base document so citations can link to it."""
    document = get_object_or_404(Document, pk=document_id)
    path = local_file(document)
    if path is None:
        raise Http404("This document has no local copy.")
    # Inline (not a download) so PDF viewers honour #page=N.
    return FileResponse(path.open("rb"), filename=path.name,
                        content_type=LOCAL_CONTENT_TYPES[path.suffix.lower()])
