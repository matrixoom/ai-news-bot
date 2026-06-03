"""LLM 配置业务服务。"""

from __future__ import annotations

from typing import Any, Callable

from ..security.local_secret_cipher import LocalSecretCipher
from .llm_config_repository import LlmConfigRepository


class LlmProviderNotFoundError(Exception):
    """表示 provider 不存在。"""


class LlmProviderInUseError(Exception):
    """表示 provider 已被任务映射引用，不能禁用。"""


class LlmConfigValidationError(Exception):
    """表示 LLM 配置请求不合法。"""


class LlmConfigService:
    """封装 LLM 配置脱敏、加密和任务映射规则。"""

    def __init__(
        self,
        repository: LlmConfigRepository,
        *,
        secret_key: str | None = None,
        connection_tester: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self._repository = repository
        self._cipher = LocalSecretCipher(secret_key)
        self._connection_tester = connection_tester

    def list_providers(self) -> dict[str, Any]:
        """返回脱敏后的 provider 列表。"""

        return {"providers": [self._present_provider(row) for row in self._repository.list_providers()]}

    def create_provider(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        """创建 provider 配置。"""

        values = self._parse_provider_payload(payload, require_api_key=True)
        row = self._repository.create_provider(values)
        return {"provider": self._present_provider(row)}

    def update_provider(self, provider_id: int, payload: dict[str, Any] | None) -> dict[str, Any]:
        """更新 provider 配置。"""

        existing = self._require_provider(provider_id)
        values = self._parse_provider_payload(payload, require_api_key=False)
        if not values.get("encrypted_api_key"):
            values["encrypted_api_key"] = existing.get("encrypted_api_key", "")
        row = self._repository.update_provider(provider_id, values)
        if row is None:
            raise LlmProviderNotFoundError()
        return {"provider": self._present_provider(row)}

    def disable_provider(self, provider_id: int) -> dict[str, Any]:
        """禁用 provider；被任务映射引用时拒绝。"""

        self._require_provider(provider_id)
        if self._repository.provider_has_task_mapping(provider_id):
            raise LlmProviderInUseError()
        row = self._repository.disable_provider(provider_id)
        if row is None:
            raise LlmProviderNotFoundError()
        return {"provider": self._present_provider(row)}

    def test_provider(self, provider_id: int) -> dict[str, Any]:
        """测试 provider 连接。"""

        provider = self._present_provider(self._require_provider(provider_id), include_secret=True)
        if self._connection_tester is not None:
            return self._connection_tester(provider)
        return {"ok": bool(provider.get("apiKey")), "detail": "provider configuration is present"}

    def list_task_configs(self) -> dict[str, Any]:
        """返回任务模型映射列表。"""

        return {"taskConfigs": [self._present_task_config(row) for row in self._repository.list_task_configs()]}

    def upsert_task_config(self, task_type: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        """保存任务模型映射。"""

        body = payload or {}
        try:
            provider_id = int(body.get("providerId"))
        except (TypeError, ValueError):
            raise LlmConfigValidationError("providerId is required") from None
        provider = self._require_provider(provider_id)
        if not int(provider.get("enabled") or 0):
            raise LlmConfigValidationError("provider is disabled")
        row = self._repository.upsert_task_config(
            task_type,
            {
                "provider_config_id": provider_id,
                "model_name": str(body.get("modelName") or provider.get("model_name") or ""),
                "temperature": float(body.get("temperature", 0.2)),
                "max_tokens": int(body.get("maxTokens", 2000)),
            },
        )
        return {"taskConfig": self._present_task_config(row)}

    def resolve_task_provider(self, task_type: str) -> dict[str, Any]:
        """解析任务对应的 provider 配置，供 LlmTaskRouter 使用。"""

        task = self._repository.get_task_config(task_type)
        if task is None:
            raise LlmProviderNotFoundError()
        provider = self._present_provider(self._require_provider(int(task["provider_config_id"])), include_secret=True)
        provider["modelName"] = task.get("model_name") or provider["modelName"]
        provider["temperature"] = float(task.get("temperature") or 0.2)
        provider["maxTokens"] = int(task.get("max_tokens") or 2000)
        return provider

    def _parse_provider_payload(self, payload: dict[str, Any] | None, *, require_api_key: bool) -> dict[str, Any]:
        """解析 provider 请求体。"""

        body = payload or {}
        name = str(body.get("name") or "").strip()
        provider_type = str(body.get("providerType") or "openai_compatible").strip()
        model_name = str(body.get("modelName") or "").strip()
        api_key = str(body.get("apiKey") or "")
        if not name or not model_name:
            raise LlmConfigValidationError("name and modelName are required")
        if require_api_key and not api_key:
            raise LlmConfigValidationError("apiKey is required")
        return {
            "name": name,
            "provider_type": provider_type,
            "base_url": str(body.get("baseUrl") or "").strip(),
            "model_name": model_name,
            "encrypted_api_key": self._cipher.encrypt(api_key) if api_key else "",
            "timeout_seconds": int(body.get("timeoutSeconds") or 60),
            "supports_structured_output": bool(body.get("supportsStructuredOutput", True)),
            "supports_embeddings": bool(body.get("supportsEmbeddings", False)),
        }

    def _require_provider(self, provider_id: int) -> dict[str, Any]:
        """读取 provider，不存在时抛出异常。"""

        provider = self._repository.get_provider(provider_id)
        if provider is None:
            raise LlmProviderNotFoundError()
        return provider

    def _present_provider(self, row: dict[str, Any], *, include_secret: bool = False) -> dict[str, Any]:
        """将数据库 provider 行转换为前端契约。"""

        encrypted = str(row.get("encrypted_api_key") or "")
        api_key = self._cipher.decrypt(encrypted) if encrypted else ""
        payload: dict[str, Any] = {
            "id": int(row["id"]),
            "name": str(row["name"]),
            "providerType": str(row["provider_type"]),
            "baseUrl": str(row.get("base_url") or ""),
            "modelName": str(row["model_name"]),
            "timeoutSeconds": int(row.get("timeout_seconds") or 60),
            "supportsStructuredOutput": bool(row.get("supports_structured_output")),
            "supportsEmbeddings": bool(row.get("supports_embeddings")),
            "enabled": bool(row.get("enabled")),
            "apiKeyConfigured": bool(api_key),
            "apiKeyPreview": _preview_key(api_key),
            "updatedAt": str(row.get("updated_at") or ""),
        }
        if include_secret:
            payload["apiKey"] = api_key
        return payload

    def _present_task_config(self, row: dict[str, Any]) -> dict[str, Any]:
        """将数据库任务映射行转换为前端契约。"""

        return {
            "taskType": str(row["task_type"]),
            "providerId": int(row["provider_config_id"]),
            "providerName": str(row.get("provider_name") or ""),
            "providerType": str(row.get("provider_type") or ""),
            "modelName": str(row.get("model_name") or ""),
            "temperature": float(row.get("temperature") or 0.2),
            "maxTokens": int(row.get("max_tokens") or 2000),
            "enabled": bool(row.get("enabled")),
            "updatedAt": str(row.get("updated_at") or ""),
        }


def _preview_key(api_key: str) -> str:
    """生成不泄露明文的密钥预览。"""

    if not api_key:
        return ""
    if len(api_key) <= 7:
        return "***"
    return f"{api_key[:3]}...{api_key[-4:]}"
