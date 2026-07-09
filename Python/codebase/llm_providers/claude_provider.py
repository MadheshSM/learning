"""Anthropic Claude LLM provider implementation"""
import anthropic
from typing import List, Dict, Any, Optional
import json
import logging

from .base import BaseLLMProvider, LLMResponse, ToolCall

logger = logging.getLogger(__name__)


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude provider implementation"""

    def __init__(self, api_key: str, model: Optional[str] = None):
        super().__init__(api_key, model)
        self.client = anthropic.Anthropic(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def default_model(self) -> str:
        return "claude-sonnet-4-20250514"

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        """Send a chat completion request to Claude"""
        try:
            # Extract system message if present
            system_message = None
            chat_messages = []

            for msg in messages:
                if msg.get("role") == "system":
                    system_message = msg.get("content", "")
                else:
                    chat_messages.append(msg)

            # Convert messages to Claude format
            converted_messages = self._convert_messages(chat_messages)

            # Build request parameters
            request_params = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": converted_messages,
            }

            if system_message:
                request_params["system"] = system_message

            # Add tools if provided
            if tools:
                request_params["tools"] = self._convert_tools(tools)

            # Make the API call
            response = self.client.messages.create(**request_params)

            # Extract content and tool calls
            content = ""
            tool_calls = []

            for block in response.content:
                if block.type == "text":
                    content += block.text
                elif block.type == "tool_use":
                    tool_calls.append(ToolCall(
                        tool_id=block.id,
                        tool_name=block.name,
                        tool_input=block.input
                    ))

            return LLMResponse(
                content=content,
                tool_calls=tool_calls if tool_calls else None,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                },
                model=response.model,
                finish_reason=response.stop_reason,
                raw_response=response
            )

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Claude provider: {e}")
            raise

    def _convert_tools(self, tools: List[Dict]) -> List[Dict]:
        """Convert tools to Claude's expected format"""
        claude_tools = []
        for tool in tools:
            claude_tool = {
                "name": tool.get("name"),
                "description": tool.get("description", ""),
                "input_schema": tool.get("parameters", {"type": "object", "properties": {}})
            }
            claude_tools.append(claude_tool)
        return claude_tools

    def _convert_messages(self, messages: List[Dict]) -> List[Dict]:
        """Convert messages to Claude's expected format"""
        converted = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")

            if role == "tool":
                # Convert tool response to Claude format
                converted.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.get("tool_call_id"),
                        "content": content
                    }]
                })
            elif role == "assistant" and msg.get("tool_calls"):
                # Convert assistant message with tool calls
                content_blocks = []
                if content:
                    content_blocks.append({"type": "text", "text": content})

                for tc in msg.get("tool_calls", []):
                    if isinstance(tc, dict):
                        content_blocks.append({
                            "type": "tool_use",
                            "id": tc.get("tool_id", tc.get("id")),
                            "name": tc.get("tool_name", tc.get("name")),
                            "input": tc.get("tool_input", tc.get("input", {}))
                        })
                    elif hasattr(tc, 'tool_id'):
                        content_blocks.append({
                            "type": "tool_use",
                            "id": tc.tool_id,
                            "name": tc.tool_name,
                            "input": tc.tool_input
                        })

                converted.append({
                    "role": "assistant",
                    "content": content_blocks
                })
            else:
                # Standard message
                converted.append({
                    "role": role,
                    "content": content
                })

        return converted
