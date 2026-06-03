"""
Base LLM Provider - Abstract base class for all LLM providers
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: int = 60,
    ):
        """
        Initialize the LLM provider.
        
        Args:
            api_key: API key for the provider
            model: Model name to use
            base_url: OpenAI-compatible base URL
            timeout_seconds: Request timeout in seconds
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
    
    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 1.0,
        **kwargs
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated text response
            
        Raises:
            Exception: If generation fails
        """
        pass
    
    @abstractmethod
    def generate_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        max_tokens: int = 2000,
        max_iterations: int = 8,
        **kwargs
    ) -> str:
        """
        Generate a response with tool calling support.
        
        Args:
            messages: List of message dicts
            tools: List of tool definitions
            max_tokens: Maximum tokens in response
            max_iterations: Maximum tool use iterations
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated text response after tool interactions
            
        Raises:
            Exception: If generation fails
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the provider"""
        pass
    
    @property
    @abstractmethod
    def default_model(self) -> str:
        """Return the default model name for this provider"""
        pass

    def generate_structured(
        self,
        messages: List[Dict[str, str]],
        schema: Dict[str, Any],
        max_tokens: int = 2000,
        temperature: float = 0.2,
        **kwargs,
    ) -> Dict[str, Any]:
        """生成结构化 JSON 响应。

        Args:
            messages: 模型消息。
            schema: JSON Schema。
            max_tokens: 最大输出 token。
            temperature: 采样温度。
            **kwargs: provider 扩展参数。

        Returns:
            解析后的 JSON 字典。
        """

        import json

        text = self.generate(messages, max_tokens=max_tokens, temperature=temperature, response_schema=schema, **kwargs)
        return json.loads(text)

    def embed_texts(self, texts: List[str], **kwargs) -> List[List[float]]:
        """生成文本向量；默认 provider 不支持 embedding。"""

        raise NotImplementedError("embedding is not supported by this provider")
