import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.app.web import create_fastapi_app


class Task03DocumentationTests(unittest.TestCase):
    def test_task03_main_doc_points_to_route_map_and_tests(self):
        content = Path("TASK/03-web-homepage-and-app-shell.md").read_text(encoding="utf-8")

        self.assertIn("Completed for implementation phase.", content)
        self.assertIn("03-route-map-and-viewmodel.md", content)
        self.assertIn("tests/test_task03_web_app_shell.py", content)


class FastAPIWebShellTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_fastapi_app())

    def test_health_route_returns_ok(self):
        response = self.client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_dashboard_api_returns_viewmodel_sections(self):
        response = self.client.get("/api/dashboard")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("dashboard_summary", payload)
        self.assertIn("news_sections", payload)
        self.assertIn("macro_sections", payload)
        self.assertIn("market_sections", payload)
        self.assertIn("event_sections", payload)
        self.assertIn("data_status", payload)
        self.assertGreaterEqual(len(payload["news_sections"]), 3)
        self.assertGreaterEqual(len(payload["macro_sections"]), 3)

    def test_root_renders_named_dashboard_panels(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Finance And Policy Intelligence Dashboard", response.text)
        self.assertIn("Technology News", response.text)
        self.assertIn("Data Status", response.text)

    def test_unknown_route_returns_custom_not_found_page(self):
        response = self.client.get("/missing")

        self.assertEqual(response.status_code, 404)
        self.assertIn("Page not found", response.text)


if __name__ == "__main__":
    unittest.main()
