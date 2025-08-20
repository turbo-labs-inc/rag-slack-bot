"""Ollama LLM provider implementation."""

import asyncio
import logging
from typing import Any

import httpx
from pydantic import BaseModel

from app.llm.base import EmbeddingResult, LLMProvider, ResponseResult

logger = logging.getLogger(__name__)


class OllamaConfig(BaseModel):
    """Configuration for Ollama provider."""

    host: str = "http://localhost:11434"
    model: str = "llama3.2"
    embedding_model: str = "nomic-embed-text"
    timeout: int = 30
    max_retries: int = 3


class OllamaProvider(LLMProvider):
    """Ollama LLM provider implementation."""

    def __init__(self, config: OllamaConfig | None = None, **kwargs: Any) -> None:
        """Initialize Ollama provider.

        Args:
            config: Ollama configuration
            **kwargs: Additional configuration options
        """
        self.config = config or OllamaConfig(**kwargs)
        self.client = httpx.AsyncClient(
            base_url=self.config.host,
            timeout=self.config.timeout,
        )

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """Generate embedding using Ollama's embedding model.

        Args:
            text: Text to embed

        Returns:
            EmbeddingResult with embedding vector
        """
        try:
            response = await self.client.post(
                "/api/embed",
                json={
                    "model": self.config.embedding_model,
                    "input": text,
                },
            )
            response.raise_for_status()
            data = response.json()

            # Ollama returns embeddings as an array with first element being the embedding
            embedding = data["embeddings"][0] if "embeddings" in data and data["embeddings"] else []

            return EmbeddingResult(
                embedding=embedding,
                model=self.config.embedding_model,
                token_count=None,  # Ollama doesn't return token count for embeddings
            )

        except httpx.RequestError as e:
            logger.error(f"Ollama embedding request failed: {e}")
            raise RuntimeError(f"Failed to generate embedding: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama embedding HTTP error: {e}")
            raise RuntimeError(f"Ollama API error: {e}")

    async def generate_response(self, prompt: str, context: str | None = None) -> ResponseResult:
        """Generate response using Ollama's chat model.

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
            logger.debug(f"Sending request to Ollama with model: {self.config.model}")
            logger.debug(f"Prompt length: {len(full_prompt)} characters")
            
            response = await self.client.post(
                "/api/generate",
                json={
                    "model": self.config.model,
                    "prompt": full_prompt,
                    "stream": False,
                },
                timeout=180.0,  # Increased timeout for longer prompts
            )
            
            logger.debug(f"Ollama response status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            
            logger.debug(f"Ollama response data keys: {data.keys()}")

            return ResponseResult(
                content=data["response"],
                model=self.config.model,
                token_count=data.get("eval_count"),
                finish_reason=data.get("done_reason"),
            )

        except httpx.TimeoutException as e:
            logger.error(f"Ollama request timed out after 180s: {e}")
            logger.error(f"Model: {self.config.model}, Prompt length: {len(full_prompt)}")
            raise RuntimeError(f"Ollama request timed out: {e}")
        except httpx.RequestError as e:
            logger.error(f"Ollama response request failed: {e}")
            logger.error(f"Model: {self.config.model}, Host: {self.config.host}")
            logger.error(f"Prompt length: {len(full_prompt)}")
            raise RuntimeError(f"Failed to generate response: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama response HTTP error: {e}")
            logger.error(f"Status: {e.response.status_code}")
            logger.error(f"Response text: {e.response.text}")
            logger.error(f"Model: {self.config.model}, Host: {self.config.host}")
            raise RuntimeError(f"Ollama API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in Ollama generate_response: {e}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Model: {self.config.model}, Host: {self.config.host}")
            raise RuntimeError(f"Unexpected error: {e}")

    async def summarize(self, text: str, max_length: int = 100) -> ResponseResult:
        """Summarize text using Ollama.

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
        """Check if Ollama service is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self.client.get("/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    async def ensure_models_available(self) -> None:
        """Ensure required models are available, pull if necessary.

        Raises:
            RuntimeError: If models cannot be pulled
        """
        models_to_check = [self.config.model, self.config.embedding_model]

        for model in models_to_check:
            if not await self._is_model_available(model):
                logger.info(f"Pulling model: {model}")
                await self._pull_model(model)

    async def _is_model_available(self, model: str) -> bool:
        """Check if a model is available locally.

        Args:
            model: Model name to check

        Returns:
            True if model is available, False otherwise
        """
        try:
            response = await self.client.get("/api/tags")
            if response.status_code == 200:
                data = response.json()
                available_models = [m["name"] for m in data.get("models", [])]
                return model in available_models
        except Exception as e:
            logger.warning(f"Failed to check model availability: {e}")

        return False

    async def _pull_model(self, model: str) -> None:
        """Pull a model from Ollama registry.

        Args:
            model: Model name to pull

        Raises:
            RuntimeError: If model cannot be pulled
        """
        try:
            response = await self.client.post(
                "/api/pull",
                json={"name": model},
                timeout=300,  # Pulling can take a while
            )

            if response.status_code != 200:
                raise RuntimeError(f"Failed to pull model {model}: {response.text}")

            # Wait for pull to complete
            await asyncio.sleep(5)

        except httpx.RequestError as e:
            logger.error(f"Failed to pull model {model}: {e}")
            raise RuntimeError(f"Failed to pull model {model}: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
