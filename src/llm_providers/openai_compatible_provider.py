"""OpenAI-compatible LLM provider."""

from __future__ import annotations

import json
from typing import Any, Optional

from openai import OpenAI

from .base_provider import BaseLLMProvider


class OpenAICompatibleProvider(BaseLLMProvider):
    """通过 OpenAI-compatible Chat Completions API 调用模型。"""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: int = 60,
        provider_name: str = "openai_compatible",
    ) -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url, timeout_seconds=timeout_seconds)
        self._provider_name = provider_name
        self.client = OpenAI(api_key=api_key, base_url=base_url or None, timeout=timeout_seconds)

    @property
    def provider_name(self) -> str:
        """返回 provider 名称。"""

        return self._provider_name

    @property
    def default_model(self) -> str:
        """返回默认模型名称。"""

        return self.model or "gpt-5.1"

    def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 1.0,
        **kwargs: Any,
    ) -> str:
        """生成文本响应。"""

        response_schema = kwargs.pop("response_schema", None)
        if response_schema:
            kwargs.setdefault("response_format", {"type": "json_object"})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    def generate_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int = 2000,
        max_iterations: int = 8,
        **kwargs: Any,
    ) -> str:
        """生成带工具调用的响应；P5 仅保留单轮工具调用兼容。"""

        _ = max_iterations
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    def embed_texts(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        """调用 OpenAI-compatible embeddings API。"""

        model = str(kwargs.get("embedding_model") or kwargs.get("model") or self.model)
        response = self.client.embeddings.create(model=model, input=texts)
        return [list(item.embedding) for item in response.data]


def create_openai_compatible_provider(config: dict[str, Any]) -> OpenAICompatibleProvider:
    """由配置字典构建 OpenAI-compatible provider。"""

    return OpenAICompatibleProvider(
        api_key=str(config.get("apiKey") or ""),
        model=str(config.get("modelName") or ""),
        base_url=str(config.get("baseUrl") or ""),
        timeout_seconds=int(config.get("timeoutSeconds") or 60),
        provider_name=str(config.get("providerType") or "openai_compatible"),
    )
