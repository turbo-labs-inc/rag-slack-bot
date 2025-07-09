"""Tests for configuration module."""

import pytest

from app.config import Environment, LLMProvider, Settings


def test_default_settings():
    """Test that default settings are loaded correctly."""
    settings = Settings(
        slack_bot_token="test-bot-token",
        slack_app_token="test-app-token",
        google_docs_id="test-doc-id",
    )

    assert settings.llm_provider == LLMProvider.OLLAMA
    assert settings.environment == Environment.DEVELOPMENT
    assert settings.log_level == "INFO"
    assert settings.chroma_host == "localhost"
    assert settings.chroma_port == 8000


def test_chroma_url():
    """Test ChromaDB URL construction."""
    settings = Settings(
        slack_bot_token="test-bot-token",
        slack_app_token="test-app-token",
        google_docs_id="test-doc-id",
        chroma_host="chromadb",
        chroma_port=8080,
    )

    assert settings.chroma_url == "http://chromadb:8080"


def test_validate_openai_config():
    """Test OpenAI configuration validation."""
    settings = Settings(
        slack_bot_token="test-bot-token",
        slack_app_token="test-app-token",
        google_docs_id="test-doc-id",
        llm_provider=LLMProvider.OPENAI,
    )

    with pytest.raises(ValueError, match="OpenAI API key is required"):
        settings.validate_provider_config()


def test_valid_openai_config():
    """Test valid OpenAI configuration."""
    settings = Settings(
        slack_bot_token="test-bot-token",
        slack_app_token="test-app-token",
        google_docs_id="test-doc-id",
        llm_provider=LLMProvider.OPENAI,
        openai_api_key="sk-test-key",
    )

    # Should not raise
    settings.validate_provider_config()
