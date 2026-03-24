import unittest
from datetime import date
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
import pandas as pd

from src.app.web import create_fastapi_app
from src.app.web.frontend_payload import build_frontend_payload
from src.domain.external_data import NewsCategory
from src.providers.live_data import AkshareMacroDataProvider, AkshareMarketDataProvider
from src.providers.newsnow_provider import NewsNowAggregatedNewsProvider, _NewsNowUpstreamServerManager
from src.services.dashboard_service import (
    DashboardSection,
    DashboardSnapshot,
    DataStatusItem,
    EventSectionView,
    MarketCard,
    MetricCard,
    NewsItemView,
    NewsSectionView,
    SummaryBlock,
)


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
        self.assertIn("news_mode", payload)
        self.assertGreaterEqual(len(payload["news_sections"]), 3)
        self.assertGreaterEqual(len(payload["macro_sections"]), 3)

    def test_frontend_dashboard_news_items_include_clickable_url_field(self):
        response = self.client.get("/api/frontend/dashboard")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("news_sections", payload)
        self.assertIn("news_mode", payload)
        self.assertIn("news_mode_options", payload)
        self.assertIn("upstream_service_status", payload)
        self.assertGreaterEqual(len(payload["news_sections"]), 1)
        first_section = payload["news_sections"][0]
        self.assertIn("items", first_section)
        self.assertIn("item_count", first_section)
        self.assertGreaterEqual(len(first_section["items"]), 1)
        self.assertIn("url", first_section["items"][0])

    def test_frontend_dashboard_accepts_news_mode_query(self):
        response = self.client.get("/api/frontend/dashboard?news_mode=upstream")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["news_mode"], "upstream")

    def test_frontend_news_module_endpoint_returns_module_payload(self):
        response = self.client.get("/api/frontend/modules/news?news_mode=upstream")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["module"]["id"], "news")
        self.assertEqual(payload["news_mode"], "upstream")
        self.assertIn("news_mode_options", payload)
        self.assertIn("upstream_service_status", payload)
        self.assertIn("details", payload["module"])

    def test_frontend_status_module_endpoint_returns_shell_status(self):
        response = self.client.get("/api/frontend/modules/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["module"]["id"], "status")
        self.assertIn("coverage_note", payload)
        self.assertEqual(payload["coverage_note"], "")
        self.assertIn("details", payload["module"])

    def test_frontend_market_module_endpoint_returns_module_payload(self):
        response = self.client.get("/api/frontend/modules/market")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["module"]["id"], "market")
        self.assertIn("details", payload["module"])
        self.assertGreaterEqual(len(payload["module"]["details"]), 1)
        self.assertIn("chart_points", payload["module"]["details"][0]["section"])

    def test_root_renders_named_dashboard_panels(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Trend Insights", response.text)
        self.assertIn("一级模块导航", response.text)
        self.assertIn("contentStage", response.text)
        self.assertIn("loading-spinner", response.text)
        self.assertNotIn("正在连接后端数据接口", response.text)

    def test_unknown_route_returns_custom_not_found_page(self):
        response = self.client.get("/missing")

        self.assertEqual(response.status_code, 404)
        self.assertIn("Page not found", response.text)


class FrontendPayloadTests(unittest.TestCase):
    def test_frontend_payload_keeps_all_news_items_without_top10_truncation(self):
        news_items = [
            NewsItemView(
                title=f"Headline {index}",
                source="source",
                url=f"https://example.com/{index}",
                published_at="2026-03-21T08:00:00Z",
                tag="rss",
                summary=f"Summary {index}",
            )
            for index in range(12)
        ]
        snapshot = DashboardSnapshot(
            generated_at="2026-03-21T08:00:00Z",
            news_mode="hybrid",
            title="Dashboard",
            summary="Summary",
            sections=[DashboardSection("news", "News", "live", "desc")],
            dashboard_summary=SummaryBlock(
                title="Dashboard",
                subtitle="Summary",
                as_of_label="2026-03-21T08:00:00Z",
                coverage_note="note",
                highlights=[],
            ),
            news_sections=[NewsSectionView(key="technology", title="Tech", status="live", description="desc", items=news_items)],
            macro_sections=[
                MetricCard(
                    key="macro",
                    label="Macro",
                    value="1.0%",
                    context="ctx",
                    status="live",
                )
            ],
            market_sections=[
                MarketCard(
                    key="market",
                    label="Market",
                    close_value="1",
                    ma20_value="1",
                    signal="neutral",
                    status="live",
                )
            ],
            event_sections=[EventSectionView(key="events", title="Events", status="live", items=[])],
            data_status=[DataStatusItem(key="news", label="News", status="live", detail="ok")],
        )

        payload = build_frontend_payload(snapshot)

        self.assertEqual(payload["news_mode"], "hybrid")
        self.assertEqual(payload["news_sections"][0]["item_count"], 12)
        self.assertEqual(len(payload["news_sections"][0]["items"]), 12)
        self.assertEqual(payload["news_sections"][0]["items"][0]["summary"], "Summary 0")


class DashboardServiceCacheTests(unittest.TestCase):
    def test_live_dashboard_service_reuses_cached_snapshot_within_ttl(self):
        from src.services.dashboard_service import DashboardService

        class CountingNewsService:
            def __init__(self):
                self.calls = 0

            def build_snapshot(self):
                self.calls += 1
                return SimpleNamespace(domains=[])

        class CountingMacroService:
            def __init__(self):
                self.calls = 0

            def build_snapshot(self):
                self.calls += 1
                return SimpleNamespace(indicators=[])

        class CountingMarketService:
            def __init__(self):
                self.calls = 0

            def build_snapshot(self):
                self.calls += 1
                return SimpleNamespace(items=[])

        class CountingEventsService:
            def __init__(self):
                self.calls = 0

            def build_snapshot(self, refresh_store=False):
                _ = refresh_store
                self.calls += 1
                return SimpleNamespace(windows=[])

        news_service = CountingNewsService()
        macro_service = CountingMacroService()
        market_service = CountingMarketService()
        events_service = CountingEventsService()

        with patch.dict(os.environ, {"DASHBOARD_SNAPSHOT_TTL_SECONDS": "60"}):
            service = DashboardService(
                news_service=news_service,
                macro_service=macro_service,
                market_service=market_service,
                events_service=events_service,
                prefer_live_data=True,
                enable_background_refresh=False,
            )
            first = service.build_snapshot()
            second = service.build_snapshot()

        self.assertIs(first, second)
        self.assertEqual(news_service.calls, 1)
        self.assertEqual(macro_service.calls, 1)
        self.assertEqual(market_service.calls, 1)
        self.assertEqual(events_service.calls, 1)

    def test_news_module_uses_cached_payload_until_force_refresh(self):
        from src.services.dashboard_service import DashboardService

        class CountingNewsService:
            def __init__(self):
                self.calls = 0

            def build_snapshot(self):
                self.calls += 1
                return SimpleNamespace(domains=[])

        service = DashboardService(
            news_service=CountingNewsService(),
            macro_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(indicators=[])),
            market_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(items=[])),
            events_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(windows=[])),
            enable_background_refresh=False,
        )

        first = service.build_news_module()
        second = service.build_news_module()
        third = service.build_news_module(force_refresh=True)

        self.assertIs(first, second)
        self.assertIsNot(first, third)
        self.assertEqual(service._news_service.calls, 2)

    def test_market_module_uses_cached_payload_until_force_refresh(self):
        from src.services.dashboard_service import DashboardService

        class CountingMarketService:
            def __init__(self):
                self.calls = 0

            def build_snapshot(self):
                self.calls += 1
                return SimpleNamespace(items=[])

        service = DashboardService(
            news_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(domains=[])),
            macro_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(indicators=[])),
            market_service=CountingMarketService(),
            events_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(windows=[])),
            enable_background_refresh=False,
        )

        first = service.build_market_module()
        second = service.build_market_module()
        third = service.build_market_module(force_refresh=True)

        self.assertIs(first, second)
        self.assertIsNot(first, third)
        self.assertEqual(service._market_service.calls, 2)

    def test_macro_module_uses_cached_payload_until_force_refresh(self):
        from src.services.dashboard_service import DashboardService

        class CountingMacroService:
            def __init__(self):
                self.calls = 0

            def build_snapshot(self):
                self.calls += 1
                return SimpleNamespace(indicators=[])

        service = DashboardService(
            news_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(domains=[])),
            macro_service=CountingMacroService(),
            market_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(items=[])),
            events_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(windows=[])),
            enable_background_refresh=False,
        )

        first = service.build_macro_module()
        second = service.build_macro_module()
        third = service.build_macro_module(force_refresh=True)

        self.assertIs(first, second)
        self.assertIsNot(first, third)
        self.assertEqual(service._macro_service.calls, 2)

    def test_events_module_uses_cached_payload_until_force_refresh(self):
        from src.services.dashboard_service import DashboardService

        class CountingEventsService:
            def __init__(self):
                self.calls = 0

            def build_snapshot(self):
                self.calls += 1
                return SimpleNamespace(windows=[])

        service = DashboardService(
            news_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(domains=[])),
            macro_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(indicators=[])),
            market_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(items=[])),
            events_service=CountingEventsService(),
            enable_background_refresh=False,
        )

        first = service.build_events_module()
        second = service.build_events_module()
        third = service.build_events_module(force_refresh=True)

        self.assertIs(first, second)
        self.assertIsNot(first, third)
        self.assertEqual(service._events_service.calls, 2)

    def test_status_module_uses_cached_payload_until_force_refresh(self):
        from src.services.dashboard_service import DashboardService

        service = DashboardService(
            news_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(domains=[])),
            macro_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(indicators=[])),
            market_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(items=[])),
            events_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(windows=[])),
            enable_background_refresh=False,
        )

        first = service.build_status_module()
        second = service.build_status_module()
        third = service.build_status_module(force_refresh=True)

        self.assertIs(first, second)
        self.assertIsNot(first, third)

    def test_live_service_marks_modules_loading_and_starts_background_refresh(self):
        from src.services.dashboard_service import DashboardService

        with (
            patch.object(DashboardService, "prime_caches") as prime_caches,
            patch.object(DashboardService, "_start_background_refresh") as start_background_refresh,
        ):
            service = DashboardService(prefer_live_data=True)

        prime_caches.assert_not_called()
        start_background_refresh.assert_called_once_with()
        self.assertTrue(service.should_serve_loading_module("news"))
        self.assertTrue(service.should_serve_loading_module("macro"))
        self.assertFalse(service.should_serve_loading_module("market"))
        self.assertFalse(service.should_serve_loading_module("events"))

    def test_prime_caches_warms_all_module_variants(self):
        from src.services.dashboard_service import DashboardService

        service = DashboardService(
            news_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(domains=[])),
            macro_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(indicators=[])),
            market_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(items=[])),
            events_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(windows=[])),
            prefer_live_data=True,
            enable_background_refresh=False,
        )

        calls = []

        def fake_build_news_module(*, news_mode=None, force_refresh=False):
            calls.append(("news", news_mode, force_refresh))
            return (
                "2026-03-21T08:00:00Z",
                news_mode or "hybrid",
                [],
                DataStatusItem(key="news", label="News", status="unknown", detail="ok"),
            )

        def fake_build_status_module(*, news_mode=None, force_refresh=False):
            calls.append(("status", news_mode, force_refresh))
            return (
                "2026-03-21T08:00:00Z",
                [DataStatusItem(key="news", label="News", status="unknown", detail="ok")],
                "ok",
            )

        def fake_build_macro_module(*, force_refresh=False):
            calls.append(("macro", None, force_refresh))
            return ("2026-03-21T08:00:00Z", [])

        def fake_build_market_module(*, force_refresh=False):
            calls.append(("market", None, force_refresh))
            return ("2026-03-21T08:00:00Z", [])

        def fake_build_events_module(*, force_refresh=False):
            calls.append(("events", None, force_refresh))
            return ("2026-03-21T08:00:00Z", [])

        service.build_news_module = fake_build_news_module
        service.build_status_module = fake_build_status_module
        service.build_macro_module = fake_build_macro_module
        service.build_market_module = fake_build_market_module
        service.build_events_module = fake_build_events_module

        service.prime_caches()

        self.assertEqual(
            sorted(calls),
            sorted(
                [
                    ("news", "hybrid", False),
                    ("news", "api", False),
                    ("news", "upstream", False),
                    ("status", "hybrid", False),
                    ("status", "api", False),
                    ("status", "upstream", False),
                    ("macro", None, False),
                    ("market", None, False),
                    ("events", None, False),
                ]
            ),
        )

    def test_background_refresh_uses_non_forced_startup_prime(self):
        from src.services.dashboard_service import DashboardService

        service = DashboardService(
            news_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(domains=[])),
            macro_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(indicators=[])),
            market_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(items=[])),
            events_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(windows=[])),
            prefer_live_data=True,
            enable_background_refresh=False,
        )
        service._prime_live_caches_on_startup = True

        with (
            patch.object(service, "prime_caches") as prime_caches,
            patch.object(service._refresh_stop_event, "is_set", side_effect=[False, True]),
            patch.object(service._refresh_stop_event, "wait", return_value=True),
        ):
            service._background_refresh_loop()

        prime_caches.assert_called_once_with(force_refresh=False)

    def test_news_view_uses_media_name_and_provider_specific_tag(self):
        from src.services.dashboard_service import DashboardService

        service = DashboardService(
            news_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(domains=[])),
            macro_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(indicators=[])),
            market_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(items=[])),
            events_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(windows=[])),
            enable_background_refresh=False,
        )

        sections = service._build_news_sections_from_snapshot(
            SimpleNamespace(
                domains=[
                    SimpleNamespace(
                        category=NewsCategory.TECHNOLOGY,
                        candidate_count=1,
                        merged_duplicate_count=0,
                        dropped_outdated_count=0,
                        items=[
                            SimpleNamespace(
                                title="headline",
                                source_name="IT之家",
                                url="https://example.com/news",
                                published_at="2026-03-22T00:00:00Z",
                                source_type=SimpleNamespace(value="rss"),
                                source_tag="realtime",
                            )
                        ],
                    )
                ]
            )
        )

        self.assertEqual(sections[0].items[0].source, "IT之家")
        self.assertEqual(sections[0].items[0].tag, "live")
        self.assertEqual(sections[0].items[0].summary, "")

    def test_news_view_falls_back_to_raw_summary_from_pipeline_items(self):
        from src.services.dashboard_service import DashboardService

        service = DashboardService(
            news_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(domains=[])),
            macro_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(indicators=[])),
            market_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(items=[])),
            events_service=SimpleNamespace(build_snapshot=lambda: SimpleNamespace(windows=[])),
            enable_background_refresh=False,
        )

        sections = service._build_news_sections_from_snapshot(
            SimpleNamespace(
                domains=[
                    SimpleNamespace(
                        category=NewsCategory.TECHNOLOGY,
                        candidate_count=1,
                        merged_duplicate_count=0,
                        dropped_outdated_count=0,
                        items=[
                            SimpleNamespace(
                                title="headline",
                                source_name="IT之家",
                                url="https://example.com/news",
                                published_at="2026-03-22T00:00:00Z",
                                source_type=SimpleNamespace(value="rss"),
                                source_tag="realtime",
                                raw_summary="pipeline summary",
                            )
                        ],
                    )
                ]
            )
        )

        self.assertEqual(sections[0].items[0].summary, "pipeline summary")


