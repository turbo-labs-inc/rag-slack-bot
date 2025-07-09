"""Tests for LLM factory functions."""

from unittest.mock import patch

import pytest

from app.config import LLMProvider as LLMProviderEnum
from app.llm.factory import create_embedding_provider, create_llm_provider
from app.llm.ollama import OllamaProvider
from app.llm.openai import OpenAIProvider


class TestLLMFactory:
    """Test LLM factory functions."""

    @patch("app.llm.factory.get_settings")
    def test_create_ollama_provider(self, mock_get_settings):
        """Test creating Ollama provider."""
        mock_settings = mock_get_settings.return_value
        mock_settings.llm_provider = LLMProviderEnum.OLLAMA
        mock_settings.ollama_host = "http://test:11434"
        mock_settings.ollama_model = "llama3.2"

        provider = create_llm_provider()
        assert isinstance(provider, OllamaProvider)
        assert provider.config.host == "http://test:11434"
        assert provider.config.model == "llama3.2"

    @patch("app.llm.factory.get_settings")
    def test_create_openai_provider(self, mock_get_settings):
        """Test creating OpenAI provider."""
        mock_settings = mock_get_settings.return_value
        mock_settings.llm_provider = LLMProviderEnum.OPENAI
        mock_settings.openai_api_key = "test-key"

        provider = create_llm_provider()
        assert isinstance(provider, OpenAIProvider)
        assert provider.config.api_key == "test-key"

    @patch("app.llm.factory.get_settings")
    def test_create_openai_provider_missing_key(self, mock_get_settings):
        """Test creating OpenAI provider without API key."""
        mock_settings = mock_get_settings.return_value
        mock_settings.llm_provider = LLMProviderEnum.OPENAI
        mock_settings.openai_api_key = None

        with pytest.raises(ValueError, match="OpenAI API key is required"):
            create_llm_provider()

    @patch("app.llm.factory.get_settings")
    def test_create_embedding_provider_anthropic_fallback(self, mock_get_settings):
        """Test embedding provider fallback for Anthropic."""
        mock_settings = mock_get_settings.return_value
        mock_settings.llm_provider = LLMProviderEnum.ANTHROPIC
        mock_settings.openai_api_key = "test-key"

        provider = create_embedding_provider()
        assert isinstance(provider, OpenAIProvider)

    @patch("app.llm.factory.get_settings")
    def test_create_embedding_provider_anthropic_fallback_ollama(self, mock_get_settings):
        """Test embedding provider fallback to Ollama for Anthropic."""
        mock_settings = mock_get_settings.return_value
        mock_settings.llm_provider = LLMProviderEnum.ANTHROPIC
        mock_settings.openai_api_key = None
        mock_settings.ollama_host = "http://test:11434"
        mock_settings.ollama_model = "llama3.2"

        provider = create_embedding_provider()
        assert isinstance(provider, OllamaProvider)
