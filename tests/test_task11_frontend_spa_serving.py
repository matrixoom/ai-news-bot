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

    def test_root_redirects_to_push_when_compiled_spa_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dist_dir = Path(temp_dir)
            index_path = dist_dir / "index.html"
            index_path.write_text("<!doctype html><title>Workbench SPA</title>", encoding="utf-8")
            client = self._client_with_spa_assets(SpaAssets(dist_dir=dist_dir, index_path=index_path))

            response = client.get("/", follow_redirects=False)

        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "/push")

    def test_workbench_routes_return_spa_index_when_compiled_bundle_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dist_dir = Path(temp_dir)
            index_path = dist_dir / "index.html"
            index_path.write_text("<!doctype html><title>Workbench SPA</title><div id='app'></div>", encoding="utf-8")
            client = self._client_with_spa_assets(SpaAssets(dist_dir=dist_dir, index_path=index_path))

            for route in ("/push", "/status", "/settings"):
                with self.subTest(route=route):
                    response = client.get(route)

                    self.assertEqual(response.status_code, 200)
                    self.assertIn("Workbench SPA", response.text)
                    self.assertIn("<div id='app'></div>", response.text)

    def test_compiled_asset_files_are_served_when_spa_bundle_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dist_dir = Path(temp_dir)
            assets_dir = dist_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            index_path = dist_dir / "index.html"
            js_path = assets_dir / "index-test.js"
            css_path = assets_dir / "index-test.css"
            js_path.write_text("console.log('spa');", encoding="utf-8")
            css_path.write_text("body{background:black;}", encoding="utf-8")
            index_path.write_text(
                "<!doctype html><title>Workbench SPA</title>"
                "<script type='module' src='/assets/index-test.js'></script>"
                "<link rel='stylesheet' href='/assets/index-test.css'>",
                encoding="utf-8",
            )
            client = self._client_with_spa_assets(SpaAssets(dist_dir=dist_dir, index_path=index_path))

            js_response = client.get("/assets/index-test.js")
            css_response = client.get("/assets/index-test.css")

        self.assertEqual(js_response.status_code, 200)
        self.assertIn("console.log('spa');", js_response.text)
        self.assertEqual(css_response.status_code, 200)
        self.assertIn("background:black", css_response.text)

    def test_root_returns_spa_unavailable_when_compiled_spa_missing(self):
        client = self._client_with_spa_assets(self._missing_spa_assets())

        response = client.get("/")

        self.assertEqual(response.status_code, 503)
        self.assertIn("Workbench unavailable", response.text)

    def test_workbench_routes_return_503_html_when_compiled_spa_missing(self):
        client = self._client_with_spa_assets(self._missing_spa_assets())

        for route in ("/push", "/status", "/settings"):
            with self.subTest(route=route):
                response = client.get(route)

                self.assertEqual(response.status_code, 503)
                self.assertIn("Workbench unavailable", response.text)
                self.assertIn("index.html", response.text)

    def test_removed_dashboard_api_and_legacy_routes_return_not_found(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dist_dir = Path(temp_dir)
            index_path = dist_dir / "index.html"
            index_path.write_text("<!doctype html><title>Workbench SPA</title>", encoding="utf-8")
            client = self._client_with_spa_assets(SpaAssets(dist_dir=dist_dir, index_path=index_path))

            api_response = client.get("/api/dashboard")
            legacy_response = client.get("/legacy")

        self.assertEqual(api_response.status_code, 404)
        self.assertEqual(legacy_response.status_code, 404)

    def test_removed_dashboard_workbench_routes_return_not_found(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dist_dir = Path(temp_dir)
            index_path = dist_dir / "index.html"
            index_path.write_text("<!doctype html><title>Workbench SPA</title>", encoding="utf-8")
            client = self._client_with_spa_assets(SpaAssets(dist_dir=dist_dir, index_path=index_path))

            for route in ("/dashboard", "/news", "/macro", "/market", "/events"):
                with self.subTest(route=route):
                    response = client.get(route)

                    self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
