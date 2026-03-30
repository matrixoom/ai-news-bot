import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.app.web import create_fastapi_app
from src.app.web.spa_assets import SpaAssets


class FrontendSpaServingTests(unittest.TestCase):
    def _client_with_spa_assets(self, spa_assets: SpaAssets) -> TestClient:
        with patch("src.app.web.fastapi_app.load_spa_assets", return_value=spa_assets):
            return TestClient(create_fastapi_app())

    def _missing_spa_assets(self) -> SpaAssets:
        missing_root = Path(tempfile.gettempdir()) / "ai-news-bot-missing-spa"
        return SpaAssets(
            dist_dir=missing_root,
            index_path=missing_root / "index.html",
        )

    def test_root_redirects_to_dashboard_when_compiled_spa_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dist_dir = Path(temp_dir)
            index_path = dist_dir / "index.html"
            index_path.write_text("<!doctype html><title>Workbench SPA</title>", encoding="utf-8")
            client = self._client_with_spa_assets(SpaAssets(dist_dir=dist_dir, index_path=index_path))

            response = client.get("/", follow_redirects=False)

        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "/dashboard")

    def test_workbench_routes_return_spa_index_when_compiled_bundle_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dist_dir = Path(temp_dir)
            index_path = dist_dir / "index.html"
            index_path.write_text("<!doctype html><title>Workbench SPA</title><div id='app'></div>", encoding="utf-8")
            client = self._client_with_spa_assets(SpaAssets(dist_dir=dist_dir, index_path=index_path))

            for route in ("/dashboard", "/news", "/macro", "/market", "/events", "/push", "/settings"):
                with self.subTest(route=route):
                    response = client.get(route)

                    self.assertEqual(response.status_code, 200)
                    self.assertIn("Workbench SPA", response.text)
                    self.assertIn("<div id='app'></div>", response.text)

    def test_root_keeps_legacy_static_homepage_when_compiled_spa_missing(self):
        client = self._client_with_spa_assets(self._missing_spa_assets())

        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Trend Insights", response.text)

    def test_workbench_routes_return_503_html_when_compiled_spa_missing(self):
        client = self._client_with_spa_assets(self._missing_spa_assets())

        for route in ("/dashboard", "/news", "/macro", "/market", "/events", "/push", "/settings"):
            with self.subTest(route=route):
                response = client.get(route)

                self.assertEqual(response.status_code, 503)
                self.assertIn("Workbench unavailable", response.text)
                self.assertIn("index.html", response.text)

    def test_api_and_static_routes_are_not_captured_by_workbench_spa_routes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dist_dir = Path(temp_dir)
            index_path = dist_dir / "index.html"
            index_path.write_text("<!doctype html><title>Workbench SPA</title>", encoding="utf-8")
            client = self._client_with_spa_assets(SpaAssets(dist_dir=dist_dir, index_path=index_path))

            api_response = client.get("/api/dashboard")
            static_response = client.get("/static/index.html")

        self.assertEqual(api_response.status_code, 200)
        self.assertIsInstance(api_response.json(), dict)
        self.assertEqual(static_response.status_code, 200)
        self.assertIn("Trend Insights", static_response.text)

    def test_legacy_route_remains_available_when_compiled_spa_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dist_dir = Path(temp_dir)
            index_path = dist_dir / "index.html"
            index_path.write_text("<!doctype html><title>Workbench SPA</title>", encoding="utf-8")
            client = self._client_with_spa_assets(SpaAssets(dist_dir=dist_dir, index_path=index_path))

            response = client.get("/legacy")

        self.assertEqual(response.status_code, 200)
        self.assertIn("财经与政策情报仪表盘", response.text)


if __name__ == "__main__":
    unittest.main()
