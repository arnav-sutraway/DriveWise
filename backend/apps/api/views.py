from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_POST
def chat(request):
    return JsonResponse(
        {"detail": "Chat responses are not implemented yet."},
        status=501,
    )
