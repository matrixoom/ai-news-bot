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


class EmptyResearchProvider:
    """提供测试用研究 provider，避免静态日历触发外部依赖。"""

    def collect_outlook(self, **_: object) -> list[object]:
        """返回空采集结果。"""
        return []

    def healthcheck(self) -> object:
        """返回轻量健康对象。"""
        return object()


class EventInsightApiTests(unittest.TestCase):
    """校验 Event Insight 事件列表工作台 API。"""

    def setUp(self) -> None:
        self.temp_dir = Path(".tmp-events-tests") / "event-insight-api" / self.id().split(".")[-1]
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
        self.client = TestClient(
            create_fastapi_app(
                event_insight_import_service=self.import_service,
                event_insight_job_service=self.job_service,
                event_insight_service=self.event_service,
                event_outlook_service=EventsOutlookService(
                    research_provider=EmptyResearchProvider(),
                    store=EventsOutlookStore(self.temp_dir / "events_outlook.db"),
                ),
            )
        )
        self.document_id = self.repository.create_raw_document(
            source_type="news",
            title="存储芯片报价上调",
            content_text="DRAM 合约价上涨，AI 服务器需求支撑内存涨价。",
            content_hash="api-doc-1",
            url="https://example.com/memory",
        )
        self.evidence_id = self.repository.create_evidence(
            raw_document_id=self.document_id,
            excerpt="DRAM 合约价上涨，AI 服务器需求支撑内存涨价。",
            evidence_level="B",
        )
        self.event_id = self.repository.create_event(
            title="存储芯片报价上调",
            summary="DRAM 合约价上涨，AI 服务器需求支撑内存涨价。",
            event_time="2026-05-16T10:30:00+08:00",
            event_type="price_change",
            confidence_score=0.82,
        )
        self.repository.link_event_evidence(event_id=self.event_id, evidence_id=self.evidence_id, role="primary")
        self.other_event_id = self.repository.create_event(
            title="CPO 光模块订单增加",
            summary="海外云厂商资本开支上修。",
            event_time="2026-05-20T10:30:00+08:00",
            event_type="supply_demand",
            confidence_score=0.76,
        )

    def tearDown(self) -> None:
        self.client.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_list_events_returns_filtered_paginated_payload(self) -> None:
        """校验事件列表支持筛选、分页和 traceId。"""
        response = self.client.get("/api/frontend/modules/event-insight/events?keyword=DRAM&page=1&pageSize=10")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["pageSize"], 10)
        self.assertEqual(payload["total"], 1)
        self.assertTrue(payload["traceId"].startswith("event-insight-events-"))
        self.assertEqual(payload["items"][0]["id"], self.event_id)
        self.assertEqual(payload["items"][0]["title"], "存储芯片报价上调")
        self.assertEqual(payload["items"][0]["eventType"], "price_change")

    def test_event_detail_returns_evidence_and_topics(self) -> None:
        """校验详情接口返回证据链和主题归属。"""
        topic_response = self.client.post(
            "/api/frontend/modules/event-insight/topics",
            json={"name": "内存涨价", "summary": "围绕存储芯片供需变化。"},
        )
        topic_id = topic_response.json()["topic"]["id"]
        self.client.post(
            f"/api/frontend/modules/event-insight/events/{self.event_id}/link-topic",
            json={"topicId": topic_id, "roleInTopic": "key_catalyst"},
        )

        response = self.client.get(f"/api/frontend/modules/event-insight/events/{self.event_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["event"]["id"], self.event_id)
        self.assertEqual(payload["event"]["topics"][0]["name"], "内存涨价")
        self.assertEqual(payload["event"]["evidence"][0]["excerpt"], "DRAM 合约价上涨，AI 服务器需求支撑内存涨价。")

    def test_topic_trace_returns_metrics_stages_and_timeline(self) -> None:
        """校验主题溯源接口返回真实关联事件、指标和阶段。"""
        topic_response = self.client.post(
            "/api/frontend/modules/event-insight/topics",
            json={"name": "内存涨价", "summary": "围绕存储芯片供需变化。"},
        )
        topic_id = topic_response.json()["topic"]["id"]
        self.client.post(
            f"/api/frontend/modules/event-insight/events/{self.event_id}/link-topic",
            json={"topicId": topic_id, "roleInTopic": "key_catalyst"},
        )
        self.client.post(
            f"/api/frontend/modules/event-insight/events/{self.other_event_id}/link-topic",
            json={"topicId": topic_id, "roleInTopic": "supporting_event"},
        )

        response = self.client.get(f"/api/frontend/modules/event-insight/topics/{topic_id}/trace")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["traceId"].startswith("event-insight-topic-trace-"))
        self.assertEqual(payload["topic"]["id"], topic_id)
        self.assertEqual(payload["metrics"][0]["label"], "主题事件")
        self.assertEqual(payload["metrics"][0]["value"], "2")
        self.assertEqual(payload["stages"][-1]["title"], "CPO 光模块订单增加")
        self.assertTrue(payload["stages"][-1]["active"])
        self.assertEqual(payload["timeline"][0]["title"], "CPO 光模块订单增加")
        self.assertEqual(payload["timeline"][1]["evidence"][0]["excerpt"], "DRAM 合约价上涨，AI 服务器需求支撑内存涨价。")

    def test_topic_trace_returns_404_for_missing_topic(self) -> None:
        """校验主题不存在时返回稳定错误码。"""
        response = self.client.get("/api/frontend/modules/event-insight/topics/9999/trace")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "event_insight_topic_not_found")

    def test_update_event_records_override_without_losing_original_fact(self) -> None:
        """校验编辑事件会写人工覆盖，并返回更新后的展示值。"""
        response = self.client.put(
            f"/api/frontend/modules/event-insight/events/{self.event_id}",
            json={
                "title": "DRAM 合约价延续上涨",
                "summary": "多来源确认内存涨价。",
                "eventType": "price_change",
                "confidenceScore": 0.9,
                "reason": "人工确认",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["event"]["title"], "DRAM 合约价延续上涨")
        original = self.repository.get_event(self.event_id)
        overrides = self.repository.list_event_field_overrides(self.event_id)
        self.assertEqual(original["title"], "存储芯片报价上调")
        self.assertIn("title", {override["field_name"] for override in overrides})

    def test_ignore_event_soft_hides_from_default_list(self) -> None:
        """校验忽略事件后默认列表不再返回该事件。"""
        response = self.client.post(
            f"/api/frontend/modules/event-insight/events/{self.event_id}/ignore",
            json={"reason": "重复新闻或低价值噪声"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["event"]["manualStatus"], "ignored")

        list_response = self.client.get("/api/frontend/modules/event-insight/events")

        ids = [item["id"] for item in list_response.json()["items"]]
        self.assertNotIn(self.event_id, ids)

    def test_batch_action_returns_partial_success(self) -> None:
        """校验批量操作逐项返回结果，不因单条失败吞掉成功项。"""
        response = self.client.post(
            "/api/frontend/modules/event-insight/events/batch-action",
            json={"eventIds": [self.event_id, 9999], "action": "ignore", "params": {"reason": "批量忽略"}},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["succeededEventIds"], [self.event_id])
        self.assertEqual(payload["failedItems"][0]["eventId"], 9999)
        self.assertEqual(payload["failedItems"][0]["error"], "event_not_found")

    def test_event_outlook_static_calendar_still_works(self) -> None:
        """校验新增事件洞察 API 不影响未来事件静态日历。"""
        response = self.client.get("/api/frontend/modules/event-outlook?region=domestic&refresh=1")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["module"]["id"], "event-outlook")
        self.assertEqual(payload["region"], "domestic")


if __name__ == "__main__":
    unittest.main()
