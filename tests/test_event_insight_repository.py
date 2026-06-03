import sqlite3
import unittest
from pathlib import Path

from src.services.event_insight_repository import EventInsightRepository


class EventInsightRepositoryTests(unittest.TestCase):
    """校验 Event Insight 独立 SQLite 事实库的迁移和基础仓储能力。"""

    def setUp(self) -> None:
        self.db_path = Path(".tmp-events-tests") / "event-insight" / f"{self.id().split('.')[-1]}.db"
        if self.db_path.exists():
            self.db_path.unlink()

    def test_repository_applies_core_migration_idempotently(self) -> None:
        """校验初始化会创建全部核心表，重复初始化不会重复写 migration。"""
        repository = EventInsightRepository(self.db_path)
        reopened = EventInsightRepository(self.db_path)

        table_names = reopened.list_table_names()
        migrations = reopened.list_applied_migrations()

        self.assertEqual(migrations, ["001_event_insight_core"])
        self.assertIn("schema_migration", table_names)
        self.assertIn("scan_batch", table_names)
        self.assertIn("analysis_run", table_names)
        self.assertIn("raw_document", table_names)
        self.assertIn("raw_document_fts", table_names)
        self.assertIn("event", table_names)
        self.assertIn("event_fts", table_names)
        self.assertIn("event_source", table_names)
        self.assertIn("evidence", table_names)
        self.assertIn("event_evidence", table_names)
        self.assertIn("entity", table_names)
        self.assertIn("entity_alias", table_names)
        self.assertIn("event_entity", table_names)
        self.assertIn("topic", table_names)
        self.assertIn("topic_event", table_names)
        self.assertIn("event_relation", table_names)
        self.assertIn("relation_evidence", table_names)
        self.assertIn("event_operation_log", table_names)
        self.assertIn("event_field_override", table_names)
        self.assertIn("duplicate_event_candidate", table_names)
        self.assertIn("processing_job", table_names)
        self.assertIn("processing_job_attempt", table_names)
        self.assertIn("graph_sync_outbox", table_names)
        self.assertIn("graph_projection_state", table_names)
        self.assertEqual(repository.list_applied_migrations(), ["001_event_insight_core"])

    def test_connections_enable_foreign_keys_and_wal(self) -> None:
        """校验仓储连接默认启用外键约束和 WAL。"""
        repository = EventInsightRepository(self.db_path)

        pragmas = repository.inspect_pragmas()

        self.assertEqual(pragmas["foreign_keys"], 1)
        self.assertEqual(pragmas["journal_mode"], "wal")

    def test_foreign_keys_reject_invalid_event_evidence_links(self) -> None:
        """校验证据链关联必须引用已存在的事件和证据。"""
        repository = EventInsightRepository(self.db_path)

        with self.assertRaises(sqlite3.IntegrityError):
            repository.link_event_evidence(event_id=404, evidence_id=505, role="primary")

    def test_raw_document_fts_tracks_insert_update_and_archive(self) -> None:
        """校验原始材料 FTS 会跟随写入、更新和归档状态变化。"""
        repository = EventInsightRepository(self.db_path)
        document_id = repository.create_raw_document(
            source_type="news",
            title="存储芯片报价上调",
            content_text="DRAM 合约价上涨，AI 服务器需求支撑内存涨价。",
            content_hash="doc-memory-price",
        )

        self.assertEqual(repository.search_raw_documents("DRAM"), [document_id])

        repository.update_raw_document_content(
            document_id=document_id,
            title="HBM4 量产节奏提前",
            content_text="先进封装产能继续吃紧。",
        )

        self.assertEqual(repository.search_raw_documents("HBM4"), [document_id])
        self.assertEqual(repository.search_raw_documents("DRAM"), [])

        repository.archive_raw_document(document_id=document_id, reason="low value")

        self.assertEqual(repository.search_raw_documents("HBM4"), [])

    def test_event_fts_tracks_insert_update_and_archive(self) -> None:
        """校验事件 FTS 会跟随事件摘要更新和软归档变化。"""
        repository = EventInsightRepository(self.db_path)
        event_id = repository.create_event(
            title="DRAM 合约价上调",
            summary="AI 服务器需求支撑内存涨价。",
            event_time="2026-05-16T10:30:00+08:00",
            event_type="price_change",
            confidence_score=0.82,
        )

        self.assertEqual(repository.search_events("DRAM"), [event_id])

        repository.update_event_summary(
            event_id=event_id,
            title="HBM4 量产节奏提前",
            summary="先进封装产能继续吃紧。",
        )

        self.assertEqual(repository.search_events("HBM4"), [event_id])
        self.assertEqual(repository.search_events("DRAM"), [])

        repository.archive_event(event_id=event_id, reason="duplicate")

        self.assertEqual(repository.search_events("HBM4"), [])

    def test_field_overrides_are_stored_independently_from_model_facts(self) -> None:
        """校验人工字段覆盖不直接改写模型抽取事实。"""
        repository = EventInsightRepository(self.db_path)
        event_id = repository.create_event(
            title="模型标题",
            summary="模型摘要",
            event_time="2026-05-16T10:30:00+08:00",
            event_type="price_change",
            confidence_score=0.72,
        )

        repository.create_event_field_override(
            event_id=event_id,
            field_name="title",
            override_value="人工校正标题",
            reason="标题需要更具体",
            operator="unit-test",
        )

        event = repository.get_event(event_id)
        overrides = repository.list_event_field_overrides(event_id)

        self.assertIsNotNone(event)
        self.assertEqual(event["title"], "模型标题")
        self.assertEqual(overrides[0]["field_name"], "title")
        self.assertEqual(overrides[0]["override_value"], "人工校正标题")
        self.assertEqual(overrides[0]["operator"], "unit-test")

    def test_duplicate_candidates_retain_source_and_candidate_events(self) -> None:
        """校验重复候选会保留来源事件、候选事件、分数和方法。"""
        repository = EventInsightRepository(self.db_path)
        source_event_id = repository.create_event(
            title="存储芯片报价上调",
            summary="DRAM 合约价上涨。",
            event_time="2026-05-16T10:30:00+08:00",
            event_type="price_change",
            confidence_score=0.82,
        )
        candidate_event_id = repository.create_event(
            title="DRAM 合约价延续上涨",
            summary="内存涨价趋势被多家渠道确认。",
            event_time="2026-05-16T11:00:00+08:00",
            event_type="price_change",
            confidence_score=0.8,
        )

        repository.create_duplicate_event_candidate(
            source_event_id=source_event_id,
            candidate_event_id=candidate_event_id,
            score=0.91,
            method="weighted_similarity_v1",
        )

        candidates = repository.list_duplicate_event_candidates(source_event_id)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["source_event_id"], source_event_id)
        self.assertEqual(candidates[0]["candidate_event_id"], candidate_event_id)
        self.assertEqual(candidates[0]["score"], 0.91)
        self.assertEqual(candidates[0]["method"], "weighted_similarity_v1")

    def test_graph_outbox_idempotency_key_prevents_duplicate_projection_work(self) -> None:
        """校验图谱 outbox 使用幂等键避免重复投影任务。"""
        repository = EventInsightRepository(self.db_path)

        first_id = repository.enqueue_graph_sync(
            aggregate_type="event",
            aggregate_id=100,
            operation="upsert",
            payload_json='{"id": 100}',
            idempotency_key="event:100:upsert",
        )
        second_id = repository.enqueue_graph_sync(
            aggregate_type="event",
            aggregate_id=100,
            operation="upsert",
            payload_json='{"id": 100}',
            idempotency_key="event:100:upsert",
        )

        outbox = repository.list_graph_outbox()

        self.assertEqual(first_id, second_id)
        self.assertEqual(len(outbox), 1)
        self.assertEqual(outbox[0]["idempotency_key"], "event:100:upsert")


if __name__ == "__main__":
    unittest.main()
