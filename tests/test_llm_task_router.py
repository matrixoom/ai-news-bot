import shutil
import unittest
from pathlib import Path

from src.services.event_insight_repository import EventInsightRepository
from src.services.llm_config_repository import LlmConfigRepository
from src.services.llm_config_service import LlmConfigService, LlmProviderInUseError
from src.services.llm_task_router import LlmTaskRouter


class FakeProvider:
    """测试用模型 provider，避免真实网络调用。"""

    def __init__(self, text: str = "ok") -> None:
        self.text = text
        self.calls: list[dict[str, object]] = []

    def generate(self, messages, max_tokens=2000, temperature=1.0, **kwargs):  # noqa: ANN001
        """记录调用并返回固定文本。"""
        self.calls.append({"messages": messages, "max_tokens": max_tokens, "temperature": temperature, **kwargs})
        return self.text


class LlmTaskRouterTests(unittest.TestCase):
    """校验 LLM 配置加密、脱敏和任务路由。"""

    def setUp(self) -> None:
        self.temp_dir = Path(".tmp-events-tests") / "llm-task-router" / self.id().split(".")[-1]
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.event_repository = EventInsightRepository(self.temp_dir / "event_insight.db")
        self.repository = LlmConfigRepository(self.event_repository.db_path)
        self.service = LlmConfigService(self.repository, secret_key="unit-test-secret")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_provider_api_key_is_encrypted_and_redacted(self) -> None:
        """校验 API Key 入库后不出现明文，列表响应只返回配置状态。"""
        provider = self.service.create_provider(
            {
                "name": "主分析模型",
                "providerType": "openai_compatible",
                "baseUrl": "https://api.example.com/v1",
                "modelName": "analysis-model",
                "apiKey": "sk-secret-value",
                "timeoutSeconds": 90,
            }
        )["provider"]

        raw_bytes = self.event_repository.db_path.read_bytes()
        listed = self.service.list_providers()["providers"][0]

        self.assertNotIn(b"sk-secret-value", raw_bytes)
        self.assertTrue(provider["apiKeyConfigured"])
        self.assertNotIn("apiKey", listed)
        self.assertEqual(listed["apiKeyPreview"], "sk-...alue")

    def test_provider_connection_test_calls_configured_model(self) -> None:
        """校验连接测试会真实调用配置的 provider，而不是只检查配置存在。"""
        fake = FakeProvider(text="OK")
        service = LlmConfigService(
            self.repository,
            secret_key="unit-test-secret",
            provider_factory=lambda _: fake,
        )
        provider = service.create_provider(
            {
                "name": "连接测试模型",
                "providerType": "openai_compatible",
                "baseUrl": "https://api.example.com/v1",
                "modelName": "connectivity-model",
                "apiKey": "sk-connect-secret",
            }
        )["provider"]

        with self.assertLogs("src.services.llm_config_service", level="INFO") as captured_logs:
            result = service.test_provider(provider["id"])

        self.assertTrue(result["ok"])
        self.assertIn("连接测试成功", result["detail"])
        self.assertEqual(fake.calls[0]["max_tokens"], 8)
        self.assertEqual(fake.calls[0]["temperature"], 0)
        request_record = captured_logs.records[0]
        response_record = captured_logs.records[1]
        self.assertEqual(request_record.messages[1]["content"], "Reply with OK.")
        self.assertEqual(response_record.response_text, "OK")

    def test_task_router_uses_configured_provider(self) -> None:
        """校验任务路由按 task_type 选择配置的 provider 和模型参数。"""
        provider = self.service.create_provider(
            {
                "name": "抽取模型",
                "providerType": "openai_compatible",
                "baseUrl": "https://api.example.com/v1",
                "modelName": "extract-model",
                "apiKey": "sk-router-secret",
            }
        )["provider"]
        self.service.upsert_task_config(
            "event_extraction",
            {"providerId": provider["id"], "modelName": "extract-model", "temperature": 0.1, "maxTokens": 600},
        )
        fake = FakeProvider(text="structured output")
        router = LlmTaskRouter(self.service, provider_factory=lambda _: fake)

        result = router.generate("event_extraction", [{"role": "user", "content": "抽取事件"}])

        self.assertEqual(result.text, "structured output")
        self.assertEqual(result.provider["id"], provider["id"])
        self.assertEqual(fake.calls[0]["temperature"], 0.1)

    def test_disable_provider_in_use_is_rejected(self) -> None:
        """校验被任务映射引用的 provider 不能直接禁用。"""
        provider = self.service.create_provider(
            {
                "name": "主分析模型",
                "providerType": "openai_compatible",
                "baseUrl": "https://api.example.com/v1",
                "modelName": "analysis-model",
                "apiKey": "sk-in-use-secret",
            }
        )["provider"]
        self.service.upsert_task_config("topic_summary", {"providerId": provider["id"]})

        with self.assertRaises(LlmProviderInUseError):
            self.service.disable_provider(provider["id"])


if __name__ == "__main__":
    unittest.main()
