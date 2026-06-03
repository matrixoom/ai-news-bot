import json
import shutil
import unittest
from pathlib import Path

from src.services.event_extraction_service import EventExtractionService, EventExtractionValidationError
from src.services.event_insight_job_service import EventInsightJobService
from src.services.event_insight_repository import EventInsightRepository
from src.services.event_insight_migrations import utc_now_iso


class FakeTaskResult:
    """测试用 LLM 任务结果。"""

    def __init__(self, text: str) -> None:
        self.text = text
        self.provider = {"id": 1, "modelName": "fake-model"}


class FakeTaskRouter:
    """测试用任务路由，返回固定 JSON。"""

    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[str] = []

    def generate(self, task_type: str, messages: list[dict[str, str]]) -> FakeTaskResult:
        """记录 task_type 并返回固定内容。"""
        self.calls.append(task_type)
        return FakeTaskResult(self.text)


class EventExtractionServiceTests(unittest.TestCase):
    """校验事件抽取服务的证据链写入能力。"""

    def setUp(self) -> None:
        self.temp_dir = Path(".tmp-events-tests") / "event-extraction" / self.id().split(".")[-1]
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.repository = EventInsightRepository(self.temp_dir / "event_insight.db")
        self.job_service = EventInsightJobService(self.repository)
        self.content = Path("tests/fixtures/event_insight/storage_price_material.txt").read_text(encoding="utf-8")
        self.document_id = self.repository.create_raw_document(
            source_type="research_report",
            title="存储价格跟踪",
            content_text=self.content,
            content_hash=f"doc-{self.id()}",
            url="https://example.com/storage",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_extract_document_creates_event_evidence_and_entities(self) -> None:
        """校验成功抽取会写入事件、证据位置和关联实体。"""
        router = FakeTaskRouter(
            json.dumps(
                {
                    "events": [
                        {
                            "title": "DRAM 合约价上涨",
                            "summary": "AI 服务器需求支撑内存涨价。",
                            "eventTime": "2026-05-16T10:30:00+08:00",
                            "eventType": "price_change",
                            "confidenceScore": 0.86,
                            "evidence": [
                                {
                                    "excerpt": "DRAM 合约价上涨，AI 服务器需求支撑内存涨价。",
                                    "evidenceLevel": "B",
                                }
                            ],
                            "entities": [{"name": "DRAM", "entityType": "product", "role": "subject"}],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        )
        service = EventExtractionService(repository=self.repository, task_router=router)

        result = service.extract_document(self.document_id)

        self.assertEqual(router.calls, ["event_extraction"])
        self.assertEqual(len(result["eventIds"]), 1)
        event = self.repository.get_event(result["eventIds"][0])
        evidence = self.repository.list_event_evidence(result["eventIds"][0])[0]
        entities = self.repository.list_event_entities(result["eventIds"][0])
        self.assertEqual(event["title"], "DRAM 合约价上涨")
        self.assertEqual(evidence["start_offset"], 0)
        self.assertGreater(evidence["end_offset"], evidence["start_offset"])
        self.assertEqual(evidence["source_url"], "https://example.com/storage")
        self.assertEqual(entities[0]["name"], "DRAM")

    def test_extract_document_rejects_evidence_not_found(self) -> None:
        """校验证据片段必须能在原始材料中定位。"""
        service = EventExtractionService(
            repository=self.repository,
            task_router=FakeTaskRouter(
                json.dumps(
                    {
                        "events": [
                            {
                                "title": "不存在的证据",
                                "summary": "摘要",
                                "eventTime": "2026-05-16T10:30:00+08:00",
                                "eventType": "other",
                                "confidenceScore": 0.5,
                                "evidence": [{"excerpt": "这句话不在原文中", "evidenceLevel": "C"}],
                            }
                        ]
                    },
                    ensure_ascii=False,
                )
            ),
        )

        with self.assertRaises(EventExtractionValidationError):
            service.extract_document(self.document_id)

    def test_run_next_extract_job_marks_success(self) -> None:
        """校验 extract_event 本地任务可被领取并完成。"""
        job = self.repository.create_processing_job(
            job_type="extract_event",
            idempotency_key="extract-doc-1",
            payload_json=json.dumps({"rawDocumentId": self.document_id}),
            next_run_at=utc_now_iso(),
        )
        service = EventExtractionService(
            repository=self.repository,
            task_router=FakeTaskRouter(
                json.dumps(
                    {
                        "events": [
                            {
                                "title": "DRAM 合约价上涨",
                                "summary": "AI 服务器需求支撑内存涨价。",
                                "eventTime": "2026-05-16T10:30:00+08:00",
                                "eventType": "price_change",
                                "confidenceScore": 0.86,
                                "evidence": [{"excerpt": "DRAM 合约价上涨，AI 服务器需求支撑内存涨价。"}],
                            }
                        ]
                    },
                    ensure_ascii=False,
                )
            ),
            job_service=self.job_service,
        )

        result = service.run_next_job(lease_owner="unit-test", now=utc_now_iso())

        self.assertEqual(result["jobId"], job["id"])
        self.assertEqual(self.repository.get_processing_job(job["id"])["status"], "succeeded")


if __name__ == "__main__":
    unittest.main()
