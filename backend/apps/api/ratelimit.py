"""Per-client request limit for the chat endpoint, so one visitor can't drain the Gemini quota."""

from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse


def client_ip(request):
    # Behind Vercel's /api rewrite and PythonAnywhere's load balancer, REMOTE_ADDR is a proxy.
    # Vercel sets X-Forwarded-For to the visitor's IP, so the leftmost entry is the visitor.
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return forwarded.split(",")[0].strip() or request.META.get("REMOTE_ADDR", "unknown")


def rate_limit(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        limit, window = settings.CHAT_RATE_LIMIT, settings.CHAT_RATE_LIMIT_WINDOW_SECONDS
        if limit <= 0 or request.method != "POST":
            return view(request, *args, **kwargs)

        key = f"chat-rate:{client_ip(request)}"
        cache.add(key, 0, timeout=window)  # starts a fixed window if none is open
        try:
            count = cache.incr(key)
        except ValueError:  # window expired between add() and incr()
            cache.set(key, 1, timeout=window)
            count = 1

        if count > limit:
            response = JsonResponse(
                {"detail": "Too many questions at once. Please wait a minute and try again."}, status=429)
            response["Retry-After"] = str(window)
            return response
        return view(request, *args, **kwargs)

    return wrapper
