import shutil
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.app.web import create_fastapi_app
from src.services.event_insight_import_service import EventInsightImportService
from src.services.event_insight_job_service import EventInsightJobService
from src.services.event_insight_repository import EventInsightRepository
from src.services.event_insight_service import EventInsightService
from src.services.events_outlook_service import EventsOutlookService
from src.services.events_outlook_store import EventsOutlookStore
from src.services.rss_config_service import RssConfigService


class EmptyResearchProvider:
    """提供测试用研究 provider，避免静态日历触发外部依赖。"""

    def collect_outlook(self, **_: object) -> list[object]:
        """返回空采集结果。"""
        return []

    def healthcheck(self) -> object:
        """返回轻量健康对象。"""
        return object()


class FakeRssFetcher:
    """提供确定性 RSS 抓取结果，避免测试访问外网。"""

    def __init__(self) -> None:
        """初始化测试抓取记录。"""
        self.called_urls: list[str] = []

    def fetch_rss_feed(self, feed_url: str, max_items: int = 10) -> list[dict[str, str]]:
        """返回固定 RSS 条目并记录被调用 URL。"""
        self.called_urls.append(feed_url)
        return [
            {
                "title": "AI 服务器拉动存储芯片需求",
                "link": "https://example.com/rss-memory",
                "description": "DRAM 合约价继续上修，AI 服务器需求维持高位。",
                "published": "Wed, 03 Jun 2026 08:00:00 GMT",
            }
        ][:max_items]


class RssSettingsApiTests(unittest.TestCase):
    """校验 System RSS 配置和 Event Insight 入库链路。"""

    def setUp(self) -> None:
        self.temp_dir = Path(".tmp-events-tests") / "rss-settings-api" / self.id().split(".")[-1]
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.repository = EventInsightRepository(self.temp_dir / "event_insight.db")
        self.job_service = EventInsightJobService(self.repository)
        self.import_service = EventInsightImportService(
            repository=self.repository,
            job_service=self.job_service,
            storage_root=self.temp_dir / "storage",
        )
        self.event_service = EventInsightService(self.repository)
        self.fetcher = FakeRssFetcher()
        self.rss_service = RssConfigService(repository=self.repository, fetcher=self.fetcher)
        self.client = TestClient(
            create_fastapi_app(
                event_insight_import_service=self.import_service,
                event_insight_job_service=self.job_service,
                event_insight_service=self.event_service,
                rss_config_service=self.rss_service,
                event_outlook_service=EventsOutlookService(
                    research_provider=EmptyResearchProvider(),
                    store=EventsOutlookStore(self.temp_dir / "events_outlook.db"),
                ),
            )
        )

    def tearDown(self) -> None:
        self.client.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_rss_source_crud_and_manual_fetch_creates_event_insight_event(self) -> None:
        """校验 RSS 源可配置、可抓取，并把新闻事件写入事件列表。"""
        defaults_response = self.client.get("/api/system/rss/sources")
        self.assertEqual(defaults_response.status_code, 200)
        default_names = {item["name"] for item in defaults_response.json()["sources"]}
        self.assertIn("TechCrunch AI", default_names)
        self.assertIn("JiQiZhiXin (机器之心)", default_names)

        create_response = self.client.post(
            "/api/system/rss/sources",
            json={
                "name": "AI 财经观察",
                "url": "https://example.com/rss.xml",
                "language": "zh",
                "category": "finance",
                "enabled": True,
                "fetchTime": "06:30",
                "maxItems": 5,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        source = create_response.json()["source"]
        self.assertEqual(source["fetchTime"], "06:30")

        update_response = self.client.put(
            f"/api/system/rss/sources/{source['id']}",
            json={
                "name": "AI 财经观察更新",
                "url": "https://example.com/rss.xml",
                "language": "zh",
                "category": "finance",
                "enabled": True,
                "fetchTime": "07:45",
                "maxItems": 3,
            },
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["source"]["name"], "AI 财经观察更新")

        fetch_response = self.client.post(f"/api/system/rss/sources/{source['id']}/fetch")
        self.assertEqual(fetch_response.status_code, 200)
        self.assertEqual(fetch_response.json()["importedCount"], 1)
        self.assertEqual(self.fetcher.called_urls, ["https://example.com/rss.xml"])

        events_response = self.client.get("/api/frontend/modules/event-insight/events?keyword=存储芯片")
        self.assertEqual(events_response.status_code, 200)
        events = events_response.json()["items"]
        self.assertEqual(events[0]["title"], "AI 服务器拉动存储芯片需求")
        self.assertEqual(events[0]["sourceMethod"], "rss")

        delete_response = self.client.delete(f"/api/system/rss/sources/{source['id']}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(delete_response.json()["source"]["enabled"])

        list_response = self.client.get("/api/system/rss/sources")
        self.assertEqual(list_response.status_code, 200)
        visible_names = {item["name"] for item in list_response.json()["sources"]}
        self.assertNotIn("AI 财经观察更新", visible_names)

    def test_rss_scheduler_settings_are_persisted(self) -> None:
        """校验 RSS 全局调度设置可在 System 页面持久化。"""
        response = self.client.put(
            "/api/system/rss/scheduler",
            json={"enabled": True, "timezone": "Asia/Shanghai", "dailyFetchTime": "05:15"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["scheduler"]["dailyFetchTime"], "05:15")

        list_response = self.client.get("/api/system/rss/sources")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["scheduler"]["timezone"], "Asia/Shanghai")


if __name__ == "__main__":
    unittest.main()
