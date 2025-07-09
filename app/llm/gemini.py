"""Google Gemini LLM provider implementation."""

import logging
from typing import Any

import google.generativeai as genai
from pydantic import BaseModel

from app.llm.base import EmbeddingResult, LLMProvider, ResponseResult

logger = logging.getLogger(__name__)


class GeminiConfig(BaseModel):
    """Configuration for Gemini provider."""

    api_key: str
    model: str = "gemini-1.5-flash"
    embedding_model: str = "models/text-embedding-004"
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout: int = 30


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider implementation."""

    def __init__(self, config: GeminiConfig | None = None, **kwargs: Any) -> None:
        """Initialize Gemini provider.

        Args:
            config: Gemini configuration
            **kwargs: Additional configuration options
        """
        self.config = config or GeminiConfig(**kwargs)
        genai.configure(api_key=self.config.api_key)
        self.model = genai.GenerativeModel(self.config.model)

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """Generate embedding using Gemini's embedding model.

        Args:
            text: Text to embed

        Returns:
            EmbeddingResult with embedding vector
        """
        try:
            result = genai.embed_content(
                model=self.config.embedding_model,
                content=text,
                task_type="retrieval_document",
            )

            return EmbeddingResult(
                embedding=result["embedding"],
                model=self.config.embedding_model,
                token_count=None,  # Gemini doesn't return token count for embeddings
            )

        except Exception as e:
            logger.error(f"Gemini embedding request failed: {e}")
            raise RuntimeError(f"Failed to generate embedding: {e}")

    async def generate_response(self, prompt: str, context: str | None = None) -> ResponseResult:
        """Generate response using Gemini's chat model.

        Args:
            prompt: User prompt or question
            context: Optional context information

        Returns:
            ResponseResult with generated response
        """
        # Construct full prompt with context if provided
        full_prompt = prompt
        if context:
            full_prompt = f"Context: {context}\n\nQuestion: {prompt}"

        try:
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                ),
            )

            return ResponseResult(
                response=response.text,
                model=self.config.model,
                token_count=response.usage_metadata.total_token_count
                if response.usage_metadata
                else None,
                finish_reason=response.candidates[0].finish_reason.name
                if response.candidates
                else None,
            )

        except Exception as e:
            logger.error(f"Gemini response request failed: {e}")
            raise RuntimeError(f"Failed to generate response: {e}")

    async def summarize(self, text: str, max_length: int = 100) -> ResponseResult:
        """Summarize text using Gemini.

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
        """Check if Gemini service is accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try a simple embedding request to test connectivity
            genai.embed_content(
                model=self.config.embedding_model,
                content="health check",
            )
            return True
        except Exception as e:
            logger.warning(f"Gemini health check failed: {e}")
            return False
