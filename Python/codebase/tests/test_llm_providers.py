"""Tests for LLM provider layer"""
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from llm_providers.base import BaseLLMProvider, LLMResponse, ToolCall, Message
from llm_providers.factory import LLMProviderFactory, LLMProviderType
from llm_providers.claude_provider import ClaudeProvider
from llm_providers.openai_provider import OpenAIProvider
from llm_providers.gemini_provider import GeminiProvider


class TestLLMResponse:
    """Tests for LLMResponse dataclass"""

    def test_create_basic_response(self):
        """Test creating a basic response"""
        response = LLMResponse(content="Hello, world!")

        assert response.content == "Hello, world!"
        assert response.tool_calls is None
        assert response.usage is None

    def test_create_response_with_tool_calls(self):
        """Test creating response with tool calls"""
        tool_call = ToolCall(
            tool_id="call_123",
            tool_name="query_data",
            tool_input={"table": "issues"}
        )

        response = LLMResponse(
            content="",
            tool_calls=[tool_call]
        )

        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].tool_name == "query_data"

    def test_create_response_with_usage(self):
        """Test creating response with usage info"""
        response = LLMResponse(
            content="Test",
            usage={"input_tokens": 100, "output_tokens": 50}
        )

        assert response.usage["input_tokens"] == 100
        assert response.usage["output_tokens"] == 50


class TestToolCall:
    """Tests for ToolCall dataclass"""

    def test_create_tool_call(self):
        """Test creating a tool call"""
        tc = ToolCall(
            tool_id="call_abc",
            tool_name="search",
            tool_input={"query": "test"}
        )

        assert tc.tool_id == "call_abc"
        assert tc.tool_name == "search"
        assert tc.tool_input == {"query": "test"}


class TestMessage:
    """Tests for Message dataclass"""

    def test_create_user_message(self):
        """Test creating user message"""
        msg = Message(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.tool_calls is None

    def test_create_assistant_message_with_tools(self):
        """Test creating assistant message with tool calls"""
        tool_call = ToolCall("id", "name", {})
        msg = Message(
            role="assistant",
            content="Using tool",
            tool_calls=[tool_call]
        )

        assert msg.role == "assistant"
        assert len(msg.tool_calls) == 1

    def test_create_tool_response(self):
        """Test creating tool response message"""
        msg = Message(
            role="tool",
            content='{"result": "data"}',
            tool_call_id="call_123"
        )

        assert msg.role == "tool"
        assert msg.tool_call_id == "call_123"


class TestLLMProviderType:
    """Tests for LLMProviderType enum"""

    def test_provider_types_exist(self):
        """Test that all provider types exist"""
        assert LLMProviderType.ANTHROPIC.value == "anthropic"
        assert LLMProviderType.OPENAI.value == "openai"
        assert LLMProviderType.GOOGLE.value == "google"

    def test_from_string_anthropic(self):
        """Test creating provider type from string - anthropic"""
        result = LLMProviderType.from_string("anthropic")
        assert result == LLMProviderType.ANTHROPIC

        result = LLMProviderType.from_string("claude")
        assert result == LLMProviderType.ANTHROPIC

    def test_from_string_openai(self):
        """Test creating provider type from string - openai"""
        result = LLMProviderType.from_string("openai")
        assert result == LLMProviderType.OPENAI

        result = LLMProviderType.from_string("gpt")
        assert result == LLMProviderType.OPENAI

    def test_from_string_google(self):
        """Test creating provider type from string - google"""
        result = LLMProviderType.from_string("google")
        assert result == LLMProviderType.GOOGLE

        result = LLMProviderType.from_string("gemini")
        assert result == LLMProviderType.GOOGLE

    def test_from_string_invalid(self):
        """Test that invalid provider raises error"""
        with pytest.raises(ValueError):
            LLMProviderType.from_string("invalid_provider")

    def test_from_string_case_insensitive(self):
        """Test that from_string is case insensitive"""
        result = LLMProviderType.from_string("ANTHROPIC")
        assert result == LLMProviderType.ANTHROPIC


class TestLLMProviderFactory:
    """Tests for LLMProviderFactory"""

    def test_create_claude_provider(self):
        """Test creating Claude provider"""
        provider = LLMProviderFactory.create(
            LLMProviderType.ANTHROPIC,
            api_key="test-key"
        )

        assert isinstance(provider, ClaudeProvider)
        assert provider.api_key == "test-key"

    def test_create_openai_provider(self):
        """Test creating OpenAI provider"""
        provider = LLMProviderFactory.create(
            LLMProviderType.OPENAI,
            api_key="test-key"
        )

        assert isinstance(provider, OpenAIProvider)
        assert provider.api_key == "test-key"

    def test_create_gemini_provider(self):
        """Test creating Gemini provider"""
        provider = LLMProviderFactory.create(
            LLMProviderType.GOOGLE,
            api_key="test-key"
        )

        assert isinstance(provider, GeminiProvider)

    def test_create_with_custom_model(self):
        """Test creating provider with custom model"""
        provider = LLMProviderFactory.create(
            LLMProviderType.ANTHROPIC,
            api_key="test-key",
            model="claude-3-haiku-20240307"
        )

        assert provider.model == "claude-3-haiku-20240307"

    def test_create_from_env(self):
        """Test creating provider from environment values"""
        provider = LLMProviderFactory.create_from_env(
            provider_name="anthropic",
            api_key="test-key"
        )

        assert isinstance(provider, ClaudeProvider)

    def test_get_supported_providers(self):
        """Test getting list of supported providers"""
        providers = LLMProviderFactory.get_supported_providers()

        assert "anthropic" in providers
        assert "openai" in providers
        assert "google" in providers

    def test_get_default_model(self):
        """Test getting default model for provider"""
        model = LLMProviderFactory.get_default_model(LLMProviderType.ANTHROPIC)
        assert "claude" in model.lower()

        model = LLMProviderFactory.get_default_model(LLMProviderType.OPENAI)
        assert "gpt" in model.lower()


class TestClaudeProvider:
    """Tests for ClaudeProvider"""

    def test_provider_name(self):
        """Test provider name"""
        provider = ClaudeProvider(api_key="test")
        assert provider.provider_name == "anthropic"

    def test_default_model(self):
        """Test default model"""
        provider = ClaudeProvider(api_key="test")
        assert "claude" in provider.default_model.lower()

    def test_convert_tools(self):
        """Test tool conversion to Claude format"""
        provider = ClaudeProvider(api_key="test")

        tools = [{
            "name": "query_data",
            "description": "Query data from table",
            "parameters": {
                "type": "object",
                "properties": {
                    "table": {"type": "string"}
                }
            }
        }]

        converted = provider._convert_tools(tools)

        assert len(converted) == 1
        assert converted[0]["name"] == "query_data"
        assert "input_schema" in converted[0]

    def test_convert_messages_basic(self):
        """Test basic message conversion"""
        provider = ClaudeProvider(api_key="test")

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]

        converted = provider._convert_messages(messages)

        assert len(converted) == 2
        assert converted[0]["role"] == "user"
        assert converted[1]["role"] == "assistant"

    def test_convert_messages_tool_response(self):
        """Test tool response message conversion"""
        provider = ClaudeProvider(api_key="test")

        messages = [
            {
                "role": "tool",
                "tool_call_id": "call_123",
                "content": '{"result": "data"}'
            }
        ]

        converted = provider._convert_messages(messages)

        assert converted[0]["role"] == "user"
        assert converted[0]["content"][0]["type"] == "tool_result"


