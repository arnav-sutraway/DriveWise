from django.test import TestCase
from django.conf import settings


class ApiEndpointTests(TestCase):
    def test_django_uses_frontend_build_directory(self):
        self.assertEqual(
            settings.FRONTEND_BUILD_DIR,
            settings.BASE_DIR.parent / "frontend" / "dist",
        )

    def test_health_endpoint_returns_ok(self):
        response = self.client.get("/api/v1/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_chat_endpoint_is_a_non_implemented_placeholder(self):
        response = self.client.post(
            "/api/v1/chat/",
            data={"message": "How does a four-way stop work?"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 501)
        self.assertEqual(
            response.json(),
            {"detail": "Chat responses are not implemented yet."},
        )

    def test_chat_endpoint_only_accepts_post(self):
        response = self.client.get("/api/v1/chat/")

        self.assertEqual(response.status_code, 405)
