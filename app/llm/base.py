"""Base LLM provider interface and factory pattern."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class EmbeddingResult(BaseModel):
    """Result from embedding generation."""

    embedding: list[float]
    model: str
    token_count: int | None = None


class ResponseResult(BaseModel):
    """Result from response generation."""

    response: str
    model: str
    token_count: int | None = None
    finish_reason: str | None = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """Generate embedding for the given text.

        Args:
            text: Text to embed

        Returns:
            EmbeddingResult with embedding vector and metadata
        """
        pass

    @abstractmethod
    async def generate_response(self, prompt: str, context: str | None = None) -> ResponseResult:
        """Generate response given a prompt and optional context.

        Args:
            prompt: User prompt or question
            context: Optional context information

        Returns:
            ResponseResult with generated response and metadata
        """
        pass

    @abstractmethod
    async def summarize(self, text: str, max_length: int = 100) -> ResponseResult:
        """Summarize the given text.

        Args:
            text: Text to summarize
            max_length: Maximum length of summary in words

        Returns:
            ResponseResult with summary and metadata
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy and accessible.

        Returns:
            True if healthy, False otherwise
        """
        pass


class LLMProviderFactory:
    """Factory for creating LLM providers."""

    _providers: dict[str, type[LLMProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: type[LLMProvider]) -> None:
        """Register a provider class.

        Args:
            name: Provider name (e.g., "ollama", "openai")
            provider_class: Provider class to register
        """
        cls._providers[name] = provider_class

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> LLMProvider:
        """Create a provider instance.

        Args:
            name: Provider name
            **kwargs: Provider-specific configuration

        Returns:
            LLMProvider instance

        Raises:
            ValueError: If provider name is not registered
        """
        if name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(f"Unknown provider '{name}'. Available: {available}")

        return cls._providers[name](**kwargs)

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names.

        Returns:
            List of provider names
        """
        return list(cls._providers.keys())
