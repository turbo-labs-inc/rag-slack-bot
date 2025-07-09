"""Tests for LLM providers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.base import EmbeddingResult, LLMProviderFactory, ResponseResult
from app.llm.ollama import OllamaConfig, OllamaProvider
from app.llm.openai import OpenAIConfig, OpenAIProvider


class TestLLMProviderFactory:
    """Test the LLM provider factory."""

    def test_list_providers(self):
        """Test listing registered providers."""
        providers = LLMProviderFactory.list_providers()
        assert "ollama" in providers
        assert "openai" in providers
        assert "gemini" in providers
        assert "anthropic" in providers

    def test_create_ollama_provider(self):
        """Test creating Ollama provider."""
        provider = LLMProviderFactory.create("ollama", host="http://test:11434")
        assert isinstance(provider, OllamaProvider)
        assert provider.config.host == "http://test:11434"

    def test_create_openai_provider(self):
        """Test creating OpenAI provider."""
        provider = LLMProviderFactory.create("openai", api_key="test-key")
        assert isinstance(provider, OpenAIProvider)
        assert provider.config.api_key == "test-key"

    def test_create_unknown_provider(self):
        """Test creating unknown provider raises error."""
        with pytest.raises(ValueError, match="Unknown provider 'unknown'"):
            LLMProviderFactory.create("unknown")


class TestOllamaProvider:
    """Test Ollama provider."""

    @pytest.fixture
    def ollama_provider(self):
        """Create Ollama provider for testing."""
        config = OllamaConfig(host="http://test:11434")
        return OllamaProvider(config=config)

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, ollama_provider):
        """Test successful embedding generation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"embeddings": [[0.1, 0.2, 0.3, 0.4]]}
        mock_response.raise_for_status.return_value = None

        with patch.object(ollama_provider.client, "post", return_value=mock_response):
            result = await ollama_provider.generate_embedding("test text")

            assert isinstance(result, EmbeddingResult)
            assert result.embedding == [0.1, 0.2, 0.3, 0.4]
            assert result.model == "nomic-embed-text"

    @pytest.mark.asyncio
    async def test_generate_response_success(self, ollama_provider):
        """Test successful response generation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": "This is a test response",
            "eval_count": 50,
            "done_reason": "stop",
        }
        mock_response.raise_for_status.return_value = None

        with patch.object(ollama_provider.client, "post", return_value=mock_response):
            result = await ollama_provider.generate_response("test prompt")

            assert isinstance(result, ResponseResult)
            assert result.response == "This is a test response"
            assert result.model == "llama3.2"
            assert result.token_count == 50

    @pytest.mark.asyncio
    async def test_generate_response_with_context(self, ollama_provider):
        """Test response generation with context."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Response with context", "eval_count": 75}
        mock_response.raise_for_status.return_value = None

        with patch.object(ollama_provider.client, "post", return_value=mock_response) as mock_post:
            result = await ollama_provider.generate_response("test prompt", "test context")

            # Verify the prompt includes context
            call_args = mock_post.call_args
            prompt = call_args[1]["json"]["prompt"]
            assert "Context: test context" in prompt
            assert "Question: test prompt" in prompt

    @pytest.mark.asyncio
    async def test_health_check_success(self, ollama_provider):
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(ollama_provider.client, "get", return_value=mock_response):
            result = await ollama_provider.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, ollama_provider):
        """Test failed health check."""
        with patch.object(ollama_provider.client, "get", side_effect=Exception("Connection error")):
            result = await ollama_provider.health_check()
            assert result is False


class TestOpenAIProvider:
    """Test OpenAI provider."""

    @pytest.fixture
    def openai_provider(self):
        """Create OpenAI provider for testing."""
        config = OpenAIConfig(api_key="test-key")
        return OpenAIProvider(config=config)

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, openai_provider):
        """Test successful embedding generation."""
        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1, 0.2, 0.3, 0.4]

        mock_response = MagicMock()
        mock_response.data = [mock_embedding]
        mock_response.usage.total_tokens = 10

        with patch.object(
            openai_provider.client.embeddings,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await openai_provider.generate_embedding("test text")

            assert isinstance(result, EmbeddingResult)
            assert result.embedding == [0.1, 0.2, 0.3, 0.4]
            assert result.model == "text-embedding-3-small"
            assert result.token_count == 10

    @pytest.mark.asyncio
    async def test_generate_response_success(self, openai_provider):
        """Test successful response generation."""
        mock_choice = MagicMock()
        mock_choice.message.content = "This is a test response"
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.total_tokens = 50

        with patch.object(
            openai_provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await openai_provider.generate_response("test prompt")

            assert isinstance(result, ResponseResult)
            assert result.response == "This is a test response"
            assert result.model == "gpt-4o-mini"
            assert result.token_count == 50
            assert result.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_generate_response_with_context(self, openai_provider):
        """Test response generation with context."""
        mock_choice = MagicMock()
        mock_choice.message.content = "Response with context"
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.total_tokens = 75

        with patch.object(
            openai_provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_create:
            result = await openai_provider.generate_response("test prompt", "test context")

            # Verify the messages include context
            call_args = mock_create.call_args
            messages = call_args[1]["messages"]
            assert len(messages) == 2
            assert "context" in messages[0]["content"].lower()
            assert messages[1]["content"] == "test prompt"