class NewsNowUpstreamManagerTests(unittest.TestCase):
    def test_failed_start_enters_cooldown_and_does_not_restart_immediately(self):
        manager = _NewsNowUpstreamServerManager()
        start_calls = 0

        def fake_start_process(*, base_url):
            nonlocal start_calls
            start_calls += 1
            raise RuntimeError("boom")

        with (
            patch.dict(
                os.environ,
                {
                    "NEWSNOW_UPSTREAM_START_TIMEOUT_SECONDS": "0.1",
                    "NEWSNOW_UPSTREAM_RETRY_COOLDOWN_SECONDS": "60",
                },
            ),
            patch.object(manager, "_is_healthy", return_value=False),
            patch.object(manager, "_start_process", side_effect=fake_start_process),
        ):
            with self.assertRaisesRegex(RuntimeError, "start failed"):
                manager.ensure_running(base_url="http://127.0.0.1:5173")
            with self.assertRaisesRegex(RuntimeError, "start failed"):
                manager.ensure_running(base_url="http://127.0.0.1:5173")

        self.assertEqual(start_calls, 1)

    def test_upstream_provider_can_disable_native_fallback_after_fetch_failure(self):
        provider = NewsNowAggregatedNewsProvider(
            base_url="http://127.0.0.1:5173",
            source_specs=(),
            enable_native_fallback=False,
        )

        with (
            patch.object(provider, "_fetch_source", side_effect=RuntimeError("boom")),
            patch.object(provider, "_fetch_native_source_items") as native_fallback,
        ):
            with self.assertRaisesRegex(RuntimeError, "boom"):
                provider._fetch_or_reuse_source(
                    SimpleNamespace(source_id="demo", interval_ms=0),
                )

        native_fallback.assert_not_called()


