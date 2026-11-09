import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from apps.chat.services.rag import answer_question
from apps.knowledge.services.embedding_generation import ConfigurationError
from apps.monitoring.metrics import monitor_chat, note_failure

logger = logging.getLogger(__name__)

MAX_QUESTION_LENGTH = 1000


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})


@csrf_exempt
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

    return JsonResponse({"answer": result.answer, "grounded": result.grounded})
