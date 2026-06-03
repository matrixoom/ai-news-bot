import shutil
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.app.web import create_fastapi_app
from src.services.event_insight_repository import EventInsightRepository
from src.services.events_outlook_service import EventsOutlookService
from src.services.events_outlook_store import EventsOutlookStore
from src.services.llm_config_repository import LlmConfigRepository
from src.services.llm_config_service import LlmConfigService


class EmptyResearchProvider:
    """提供测试用研究 provider，避免静态日历触发外部依赖。"""

    def collect_outlook(self, **_: object) -> list[object]:
        """返回空采集结果。"""
        return []

    def healthcheck(self) -> object:
        """返回轻量健康对象。"""
        return object()


class LlmSettingsApiTests(unittest.TestCase):
    """校验 LLM Settings API 契约。"""

    def setUp(self) -> None:
        self.temp_dir = Path(".tmp-events-tests") / "llm-settings-api" / self.id().split(".")[-1]
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        event_repository = EventInsightRepository(self.temp_dir / "event_insight.db")
        repository = LlmConfigRepository(event_repository.db_path)
        service = LlmConfigService(
            repository,
            secret_key="api-test-secret",
            connection_tester=lambda provider: {"ok": True, "detail": f"{provider['name']} connected"},
        )
        self.client = TestClient(
            create_fastapi_app(
                llm_config_service=service,
                event_outlook_service=EventsOutlookService(
                    research_provider=EmptyResearchProvider(),
                    store=EventsOutlookStore(self.temp_dir / "events_outlook.db"),
                ),
            )
        )

    def tearDown(self) -> None:
        self.client.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_provider_crud_redacts_secret_and_tests_connection(self) -> None:
        """校验新增、列表、连接测试都不会返回明文密钥。"""
        response = self.client.post(
            "/api/system/llm/providers",
            json={
                "name": "主分析模型",
                "providerType": "openai_compatible",
                "baseUrl": "https://api.example.com/v1",
                "modelName": "analysis-model",
                "apiKey": "sk-api-secret",
            },
        )

        self.assertEqual(response.status_code, 201)
        provider = response.json()["provider"]
        self.assertTrue(provider["apiKeyConfigured"])
        self.assertNotIn("apiKey", provider)

        list_response = self.client.get("/api/system/llm/providers")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["providers"][0]["apiKeyPreview"], "sk-...cret")

        test_response = self.client.post(f"/api/system/llm/providers/{provider['id']}/test")
        self.assertEqual(test_response.status_code, 200)
        self.assertTrue(test_response.json()["ok"])

        log_response = self.client.get("/api/system/llm/call-logs?taskType=connection_test")
        self.assertEqual(log_response.status_code, 200)
        logs = log_response.json()["items"]
        self.assertEqual(logs[0]["taskType"], "connection_test")
        self.assertEqual(logs[0]["providerId"], provider["id"])
        self.assertEqual(logs[0]["status"], "succeeded")
        self.assertIn("主分析模型 connected", logs[0]["responsePreview"])
        self.assertNotIn("sk-api-secret", str(logs[0]))

        update_response = self.client.put(
            f"/api/system/llm/providers/{provider['id']}",
            json={
                "name": "主分析模型-更新",
                "providerType": "openai_compatible",
                "baseUrl": "https://api.updated.example.com/v1",
                "modelName": "updated-model",
                "timeoutSeconds": 45,
            },
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["provider"]["name"], "主分析模型-更新")
        self.assertEqual(update_response.json()["provider"]["apiKeyPreview"], "sk-...cret")

        disable_response = self.client.post(f"/api/system/llm/providers/{provider['id']}/disable")
        self.assertEqual(disable_response.status_code, 200)
        self.assertFalse(disable_response.json()["provider"]["enabled"])

    def test_task_mapping_and_disable_conflict(self) -> None:
        """校验任务映射可保存，引用中的 provider 禁用返回 409。"""
        provider = self.client.post(
            "/api/system/llm/providers",
            json={
                "name": "主题摘要模型",
                "providerType": "openai_compatible",
                "baseUrl": "https://api.example.com/v1",
                "modelName": "summary-model",
                "apiKey": "sk-summary-secret",
            },
        ).json()["provider"]

        mapping_response = self.client.put(
            "/api/system/llm/task-configs/topic_summary",
            json={"providerId": provider["id"], "modelName": "summary-model", "temperature": 0.2, "maxTokens": 800},
        )
        self.assertEqual(mapping_response.status_code, 200)
        self.assertEqual(mapping_response.json()["taskConfig"]["taskType"], "topic_summary")

        disable_response = self.client.post(f"/api/system/llm/providers/{provider['id']}/disable")
        self.assertEqual(disable_response.status_code, 409)
        self.assertEqual(disable_response.json()["error"], "provider_in_use")

    def test_event_outlook_static_calendar_still_works(self) -> None:
        """校验 LLM Settings API 不影响 Event Outlook 静态日历。"""
        response = self.client.get("/api/frontend/modules/event-outlook?region=domestic&refresh=1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["module"]["id"], "event-outlook")


if __name__ == "__main__":
    unittest.main()
