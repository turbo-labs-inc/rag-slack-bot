"""Factory for creating LLM providers from configuration."""

from app.config import LLMProvider as LLMProviderEnum
from app.config import get_settings
from app.llm.base import LLMProvider, LLMProviderFactory


def create_llm_provider(provider_name: str | None = None) -> LLMProvider:
    """Create LLM provider from configuration.

    Args:
        provider_name: Override provider name, defaults to settings.llm_provider

    Returns:
        Configured LLM provider instance

    Raises:
        ValueError: If provider configuration is invalid
    """
    settings = get_settings()
    provider_name = provider_name or settings.llm_provider

    # Build provider-specific config
    if provider_name == LLMProviderEnum.OLLAMA:
        from app.llm.ollama import OllamaConfig

        config = OllamaConfig(
            host=settings.ollama_host,
            model=settings.ollama_model,
        )
        return LLMProviderFactory.create("ollama", config=config)

    elif provider_name == LLMProviderEnum.OPENAI:
        from app.llm.openai import OpenAIConfig

        if not settings.openai_api_key:
            raise ValueError("OpenAI API key is required")

        config = OpenAIConfig(api_key=settings.openai_api_key)
        return LLMProviderFactory.create("openai", config=config)

    elif provider_name == LLMProviderEnum.GEMINI:
        from app.llm.gemini import GeminiConfig

        if not settings.gemini_api_key:
            raise ValueError("Gemini API key is required")

        config = GeminiConfig(api_key=settings.gemini_api_key)
        return LLMProviderFactory.create("gemini", config=config)

    elif provider_name == LLMProviderEnum.ANTHROPIC:
        from app.llm.anthropic import AnthropicConfig

        if not settings.anthropic_api_key:
            raise ValueError("Anthropic API key is required")

        config = AnthropicConfig(api_key=settings.anthropic_api_key)
        return LLMProviderFactory.create("anthropic", config=config)

    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")


def create_embedding_provider(provider_name: str | None = None) -> LLMProvider:
    """Create LLM provider specifically for embeddings.

    Note: Anthropic doesn't provide embeddings, so this will fallback to OpenAI
    or Ollama for embeddings even if Anthropic is selected for responses.

    Args:
        provider_name: Override provider name, defaults to settings.llm_provider

    Returns:
        Configured LLM provider instance suitable for embeddings

    Raises:
        ValueError: If no suitable embedding provider is available
    """
    settings = get_settings()
    provider_name = provider_name or settings.llm_provider

    # If using Anthropic, fallback to OpenAI or Ollama for embeddings
    if provider_name == LLMProviderEnum.ANTHROPIC:
        if settings.openai_api_key:
            return create_llm_provider(LLMProviderEnum.OPENAI)
        else:
            # Fallback to Ollama for embeddings
            return create_llm_provider(LLMProviderEnum.OLLAMA)

    # For other providers, use the same provider for embeddings
    return create_llm_provider(provider_name)
