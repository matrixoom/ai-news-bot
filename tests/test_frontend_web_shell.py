import unittest
import sys
from pathlib import Path
from unittest.mock import Mock

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
        self.assertIn('getPushModule({ signal, includePreview })', content)

    def test_live_frontend_background_refresh_excludes_newsnow_modes(self):
        """校验实时工作台后台预热不再注册 NewsNow 的三种新闻模式。"""
        service = DashboardService(prefer_live_data=True, enable_background_refresh=False)

        self.assertNotIn("module:news:hybrid", service._background_managed_module_keys)
        self.assertNotIn("module:news:api", service._background_managed_module_keys)
        self.assertNotIn("module:news:upstream", service._background_managed_module_keys)

    def test_frontend_theme_uses_semantic_tokens_without_important_overrides(self):
        """校验新主题通过语义变量驱动，不再翻转 Tailwind 工具类。"""
        content = Path("frontend/src/index.css").read_text(encoding="utf-8")

        self.assertIn("--color-canvas:", content)
        self.assertIn("--color-surface:", content)
        self.assertIn("--color-accent:", content)
        self.assertNotIn("!important", content)


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

    def test_frontend_status_module_endpoint_is_removed(self):
        response = self.client.get("/api/frontend/modules/status")

        self.assertEqual(response.status_code, 404)

    def test_legacy_dashboard_route_is_removed(self):
        response = self.client.get("/legacy")

        self.assertEqual(response.status_code, 404)

    def test_unknown_route_returns_custom_not_found_page(self):
        response = self.client.get("/missing")

        self.assertEqual(response.status_code, 404)
        self.assertIn("Page not found", response.text)

    def test_stock_market_overview_endpoint_returns_service_payload(self):
        """校验股票市场概览接口透传 Service 的稳定契约。"""
        stock_service = Mock()
        stock_service.build_overview_payload.return_value = {
            "generated_at": "2026-06-10T10:32:00Z",
            "indices": [],
            "breadth": {
                "trade_date": "2026-06-09",
                "advanced": 1,
                "declined": 1,
                "unchanged": 0,
                "total": 2,
                "status": "live",
            },
        }
        client = TestClient(create_fastapi_app(stock_market_service=stock_service))

        response = client.get("/api/frontend/modules/market-data/stocks/overview")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["breadth"]["advanced"], 1)
        stock_service.build_overview_payload.assert_called_once_with()

    def test_stock_market_overview_endpoint_returns_503_on_service_failure(self):
        """校验概览 Service 整体异常时返回统一不可用错误。"""
        stock_service = Mock()
        stock_service.build_overview_payload.side_effect = RuntimeError("boom")
        client = TestClient(create_fastapi_app(stock_market_service=stock_service))

        response = client.get("/api/frontend/modules/market-data/stocks/overview")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"error": "frontend_stock_market_overview_unavailable"})

    def test_stock_market_overview_index_refresh_endpoint_passes_range(self):
        """校验宽基 K 线刷新接口把当前时间范围传给 Service。"""
        stock_service = Mock()
        stock_service.refresh_overview_indices.return_value = {
            "ok": True,
            "range": {
                "type": "20y",
                "start_date": "2006-06-20",
                "end_date": "2026-06-20",
            },
            "overview": {
                "generated_at": "2026-06-20T06:20:00Z",
                "indices": [],
                "breadth": {
                    "trade_date": None,
                    "advanced": 0,
                    "declined": 0,
                    "unchanged": 0,
                    "total": 0,
                    "status": "unavailable",
                },
            },
        }
        client = TestClient(create_fastapi_app(stock_market_service=stock_service))

        response = client.post(
            "/api/frontend/modules/market-data/stocks/overview/indices/refresh",
            json={"range": "20y"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["range"]["type"], "20y")
        stock_service.refresh_overview_indices.assert_called_once_with(
            range_type="20y",
            start_date=None,
            end_date=None,
        )


if __name__ == "__main__":
    unittest.main()
