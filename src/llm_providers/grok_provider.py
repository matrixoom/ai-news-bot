"""
Grok Provider - xAI Grok API implementation using OpenAI-compatible interface
"""
import os
from typing import List, Dict, Any, Optional
from openai import OpenAI
from .base_provider import BaseLLMProvider
from ..logger import setup_logger


logger = setup_logger(__name__)


class GrokProvider(BaseLLMProvider):
    """xAI Grok LLM provider using OpenAI-compatible API"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Grok provider.
        
        Args:
            api_key: xAI API key. If None, reads from XAI_API_KEY env var
            model: Model name to use. If None, uses default model
            
        Raises:
            ValueError: If API key is not provided and not in environment
        """
        api_key = api_key or os.getenv("XAI_API_KEY")
        if not api_key:
            raise ValueError(
                "xAI API key must be provided or set in XAI_API_KEY environment variable"
            )
        
        super().__init__(api_key=api_key, model=model or self.default_model)
        
        # Initialize OpenAI client with xAI base URL
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1"
        )
        logger.info(f"Grok provider initialized with model: {self.model}")
    
    @property
    def provider_name(self) -> str:
        return "grok"
    
    @property
    def default_model(self) -> str:
        return "grok-beta"
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 1.0,
        **kwargs
    ) -> str:
        """
        Generate a response using Grok API.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            **kwargs: Additional Grok-specific parameters
            
        Returns:
            Generated text response
            
        Raises:
            Exception: If API call fails
        """
        try:
            logger.debug(f"Calling Grok API with {len(messages)} messages")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            # Extract text from response
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            
            raise Exception("No response received from Grok")
            
        except Exception as e:
            logger.error(f"Grok API error: {str(e)}", exc_info=True)
            raise
    
    def generate_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        max_tokens: int = 2000,
        max_iterations: int = 8,
        tool_handler: Optional[callable] = None,
        **kwargs
    ) -> str:
        """
        Generate a response with tool calling support using OpenAI format.
        
        Args:
            messages: List of message dicts
            tools: List of tool definitions in OpenAI format
            max_tokens: Maximum tokens in response
            max_iterations: Maximum tool use iterations
            tool_handler: Function to handle tool calls
            **kwargs: Additional Grok-specific parameters
            
        Returns:
            Generated text response after tool interactions
            
        Raises:
            Exception: If generation fails
        """
        try:
            logger.debug(f"Calling Grok API with tools, max_iterations={max_iterations}")
            
            response_text = None
            
            for iteration in range(max_iterations):
                # Call Grok API
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                message = response.choices[0].message
                finish_reason = response.choices[0].finish_reason
                
                logger.debug(f"Iteration {iteration + 1}: finish_reason = {finish_reason}")
                
                # Check if we got a final response
                if finish_reason == "stop" or not message.tool_calls:
                    response_text = message.content
                    break
                
                # Check if model wants to use tools
                elif finish_reason == "tool_calls" or message.tool_calls:
                    # Add assistant's message to history
                    messages.append({
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in message.tool_calls
                        ]
                    })
                    
                    # Process tool calls
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        # Parse arguments (they come as JSON string)
                        import json
                        tool_input = json.loads(tool_call.function.arguments)
                        
                        logger.info(f"Tool call: {tool_name} with input: {tool_input}")
                        
                        # Execute the tool using the handler
                        if tool_handler:
                            result_text = tool_handler(tool_name, tool_input, tool_call.id)
                            
                            # Add tool result to messages
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_name,
                                "content": result_text
                            })
                else:
                    # Unexpected finish reason
                    break
            
            if response_text is None:
                raise Exception("No text response received from Grok")
            
            logger.info("Grok generation with tools completed successfully")
            return response_text
            
        except Exception as e:
            logger.error(f"Grok API error with tools: {str(e)}", exc_info=True)
            raise
