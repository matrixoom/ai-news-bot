import shutil
import unittest
from pathlib import Path

from src.services.event_insight_repository import EventInsightRepository
from src.services.event_retrieval_service import EventRetrievalService


class EventRetrievalServiceTests(unittest.TestCase):
    """校验事件检索、重复候选和主题聚类。"""

    def setUp(self) -> None:
        self.temp_dir = Path(".tmp-events-tests") / "event-retrieval" / self.id().split(".")[-1]
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.repository = EventInsightRepository(self.temp_dir / "event_insight.db")
        self.memory_event_id = self.repository.create_event(
            title="存储芯片报价上调",
            summary="DRAM 合约价上涨，AI 服务器需求支撑内存涨价。",
            event_time="2026-05-16T10:30:00+08:00",
            event_type="price_change",
            confidence_score=0.86,
        )
        self.duplicate_event_id = self.repository.create_event(
            title="DRAM 合约价格继续上涨",
            summary="内存价格受 AI 服务器需求支撑。",
            event_time="2026-05-17T10:30:00+08:00",
            event_type="price_change",
            confidence_score=0.82,
        )
        self.cpo_event_id = self.repository.create_event(
            title="CPO 光模块订单增加",
            summary="海外云厂商资本开支上修。",
            event_time="2026-05-20T10:30:00+08:00",
            event_type="supply_demand",
            confidence_score=0.76,
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_chinese_ngram_search_recalls_memory_event(self) -> None:
        """校验中文短词可通过 n-gram fallback 召回。"""
        service = EventRetrievalService(self.repository)

        result = service.search_events("内存涨价")

        ids = [item["id"] for item in result["items"]]
        self.assertIn(self.memory_event_id, ids)
        self.assertNotIn(self.cpo_event_id, ids)

    def test_duplicate_candidates_are_non_destructive(self) -> None:
        """校验重复候选只写 candidate，不合并或删除事件。"""
        service = EventRetrievalService(self.repository)

        result = service.generate_duplicate_candidates(self.memory_event_id, threshold=0.2)

        self.assertEqual(result["sourceEventId"], self.memory_event_id)
        self.assertIn(self.duplicate_event_id, [item["candidateEventId"] for item in result["candidates"]])
        self.assertEqual(self.repository.get_event(self.duplicate_event_id)["manual_status"], "active")

    def test_cluster_events_links_matching_events_to_topic(self) -> None:
        """校验规则聚类只创建主题并关联匹配事件。"""
        service = EventRetrievalService(self.repository)

        result = service.cluster_events(keyword="DRAM", topic_name="内存涨价")

        self.assertEqual(result["topic"]["name"], "内存涨价")
        self.assertGreaterEqual(len(result["linkedEventIds"]), 2)
        self.assertEqual(self.repository.get_event(self.memory_event_id)["manual_status"], "active")

    def test_vector_runtime_probe_is_non_blocking(self) -> None:
        """校验 sqlite-vec 探测只返回状态，不阻断基础服务初始化。"""
        service = EventRetrievalService(self.repository)

        result = service.inspect_vector_runtime()

        self.assertIn("available", result)
        self.assertIn("reason", result)


if __name__ == "__main__":
    unittest.main()
