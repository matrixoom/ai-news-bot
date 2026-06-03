"""LLM 任务路由服务。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .llm_config_service import LlmConfigService


@dataclass(frozen=True)
class LlmTaskResult:
    """LLM 任务调用结果。"""

    text: str
    provider: dict[str, Any]


class LlmTaskRouter:
    """按 task_type 路由到配置的模型 provider。"""

    def __init__(self, config_service: LlmConfigService, provider_factory: Callable[[dict[str, Any]], Any]) -> None:
        self._config_service = config_service
        self._provider_factory = provider_factory

    def generate(self, task_type: str, messages: list[dict[str, str]], **kwargs: Any) -> LlmTaskResult:
        """按任务类型调用模型。"""

        provider_config = self._config_service.resolve_task_provider(task_type)
        provider = self._provider_factory(provider_config)
        text = provider.generate(
            messages,
            max_tokens=int(kwargs.get("max_tokens") or provider_config.get("maxTokens") or 2000),
            temperature=float(kwargs.get("temperature", provider_config.get("temperature", 0.2))),
        )
        return LlmTaskResult(text=text, provider={key: value for key, value in provider_config.items() if key != "apiKey"})
