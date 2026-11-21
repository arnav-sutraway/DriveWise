from django.urls import path

from . import views


urlpatterns = [
    path("health/", views.health, name="health"),
    path("chat/", views.chat, name="chat"),
    path("documents/<int:document_id>/file/", views.document_file, name="document-file"),
    path("developer/session/", views.developer_session, name="developer-session"),
    path("developer/csrf/", views.developer_csrf, name="developer-csrf"),
    path("developer/dashboard/", views.developer_dashboard, name="developer-dashboard"),
    path("developer/documents/", views.developer_documents, name="developer-documents"),
    path("developer/documents/<int:document_id>/", views.developer_document_detail,
         name="developer-document-detail"),
    path("developer/documents/<int:document_id>/reprocess/", views.developer_reprocess,
         name="developer-document-reprocess"),
    path("developer/ingest/upload/", views.developer_ingest_upload,
         name="developer-ingest-upload"),
    path("developer/ingest/text/", views.developer_ingest_text,
         name="developer-ingest-text"),
    path("developer/ingest/url/preview/", views.developer_url_preview,
         name="developer-url-preview"),
    path("developer/ingest/url/", views.developer_ingest_url,
         name="developer-ingest-url"),
    path("developer/preprocess/preview/", views.developer_preprocess_preview,
         name="developer-preprocess-preview"),
    path("developer/config/", views.developer_config, name="developer-config"),
    path("developer/tests/", views.developer_tests, name="developer-tests"),
    path("developer/tests/<int:test_id>/", views.developer_test_detail,
         name="developer-test-detail"),
    path("developer/evaluations/run/", views.developer_evaluation_run,
         name="developer-evaluation-run"),
    path("developer/evaluations/", views.developer_evaluations,
         name="developer-evaluations"),
]
