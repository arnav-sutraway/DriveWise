from django.urls import path

from . import views


urlpatterns = [
    path("health/", views.health, name="health"),
    path("chat/", views.chat, name="chat"),
    path("documents/<int:document_id>/file/", views.document_file, name="document-file"),
]
