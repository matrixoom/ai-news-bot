import json
import unittest

from src.app.web.app import create_web_app
from src.services.dashboard_service import DashboardService


class DashboardServiceTests(unittest.TestCase):
    def test_build_snapshot_returns_expected_sections(self):
        snapshot = DashboardService().build_snapshot()

        self.assertEqual(snapshot.title, "财经与政策情报仪表盘")
        self.assertGreaterEqual(len(snapshot.sections), 5)
        self.assertIn("Z", snapshot.generated_at)


class WebAppTests(unittest.TestCase):
    def _call_app(self, path: str):
        app = create_web_app()
        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = headers

        body = b"".join(app({"PATH_INFO": path}, start_response))
        return captured["status"], dict(captured["headers"]), body

    def test_health_endpoint_returns_ok_json(self):
        status, headers, body = self._call_app("/healthz")

        self.assertEqual(status, "200 OK")
        self.assertIn("application/json", headers["Content-Type"])
        self.assertEqual(json.loads(body.decode("utf-8")), {"status": "ok"})

    def test_dashboard_api_returns_structured_payload(self):
        status, headers, body = self._call_app("/api/dashboard")

        self.assertEqual(status, "200 OK")
        self.assertIn("application/json", headers["Content-Type"])
        payload = json.loads(body.decode("utf-8"))
        self.assertIn("sections", payload)
        self.assertGreaterEqual(len(payload["sections"]), 5)

    def test_root_page_renders_dashboard_title(self):
        status, headers, body = self._call_app("/")

        self.assertEqual(status, "200 OK")
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn("财经与政策情报仪表盘", body.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
