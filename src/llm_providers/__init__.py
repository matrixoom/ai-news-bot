"""
LLM Providers Module - Abstracts different LLM API providers
"""
from .base_provider import BaseLLMProvider
from .claude_provider import ClaudeProvider
from .deepseek_provider import DeepSeekProvider
from .gemini_provider import GeminiProvider
from .grok_provider import GrokProvider
from .openai_provider import OpenAIProvider


def get_llm_provider(provider_name: str, **kwargs) -> BaseLLMProvider:
    """
    Factory function to get the appropriate LLM provider.
    
    Args:
        provider_name: Name of the provider ('claude', 'deepseek', 'gemini', 'grok', or 'openai')
        **kwargs: Additional arguments passed to the provider constructor
        
    Returns:
        An instance of the requested LLM provider
        
    Raises:
        ValueError: If provider_name is not recognized
    """
    providers = {
        'claude': ClaudeProvider,
        'deepseek': DeepSeekProvider,
        'gemini': GeminiProvider,
        'grok': GrokProvider,
        'openai': OpenAIProvider,
    }
    
    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(
            f"Unknown LLM provider: {provider_name}. "
            f"Available providers: {', '.join(providers.keys())}"
        )
    
    return provider_class(**kwargs)


__all__ = [
    'BaseLLMProvider',
    'ClaudeProvider',
    'DeepSeekProvider',
    'GeminiProvider',
    'GrokProvider',
    'OpenAIProvider',
    'get_llm_provider',
]