class LiveProviderResilienceTests(unittest.TestCase):
    def test_macro_provider_skips_failed_indicator_and_returns_remaining_readings(self):
        provider = AkshareMacroDataProvider()

        class FakeAkshare:
            @staticmethod
            def macro_china_cpi_yearly():
                return pd.DataFrame(
                    [
                        {"月份": "2025-12", "同比": 0.1},
                        {"月份": "2026-01", "同比": 0.3},
                    ]
                )

            @staticmethod
            def macro_china_shrzgm():
                raise RuntimeError("ssl handshake failed")

        with patch.object(provider, "_load_akshare", return_value=FakeAkshare()):
            readings = provider.fetch_latest_readings(indicator_codes=["cpi", "social_financing"])

        self.assertEqual([item.indicator_code for item in readings], ["cpi"])

    def test_market_provider_skips_failed_symbol_and_filters_unsupported_kwargs(self):
        provider = AkshareMarketDataProvider()

        class FakeAkshare:
            @staticmethod
            def stock_zh_index_daily_em(symbol: str, start_date: str, end_date: str):
                self.assertEqual(symbol, "sh000300")
                self.assertEqual(start_date, "20250922")
                self.assertEqual(end_date, "20260321")
                return pd.DataFrame(
                    [
                        {"date": "2026-03-20", "close": 3999.0},
                        {"date": "2026-03-21", "close": 4001.0},
                    ]
                )

            @staticmethod
            def stock_hk_index_daily_em(symbol: str):
                raise RuntimeError("proxy unavailable")

        with patch.object(provider, "_load_akshare", return_value=FakeAkshare()):
            snapshots = provider.fetch_index_snapshots(
                symbols=["CSI300", "HSTECH"],
                trade_date=date(2026, 3, 21),
            )

        self.assertEqual([item.symbol for item in snapshots], ["CSI300"])
        self.assertEqual(snapshots[0].close_price, 4001.0)
        self.assertEqual(len(snapshots[0].history_points), 2)

    def test_market_provider_fetches_hstech_from_sina_daily_source(self):
        provider = AkshareMarketDataProvider()

        class FakeAkshare:
            @staticmethod
            def stock_hk_index_daily_sina(symbol: str):
                self.assertEqual(symbol, "HSTECH")
                return pd.DataFrame(
                    [
                        {"date": "2026-03-20", "close": 3918.0},
                        {"date": "2026-03-21", "close": 3932.0},
                    ]
                )

        with patch.object(provider, "_load_akshare", return_value=FakeAkshare()):
            snapshots = provider.fetch_index_snapshots(
                symbols=["HSTECH"],
                trade_date=date(2026, 3, 21),
            )

        self.assertEqual([item.symbol for item in snapshots], ["HSTECH"])
        self.assertEqual(snapshots[0].close_price, 3932.0)
        self.assertEqual(snapshots[0].currency, "HKD")
        self.assertEqual(len(snapshots[0].history_points), 2)


if __name__ == "__main__":
    unittest.main()
