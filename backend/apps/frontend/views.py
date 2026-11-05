from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.views.decorators.http import require_GET


@require_GET
def index(request):
    index_file = settings.FRONTEND_BUILD_DIR / "index.html"
    if not index_file.is_file():
        raise Http404(
            "Frontend build not found. Run `npm run build` from the frontend folder."
        )

    return FileResponse(index_file.open("rb"), content_type="text/html")
