import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.app.web import create_fastapi_app
from src.app.web.frontend_payload import build_frontend_payload
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

    def test_root_renders_named_dashboard_panels(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("财经与政策情报终端", response.text)
        self.assertIn("热点新闻追踪", response.text)
        self.assertIn("数据状态", response.text)

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


if __name__ == "__main__":
    unittest.main()
