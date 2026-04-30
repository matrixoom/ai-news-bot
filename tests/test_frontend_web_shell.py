import unittest
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from src.app.web import create_fastapi_app
from src.services.dashboard_service import DashboardService


class FrontendShellSourceGuardTests(unittest.TestCase):
    """校验前端壳层仍按推送中心使用场景懒加载预览数据。"""

    def test_frontend_shell_does_not_load_newsnow_provider(self):
        """校验前端壳层启动不会隐式加载已下线的 NewsNow provider。"""
        self.assertNotIn("src.providers.newsnow_provider", sys.modules)

    def test_frontend_shell_keeps_push_module_lazy_loaded(self):
        content = Path("frontend/src/features/push/hooks/use-push-module-query.ts").read_text(encoding="utf-8")

        self.assertIn('const includePreview = activeTab !== "history";', content)
        self.assertIn('queryKey: ["push-module", includePreview]', content)
        self.assertIn('getPushModule({ signal, includePreview, refresh: includePreview })', content)

    def test_live_frontend_background_refresh_excludes_newsnow_modes(self):
        """校验实时工作台后台预热不再注册 NewsNow 的三种新闻模式。"""
        service = DashboardService(prefer_live_data=True, enable_background_refresh=False)

        self.assertNotIn("module:news:hybrid", service._background_managed_module_keys)
        self.assertNotIn("module:news:api", service._background_managed_module_keys)
        self.assertNotIn("module:news:upstream", service._background_managed_module_keys)


class FastAPIWebShellTests(unittest.TestCase):
    """校验前端工作台壳层依赖的后端基础路由契约。"""

    def setUp(self):
        self.client = TestClient(create_fastapi_app())

    def test_health_route_returns_ok(self):
        response = self.client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_dashboard_api_is_removed(self):
        response = self.client.get("/api/dashboard")

        self.assertEqual(response.status_code, 404)

    def test_frontend_dashboard_api_is_removed(self):
        response = self.client.get("/api/frontend/dashboard")

        self.assertEqual(response.status_code, 404)

    def test_frontend_dashboard_news_mode_query_is_removed(self):
        response = self.client.get("/api/frontend/dashboard?news_mode=upstream")

        self.assertEqual(response.status_code, 404)

    def test_removed_frontend_child_module_endpoints_return_not_found(self):
        for path in (
            "/api/frontend/modules/news?news_mode=upstream",
            "/api/frontend/modules/macro",
            "/api/frontend/modules/market",
            "/api/frontend/modules/events",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)

    def test_frontend_status_module_endpoint_returns_shell_status(self):
        response = self.client.get("/api/frontend/modules/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["module"]["id"], "status")
        self.assertIn("coverage_note", payload)
        self.assertEqual(payload["coverage_note"], "")
        self.assertIn("details", payload["module"])

    def test_legacy_dashboard_route_is_removed(self):
        response = self.client.get("/legacy")

        self.assertEqual(response.status_code, 404)

    def test_unknown_route_returns_custom_not_found_page(self):
        response = self.client.get("/missing")

        self.assertEqual(response.status_code, 404)
        self.assertIn("Page not found", response.text)


if __name__ == "__main__":
    unittest.main()
