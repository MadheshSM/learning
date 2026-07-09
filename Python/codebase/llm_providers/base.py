"""Base LLM provider abstract class and common types"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


@dataclass
class ToolCall:
    """Represents a tool/function call from the LLM"""
    tool_id: str
    tool_name: str
    tool_input: Dict[str, Any]


@dataclass
class Message:
    """Represents a chat message"""
    role: str  # 'system', 'user', 'assistant', 'tool'
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None  # For tool response messages
    name: Optional[str] = None  # Tool name for tool responses


@dataclass
class LLMResponse:
    """Standardized response from LLM providers"""
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[Any] = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or self.default_model

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g., 'anthropic', 'openai', 'google')"""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model to use if none specified"""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        """Send a chat completion request"""
        pass

    @abstractmethod
    def _convert_tools(self, tools: List[Dict]) -> List[Any]:
        """Convert tools to provider-specific format"""
        pass

    @abstractmethod
    def _convert_messages(self, messages: List[Dict]) -> List[Any]:
        """Convert messages to provider-specific format"""
        pass

    def _extract_tool_calls(self, response: Any) -> Optional[List[ToolCall]]:
        """Extract tool calls from provider-specific response"""
        return None

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Simple text generation (wraps chat)"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return await self.chat(messages, **kwargs)

    async def health_check(self) -> bool:
        """Check if the provider is available"""
        try:
            response = await self.generate("Hello", max_tokens=10)
            return response.content is not None
        except Exception:
            return False
