"""Anthropic Claude LLM provider implementation."""

import logging
from typing import Any

import anthropic
from pydantic import BaseModel

from app.llm.base import EmbeddingResult, LLMProvider, ResponseResult

logger = logging.getLogger(__name__)


class AnthropicConfig(BaseModel):
    """Configuration for Anthropic provider."""

    api_key: str
    model: str = "claude-3-5-haiku-20241022"
    # Note: Anthropic doesn't provide embeddings, so we'll need to use another provider
    # or implement a fallback strategy
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout: int = 30


class AnthropicProvider(LLMProvider):
    """Anthropic Claude LLM provider implementation."""

    def __init__(self, config: AnthropicConfig | None = None, **kwargs: Any) -> None:
        """Initialize Anthropic provider.

        Args:
            config: Anthropic configuration
            **kwargs: Additional configuration options
        """
        self.config = config or AnthropicConfig(**kwargs)
        self.client = anthropic.AsyncAnthropic(
            api_key=self.config.api_key,
            timeout=self.config.timeout,
        )

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """Generate embedding - Anthropic doesn't provide embeddings.

        Args:
            text: Text to embed

        Returns:
            EmbeddingResult with embedding vector

        Raises:
            NotImplementedError: Anthropic doesn't provide embeddings
        """
        raise NotImplementedError(
            "Anthropic doesn't provide embeddings. Use a different provider for embeddings "
            "(e.g., OpenAI, Sentence Transformers) or implement a hybrid approach."
        )

    async def generate_response(self, prompt: str, context: str | None = None) -> ResponseResult:
        """Generate response using Anthropic's Claude model.

        Args:
            prompt: User prompt or question
            context: Optional context information

        Returns:
            ResponseResult with generated response
        """
        messages = []

        if context:
            messages.append(
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {prompt}"}
            )
        else:
            messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=messages,
            )

            # Anthropic returns content as a list of blocks
            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text

            return ResponseResult(
                response=content,
                model=self.config.model,
                token_count=response.usage.output_tokens + response.usage.input_tokens,
                finish_reason=response.stop_reason,
            )

        except anthropic.AnthropicError as e:
            logger.error(f"Anthropic response request failed: {e}")
            raise RuntimeError(f"Failed to generate response: {e}")

    async def summarize(self, text: str, max_length: int = 100) -> ResponseResult:
        """Summarize text using Anthropic Claude.

        Args:
            text: Text to summarize
            max_length: Maximum length of summary in words

        Returns:
            ResponseResult with summary
        """
        prompt = f"""Please provide a concise summary of the following text in no more than {max_length} words:

{text}

Summary:"""

        return await self.generate_response(prompt)

    async def health_check(self) -> bool:
        """Check if Anthropic service is accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try a simple message to test connectivity
            await self.client.messages.create(
                model=self.config.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True
        except Exception as e:
            logger.warning(f"Anthropic health check failed: {e}")
            return False
