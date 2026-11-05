from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import TestCase, override_settings


class FrontendIndexTests(TestCase):
    def test_index_is_served_from_the_configured_build_directory(self):
        with TemporaryDirectory() as build_directory:
            index_file = Path(build_directory) / "index.html"
            index_file.write_text("<html>frontend build</html>", encoding="utf-8")

            with override_settings(FRONTEND_BUILD_DIR=Path(build_directory)):
                response = self.client.get("/")

            try:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], "text/html")
                self.assertEqual(
                    b"".join(response.streaming_content),
                    b"<html>frontend build</html>",
                )
            finally:
                response.close()
