"""LLM providers module."""

from app.llm.anthropic import AnthropicConfig, AnthropicProvider
from app.llm.base import LLMProvider, LLMProviderFactory
from app.llm.factory import create_embedding_provider, create_llm_provider
from app.llm.gemini import GeminiConfig, GeminiProvider
from app.llm.ollama import OllamaConfig, OllamaProvider
from app.llm.openai import OpenAIConfig, OpenAIProvider

# Register all providers
LLMProviderFactory.register("ollama", OllamaProvider)
LLMProviderFactory.register("openai", OpenAIProvider)
LLMProviderFactory.register("gemini", GeminiProvider)
LLMProviderFactory.register("anthropic", AnthropicProvider)

__all__ = [
    "AnthropicConfig",
    "AnthropicProvider",
    "GeminiConfig",
    "GeminiProvider",
    "LLMProvider",
    "LLMProviderFactory",
    "OllamaConfig",
    "OllamaProvider",
    "OpenAIConfig",
    "OpenAIProvider",
    "create_embedding_provider",
    "create_llm_provider",
]
