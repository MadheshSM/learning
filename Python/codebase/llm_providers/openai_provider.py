"""OpenAI GPT LLM provider implementation"""
import openai
from typing import List, Dict, Any, Optional
import json
import logging

from .base import BaseLLMProvider, LLMResponse, ToolCall

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider implementation"""

    def __init__(self, api_key: str, model: Optional[str] = None):
        super().__init__(api_key, model)
        self.client = openai.AsyncOpenAI(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def default_model(self) -> str:
        return "gpt-4o"

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        """Send a chat completion request to OpenAI"""
        try:
            # Convert messages to OpenAI format
            converted_messages = self._convert_messages(messages)

            # Build request parameters
            request_params = {
                "model": self.model,
                "messages": converted_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Add tools if provided
            if tools:
                request_params["tools"] = self._convert_tools(tools)
                request_params["tool_choice"] = "auto"

            # Make the API call
            response = await self.client.chat.completions.create(**request_params)

            # Extract the response
            choice = response.choices[0]
            message = choice.message

            # Extract tool calls if present
            tool_calls = None
            if message.tool_calls:
                tool_calls = []
                for tc in message.tool_calls:
                    try:
                        tool_input = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        tool_input = {"raw": tc.function.arguments}

                    tool_calls.append(ToolCall(
                        tool_id=tc.id,
                        tool_name=tc.function.name,
                        tool_input=tool_input
                    ))

            return LLMResponse(
                content=message.content or "",
                tool_calls=tool_calls,
                usage={
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
                } if response.usage else None,
                model=response.model,
                finish_reason=choice.finish_reason,
                raw_response=response
            )

        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI provider: {e}")
            raise

    def _convert_tools(self, tools: List[Dict]) -> List[Dict]:
        """Convert tools to OpenAI's function calling format"""
        openai_tools = []
        for tool in tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.get("name"),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {"type": "object", "properties": {}})
                }
            }
            openai_tools.append(openai_tool)
        return openai_tools

    def _convert_messages(self, messages: List[Dict]) -> List[Dict]:
        """Convert messages to OpenAI's expected format"""
        converted = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")

            if role == "tool":
                # Tool response message
                converted.append({
                    "role": "tool",
                    "tool_call_id": msg.get("tool_call_id"),
                    "content": content
                })
            elif role == "assistant" and msg.get("tool_calls"):
                # Assistant message with tool calls
                tool_calls = []
                for tc in msg.get("tool_calls", []):
                    if isinstance(tc, dict):
                        tool_calls.append({
                            "id": tc.get("tool_id", tc.get("id")),
                            "type": "function",
                            "function": {
                                "name": tc.get("tool_name", tc.get("name")),
                                "arguments": json.dumps(tc.get("tool_input", tc.get("input", {})))
                            }
                        })
                    elif hasattr(tc, 'tool_id'):
                        tool_calls.append({
                            "id": tc.tool_id,
                            "type": "function",
                            "function": {
                                "name": tc.tool_name,
                                "arguments": json.dumps(tc.tool_input)
                            }
                        })

                converted.append({
                    "role": "assistant",
                    "content": content if content else None,
                    "tool_calls": tool_calls
                })
            else:
                # Standard message
                converted.append({
                    "role": role,
                    "content": content
                })

        return converted
