"""
LLM Providers Module - Abstracts different LLM API providers
"""
from .base_provider import BaseLLMProvider
from .claude_provider import ClaudeProvider
from .deepseek_provider import DeepSeekProvider


def get_llm_provider(provider_name: str, **kwargs) -> BaseLLMProvider:
    """
    Factory function to get the appropriate LLM provider.
    
    Args:
        provider_name: Name of the provider ('claude' or 'deepseek')
        **kwargs: Additional arguments passed to the provider constructor
        
    Returns:
        An instance of the requested LLM provider
        
    Raises:
        ValueError: If provider_name is not recognized
    """
    providers = {
        'claude': ClaudeProvider,
        'deepseek': DeepSeekProvider,
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
    'get_llm_provider',
]
