"""按需加载不同 LLM SDK 的 Provider 工厂。"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from .base_provider import BaseLLMProvider


_PROVIDER_IMPORTS = {
    "claude": (".claude_provider", "ClaudeProvider"),
    "deepseek": (".deepseek_provider", "DeepSeekProvider"),
    "gemini": (".gemini_provider", "GeminiProvider"),
    "grok": (".grok_provider", "GrokProvider"),
    "openai": (".openai_provider", "OpenAIProvider"),
    "openai_compatible": (".openai_compatible_provider", "OpenAICompatibleProvider"),
}

_PUBLIC_IMPORTS = {
    class_name: module_name
    for module_name, class_name in _PROVIDER_IMPORTS.values()
}
_PUBLIC_IMPORTS["create_openai_compatible_provider"] = ".openai_compatible_provider"


def _load_public_attribute(attribute_name: str) -> Any:
    """按公开属性名加载对应 Provider 模块。

    Args:
        attribute_name: 包级公开类或工厂函数名称。

    Returns:
        从目标模块读取到的类或函数。

    Raises:
        AttributeError: 属性不属于本包公开 API。
    """

    module_name = _PUBLIC_IMPORTS.get(attribute_name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {attribute_name!r}")
    attribute = getattr(import_module(module_name, __name__), attribute_name)
    globals()[attribute_name] = attribute
    return attribute


def __getattr__(attribute_name: str) -> Any:
    """兼容包级 Provider 导入，同时避免 Web 启动加载全部第三方 SDK。"""

    return _load_public_attribute(attribute_name)


def get_llm_provider(provider_name: str, **kwargs: Any) -> BaseLLMProvider:
    """创建指定类型的 LLM Provider。

    Args:
        provider_name: Provider 类型名称。
        **kwargs: 传递给 Provider 构造函数的参数。

    Returns:
        指定 Provider 的实例。

    Raises:
        ValueError: Provider 类型不受支持。
    """

    normalized_name = provider_name.lower()
    provider_import = _PROVIDER_IMPORTS.get(normalized_name)
    if provider_import is None:
        raise ValueError(
            f"Unknown LLM provider: {provider_name}. "
            f"Available providers: {', '.join(_PROVIDER_IMPORTS)}"
        )

    _, class_name = provider_import
    provider_class = _load_public_attribute(class_name)
    return provider_class(**kwargs)


__all__ = [
    'BaseLLMProvider',
    'ClaudeProvider',
    'DeepSeekProvider',
    'GeminiProvider',
    'GrokProvider',
    'OpenAIProvider',
    'OpenAICompatibleProvider',
    'create_openai_compatible_provider',
    'get_llm_provider',
]
