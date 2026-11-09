from django.contrib import admin
from django.urls import include, path

from apps.monitoring.views import performance


urlpatterns = [
    path("admin/performance/", admin.site.admin_view(performance), name="performance"),
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.api.urls")),
    path("", include("apps.frontend.urls")),
]
