"""Factory for creating LLM providers"""
from enum import Enum
from typing import Optional
import logging

from .base import BaseLLMProvider
from .claude_provider import ClaudeProvider
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class LLMProviderType(str, Enum):
    """Supported LLM provider types"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    GEMINI = "gemini"  # Alias for google

    @classmethod
    def from_string(cls, value: str) -> "LLMProviderType":
        """Convert string to provider type"""
        value = value.lower().strip()
        if value in ("anthropic", "claude"):
            return cls.ANTHROPIC
        elif value in ("openai", "gpt"):
            return cls.OPENAI
        elif value in ("google", "gemini"):
            return cls.GOOGLE
        else:
            raise ValueError(f"Unknown provider type: {value}")


class LLMProviderFactory:
    """Factory for creating LLM providers"""

    _providers = {
        LLMProviderType.ANTHROPIC: ClaudeProvider,
        LLMProviderType.OPENAI: OpenAIProvider,
        LLMProviderType.GOOGLE: GeminiProvider,
        LLMProviderType.GEMINI: GeminiProvider,
    }

    _default_models = {
        LLMProviderType.ANTHROPIC: "claude-sonnet-4-20250514",
        LLMProviderType.OPENAI: "gpt-4o",
        LLMProviderType.GOOGLE: "gemini-1.5-pro",
        LLMProviderType.GEMINI: "gemini-1.5-pro",
    }

    @classmethod
    def create(
        cls,
        provider_type: LLMProviderType,
        api_key: str,
        model: Optional[str] = None
    ) -> BaseLLMProvider:
        """Create an LLM provider instance"""
        if provider_type not in cls._providers:
            raise ValueError(f"Unknown provider type: {provider_type}")

        provider_class = cls._providers[provider_type]
        model = model or cls._default_models.get(provider_type)

        logger.info(f"Creating {provider_type.value} provider with model: {model}")
        return provider_class(api_key=api_key, model=model)

    @classmethod
    def create_from_env(
        cls,
        provider_name: str,
        api_key: str,
        model: Optional[str] = None
    ) -> BaseLLMProvider:
        """Create provider from environment variable values"""
        try:
            provider_type = LLMProviderType.from_string(provider_name)
            return cls.create(provider_type, api_key, model)
        except ValueError as e:
            logger.error(f"Failed to create provider: {e}")
            raise

    @classmethod
    def get_supported_providers(cls) -> list:
        """Get list of supported provider names"""
        return [p.value for p in LLMProviderType]

    @classmethod
    def get_default_model(cls, provider_type: LLMProviderType) -> str:
        """Get the default model for a provider"""
        return cls._default_models.get(provider_type, "")