class TestOpenAIProvider:
    """Tests for OpenAIProvider"""

    def test_provider_name(self):
        """Test provider name"""
        provider = OpenAIProvider(api_key="test")
        assert provider.provider_name == "openai"

    def test_default_model(self):
        """Test default model"""
        provider = OpenAIProvider(api_key="test")
        assert "gpt" in provider.default_model.lower()

    def test_convert_tools(self):
        """Test tool conversion to OpenAI format"""
        provider = OpenAIProvider(api_key="test")

        tools = [{
            "name": "search",
            "description": "Search data",
            "parameters": {"type": "object", "properties": {}}
        }]

        converted = provider._convert_tools(tools)

        assert len(converted) == 1
        assert converted[0]["type"] == "function"
        assert converted[0]["function"]["name"] == "search"

    def test_convert_messages_basic(self):
        """Test basic message conversion"""
        provider = OpenAIProvider(api_key="test")

        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"}
        ]

        converted = provider._convert_messages(messages)

        assert len(converted) == 2
        assert converted[0]["role"] == "system"

    def test_convert_messages_tool_calls(self):
        """Test converting message with tool calls"""
        provider = OpenAIProvider(api_key="test")

        messages = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "tool_id": "call_123",
                        "tool_name": "search",
                        "tool_input": {"query": "test"}
                    }
                ]
            }
        ]

        converted = provider._convert_messages(messages)

        assert converted[0]["role"] == "assistant"
        assert len(converted[0]["tool_calls"]) == 1


class TestGeminiProvider:
    """Tests for GeminiProvider"""

    def test_provider_name(self):
        """Test provider name"""
        provider = GeminiProvider(api_key="test")
        assert provider.provider_name == "google"

    def test_default_model(self):
        """Test default model"""
        provider = GeminiProvider(api_key="test")
        assert "gemini" in provider.default_model.lower()

    def test_convert_messages_basic(self):
        """Test basic message conversion"""
        provider = GeminiProvider(api_key="test")

        messages = [
            {"role": "user", "content": "Hello"}
        ]

        converted = provider._convert_messages(messages)

        assert len(converted) == 1
        assert converted[0]["role"] == "user"
        assert converted[0]["parts"][0]["text"] == "Hello"

    def test_convert_messages_assistant(self):
        """Test assistant message conversion (maps to 'model')"""
        provider = GeminiProvider(api_key="test")

        messages = [
            {"role": "assistant", "content": "Hello back"}
        ]

        converted = provider._convert_messages(messages)

        assert converted[0]["role"] == "model"


class TestProviderIntegration:
    """Integration tests for providers (using mocks)"""

    @pytest.mark.asyncio
    async def test_claude_chat_mock(self):
        """Test Claude chat with mocked client"""
        provider = ClaudeProvider(api_key="test")

        # Mock the client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="Hello!")]
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=5)
        mock_response.model = "claude-3-sonnet"
        mock_response.stop_reason = "end_turn"

        with patch.object(provider.client.messages, 'create', return_value=mock_response):
            response = await provider.chat([
                {"role": "user", "content": "Hi"}
            ])

            assert response.content == "Hello!"

    @pytest.mark.asyncio
    async def test_openai_chat_mock(self):
        """Test OpenAI chat with mocked client"""
        provider = OpenAIProvider(api_key="test")

        # Mock the async client
        mock_message = MagicMock()
        mock_message.content = "Hello!"
        mock_message.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4"
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

        provider.client = AsyncMock()
        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        response = await provider.chat([
            {"role": "user", "content": "Hi"}
        ])

        assert response.content == "Hello!"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
