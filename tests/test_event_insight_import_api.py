import json
import shutil
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.app.web import create_fastapi_app
from src.services.event_insight_import_service import EventInsightImportService
from src.services.event_insight_job_service import EventInsightJobService
from src.services.event_insight_repository import EventInsightRepository
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


class EventInsightImportApiTests(unittest.TestCase):
    """校验 Event Insight 材料导入 API 和任务状态 API。"""

    def setUp(self) -> None:
        self.temp_dir = Path(".tmp-events-tests") / "event-insight-import-api" / self.id().split(".")[-1]
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.repository = EventInsightRepository(self.temp_dir / "event_insight.db")
        self.job_service = EventInsightJobService(self.repository)
        self.import_service = EventInsightImportService(
            repository=self.repository,
            job_service=self.job_service,
            storage_root=self.temp_dir / "storage",
        )
        event_outlook_service = EventsOutlookService(
            research_provider=EmptyResearchProvider(),
            store=EventsOutlookStore(self.temp_dir / "events_outlook.db"),
        )
        self.client = TestClient(
            create_fastapi_app(
                event_insight_import_service=self.import_service,
                event_insight_job_service=self.job_service,
                event_outlook_service=event_outlook_service,
            )
        )

    def tearDown(self) -> None:
        self.client.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_text_import_returns_accepted_job_and_stores_document(self) -> None:
        """校验粘贴文本导入返回 202、写入材料并创建解析任务。"""
        response = self.client.post(
            "/api/frontend/modules/event-insight/documents/import",
            headers={"Idempotency-Key": "text-import-1"},
            json={
                "mode": "text",
                "title": "存储芯片报价上调",
                "content": "DRAM 合约价上涨，AI 服务器需求支撑内存涨价。",
            },
        )

        self.assertEqual(response.status_code, 202)
        payload = response.json()
        self.assertEqual(payload["status"], "pending")
        self.assertEqual(payload["jobType"], "parse_document")
        self.assertGreater(payload["rawDocumentId"], 0)
        self.assertEqual(self.repository.search_raw_documents("DRAM"), [payload["rawDocumentId"]])

        repeated = self.client.post(
            "/api/frontend/modules/event-insight/documents/import",
            headers={"Idempotency-Key": "text-import-1"},
            json={
                "mode": "text",
                "title": "存储芯片报价上调",
                "content": "DRAM 合约价上涨，AI 服务器需求支撑内存涨价。",
            },
        )

        self.assertEqual(repeated.status_code, 202)
        self.assertEqual(repeated.json()["jobId"], payload["jobId"])

    def test_url_import_stores_metadata_without_fetching_remote_body(self) -> None:
        """校验 URL 导入只保存元信息，不在请求线程抓取远端正文。"""
        response = self.client.post(
            "/api/frontend/modules/event-insight/documents/import",
            json={
                "mode": "url",
                "title": "HBM4 量产节奏提前",
                "url": "https://example.com/research/hbm4",
            },
        )

        self.assertEqual(response.status_code, 202)
        payload = response.json()
        document = self.repository.get_raw_document(payload["rawDocumentId"])

        self.assertIsNotNone(document)
        self.assertEqual(document["url"], "https://example.com/research/hbm4")
        self.assertEqual(document["content_text"], "")

    def test_file_import_copies_to_controlled_relative_directory(self) -> None:
        """校验 JSON 文件导入会复制到受控目录并只保存相对路径。"""
        response = self.client.post(
            "/api/frontend/modules/event-insight/documents/import",
            json={
                "mode": "file",
                "title": "研报摘要",
                "fileName": "memory-report.txt",
                "contentType": "text/plain",
                "content": "存储芯片价格继续上涨。",
            },
        )

        self.assertEqual(response.status_code, 202)
        payload = response.json()
        document = self.repository.get_raw_document(payload["rawDocumentId"])

        self.assertIsNotNone(document)
        self.assertTrue(document["local_file_path"].startswith("raw/txt/"))
        self.assertNotIn("..", document["local_file_path"])
        self.assertTrue((self.temp_dir / "storage" / document["local_file_path"]).exists())

    def test_file_import_rejects_path_traversal(self) -> None:
        """校验文件名路径穿越会快速失败。"""
        response = self.client.post(
            "/api/frontend/modules/event-insight/documents/import",
            json={
                "mode": "file",
                "title": "恶意文件",
                "fileName": "../escape.txt",
                "contentType": "text/plain",
                "content": "bad",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_event_insight_import_payload")

    def test_get_job_returns_status_payload(self) -> None:
        """校验任务状态接口返回可轮询 payload。"""
        create_response = self.client.post(
            "/api/frontend/modules/event-insight/documents/import",
            json={
                "mode": "text",
                "title": "光模块订单增加",
                "content": "CPO 光模块订单增加。",
            },
        )
        job_id = create_response.json()["jobId"]

        response = self.client.get(f"/api/frontend/modules/event-insight/jobs/{job_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], job_id)
        self.assertEqual(payload["jobType"], "parse_document")
        self.assertEqual(payload["status"], "pending")

    def test_event_outlook_static_calendar_still_uses_existing_route(self) -> None:
        """校验新增事件洞察 API 不影响原未来事件静态日历。"""
        response = self.client.get("/api/frontend/modules/event-outlook?region=domestic&refresh=1")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["module"]["id"], "event-outlook")
        self.assertEqual(payload["region"], "domestic")


if __name__ == "__main__":
    unittest.main()
