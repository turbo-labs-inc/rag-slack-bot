"""OpenAI LLM provider implementation."""

import logging
from typing import Any

import openai
from pydantic import BaseModel

from app.llm.base import EmbeddingResult, LLMProvider, ResponseResult

logger = logging.getLogger(__name__)


class OpenAIConfig(BaseModel):
    """Configuration for OpenAI provider."""

    api_key: str
    model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout: int = 30
    max_retries: int = 3


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider implementation."""

    def __init__(self, config: OpenAIConfig | None = None, **kwargs: Any) -> None:
        """Initialize OpenAI provider.

        Args:
            config: OpenAI configuration
            **kwargs: Additional configuration options
        """
        self.config = config or OpenAIConfig(**kwargs)
        self.client = openai.AsyncOpenAI(
            api_key=self.config.api_key,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries,
        )

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """Generate embedding using OpenAI's embedding model.

        Args:
            text: Text to embed

        Returns:
            EmbeddingResult with embedding vector
        """
        try:
            response = await self.client.embeddings.create(
                model=self.config.embedding_model,
                input=text,
            )

            embedding_data = response.data[0]

            return EmbeddingResult(
                embedding=embedding_data.embedding,
                model=self.config.embedding_model,
                token_count=response.usage.total_tokens,
            )

        except openai.OpenAIError as e:
            logger.error(f"OpenAI embedding request failed: {e}")
            raise RuntimeError(f"Failed to generate embedding: {e}")

    async def generate_response(self, prompt: str, context: str | None = None) -> ResponseResult:
        """Generate response using OpenAI's chat model.

        Args:
            prompt: User prompt or question
            context: Optional context information

        Returns:
            ResponseResult with generated response
        """
        messages = []

        if context:
            messages.append(
                {
                    "role": "system",
                    "content": f"Use the following context to answer the user's question: {context}",
                }
            )

        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )

            choice = response.choices[0]

            return ResponseResult(
                response=choice.message.content or "",
                model=self.config.model,
                token_count=response.usage.total_tokens if response.usage else None,
                finish_reason=choice.finish_reason,
            )

        except openai.OpenAIError as e:
            logger.error(f"OpenAI response request failed: {e}")
            raise RuntimeError(f"Failed to generate response: {e}")

    async def summarize(self, text: str, max_length: int = 100) -> ResponseResult:
        """Summarize text using OpenAI.

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
        """Check if OpenAI service is accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try a simple embedding request to test connectivity
            await self.client.embeddings.create(
                model=self.config.embedding_model,
                input="health check",
            )
            return True
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
            return False
