from django.urls import path

from . import views


urlpatterns = [
    path("developer/", views.index, name="developer-frontend"),
    path("", views.index, name="frontend"),
]
