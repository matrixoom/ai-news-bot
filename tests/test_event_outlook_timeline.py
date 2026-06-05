import sqlite3
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from src.app.web import create_fastapi_app
from src.services.events_outlook_service import EventsOutlookService
from src.services.events_outlook_store import EventsOutlookStore


class EmptyResearchProvider:
    """提供测试用研究 provider；时间轴接口不依赖外部采集结果。"""

    def collect_outlook(self, **_: object) -> list[object]:
        """返回空采集结果，避免测试触发外部依赖。"""
        return []

    def healthcheck(self) -> object:
        """返回简单健康状态对象，满足服务初始化依赖。"""
        return object()


class EventOutlookTimelineStoreTests(unittest.TestCase):
    """校验 Outlook 时间轴事件会持久化到本地 SQLite。"""

    def setUp(self) -> None:
        self.db_path = Path(".tmp-events-tests") / "event-outlook" / f"{self.id().split('.')[-1]}.db"
        if self.db_path.exists():
            self.db_path.unlink()
        self.store = EventsOutlookStore(self.db_path)

    def test_store_initializes_timeline_events_table(self) -> None:
        """校验初始化会创建时间轴事件表和日期索引。"""
        with sqlite3.connect(self.db_path) as connection:
            table_names = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            index_names = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                ).fetchall()
            }

        self.assertIn("timeline_events", table_names)
        self.assertIn("idx_timeline_events_region_date", index_names)

    def test_manual_event_round_trips_through_store(self) -> None:
        """校验手工录入事件可按区域和日期范围读取。"""
        created = self.store.create_timeline_event(
            region="domestic",
            event_date="2026-11-18",
            title="APEC 领导人非正式会议",
            summary="会议将在深圳举行，关注开放、创新、合作等议题。",
            category="politics",
            source_url="https://english.www.gov.cn/news/202512/12/content_WS693c1432c6d00ca5f9a080e6.html",
            source_name="中国政府网",
        )

        events = self.store.list_timeline_events(
            region="domestic",
            start_date="2026-05-05",
            end_date="2027-05-05",
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].id, created.id)
        self.assertEqual(events[0].title, "APEC 领导人非正式会议")
        self.assertEqual(events[0].summary, "会议将在深圳举行，关注开放、创新、合作等议题。")
        self.assertEqual(events[0].source_name, "中国政府网")

    def test_finance_event_round_trips_through_store(self) -> None:
        """校验财经事件分类可被 SQLite 约束接受并持久化。"""
        created = self.store.create_timeline_event(
            region="international",
            event_date="2026-10-12",
            title="IMF/World Bank Annual Meetings",
            summary="关注全球经济、金融市场与发展融资议题。",
            category="finance",
            source_url="https://www.worldbank.org/en/meetings/splash/annual",
            source_name="World Bank Group",
        )

        stored = EventsOutlookStore(self.db_path).get_timeline_event(created.id)

        self.assertIsNotNone(stored)
        self.assertEqual(stored.category, "finance")

    def test_update_event_persists_title_and_summary(self) -> None:
        """校验编辑标题和摘要后重新打开数据库仍可读取新值。"""
        created = self.store.create_timeline_event(
            region="international",
            event_date="2026-06-08",
            title="WWDC26",
            summary="Apple 年度开发者大会。",
            category="technology",
            source_url="https://developer.apple.com/news/?id=yi8qj25k",
            source_name="Apple Developer",
        )

        updated = self.store.update_timeline_event(
            event_id=created.id,
            title="Apple WWDC26",
            summary="聚焦 Apple 平台软件、AI 与开发者工具更新。",
        )
        reopened = EventsOutlookStore(self.db_path).get_timeline_event(created.id)

        self.assertIsNotNone(updated)
        self.assertIsNotNone(reopened)
        self.assertEqual(reopened.title, "Apple WWDC26")
        self.assertEqual(reopened.summary, "聚焦 Apple 平台软件、AI 与开发者工具更新。")


class EventOutlookTimelineApiTests(unittest.TestCase):
    """校验前端 Outlook API 契约。"""

    def setUp(self) -> None:
        self.db_path = Path(".tmp-events-tests") / "event-outlook-api" / f"{self.id().split('.')[-1]}.db"
        if self.db_path.exists():
            self.db_path.unlink()
        self.store = EventsOutlookStore(self.db_path)
        service = EventsOutlookService(
            research_provider=EmptyResearchProvider(),
            store=self.store,
            now_factory=lambda: datetime(2026, 5, 5, 12, 0, tzinfo=UTC),
        )
        self.client = TestClient(create_fastapi_app(event_outlook_service=service))

    def test_module_endpoint_seeds_and_filters_domestic_events(self) -> None:
        """校验模块接口刷新后返回未来一年内的国内科技、时政与财经事件。"""
        response = self.client.get("/api/frontend/modules/event-outlook?region=domestic&refresh=1")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["module"]["id"], "event-outlook")
        self.assertEqual(payload["region"], "domestic")
        self.assertEqual(payload["range"]["start_date"], "2026-05-05")
        self.assertEqual(payload["range"]["end_date"], "2027-05-05")
        titles = [event["title"] for event in payload["events"]]
        self.assertIn("COMPUTEX 2026", titles)
        self.assertIn("夏季达沃斯 2026", titles)
        self.assertIn("APEC 领导人非正式会议", titles)
        self.assertTrue(all(event["region"] == "domestic" for event in payload["events"]))
        self.assertIn("finance", {event["category"] for event in payload["events"]})

    def test_module_endpoint_returns_international_events(self) -> None:
        """校验国际标签返回未来一年内的国际科技、时政与财经日程。"""
        response = self.client.get("/api/frontend/modules/event-outlook?region=international&refresh=1")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        titles = [event["title"] for event in payload["events"]]
        self.assertIn("Google I/O 2026", titles)
        self.assertIn("FOMC 利率会议", titles)
        self.assertIn("NATO Summit 2026", titles)
        self.assertTrue(all(event["region"] == "international" for event in payload["events"]))
        self.assertIn("finance", {event["category"] for event in payload["events"]})

    def test_create_event_rejects_invalid_region(self) -> None:
        """校验手工录入会快速拒绝非法区域。"""
        response = self.client.post(
            "/api/frontend/modules/event-outlook/events",
            json={
                "region": "space",
                "event_date": "2026-07-01",
                "title": "Invalid",
                "summary": "Invalid",
                "category": "technology",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_event_outlook_payload")

    def test_create_and_update_event_are_persistent(self) -> None:
        """校验手工录入和编辑接口都写入 SQLite。"""
        create_response = self.client.post(
            "/api/frontend/modules/event-outlook/events",
            json={
                "region": "domestic",
                "event_date": "2026-09-11",
                "title": "自定义科技发布",
                "summary": "跟踪重点公司新品发布时间。",
                "category": "technology",
                "source_name": "manual",
                "source_url": "",
            },
        )

        self.assertEqual(create_response.status_code, 201)
        event_id = create_response.json()["event"]["id"]

        update_response = self.client.put(
            f"/api/frontend/modules/event-outlook/events/{event_id}",
            json={
                "title": "自定义科技发布节点",
                "summary": "跟踪重点公司新品发布和供应链影响。",
            },
        )

        self.assertEqual(update_response.status_code, 200)
        stored = self.store.get_timeline_event(event_id)
        self.assertIsNotNone(stored)
        self.assertEqual(stored.title, "自定义科技发布节点")
        self.assertEqual(stored.summary, "跟踪重点公司新品发布和供应链影响。")


if __name__ == "__main__":
    unittest.main()
