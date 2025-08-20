"""Configuration management using pydantic-settings."""

from enum import Enum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OLLAMA = "ollama"
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"


class Environment(str, Enum):
    """Application environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Slack Configuration
    slack_bot_token: str = Field(..., description="Slack bot user OAuth token")
    slack_app_token: str = Field(..., description="Slack app-level token for Socket Mode")

    # Google Docs Configuration
    google_docs_id: str | None = Field(None, description="Google Docs document ID to index")
    google_drive_folder_id: str | None = Field(None, description="Google Drive folder ID to index all files")
    google_file_ids: str | None = Field(None, description="Comma-separated list of Google file IDs to index")
    google_service_account_key_path: Path = Field(
        default=Path("./credentials/google-docs-service-account.json"),
        description="Path to Google service account credentials JSON",
    )

    # LLM Provider Configuration
    llm_provider: LLMProvider = Field(
        default=LLMProvider.OLLAMA,
        description="LLM provider to use for embeddings and responses",
    )

    # Ollama Configuration
    ollama_host: str = Field(
        default="http://localhost:11434",
        description="Ollama API host URL",
    )
    ollama_model: str = Field(
        default="llama3.2",
        description="Ollama model to use",
    )
    ollama_embedding_model: str = Field(
        default="nomic-embed-text",
        description="Ollama embedding model to use",
    )

    # OpenAI Configuration
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key",
    )

    # Google Gemini Configuration
    gemini_api_key: str | None = Field(
        default=None,
        description="Google Gemini API key",
    )
    gemini_model: str = Field(
        default="gemini-1.5-flash",
        description="Google Gemini model to use",
    )

    # Anthropic Configuration
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key",
    )

    # ChromaDB Configuration
    chroma_host: str = Field(
        default="localhost",
        description="ChromaDB host",
    )
    chroma_port: int = Field(
        default=8000,
        description="ChromaDB port",
    )

    # Application Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment",
    )

    @property
    def chroma_url(self) -> str:
        """Get the full ChromaDB URL."""
        return f"http://{self.chroma_host}:{self.chroma_port}"

    def validate_provider_config(self) -> None:
        """Validate that required API keys are set for the selected provider."""
        if self.llm_provider == LLMProvider.OPENAI and not self.openai_api_key:
            raise ValueError("OpenAI API key is required when using OpenAI provider")
        elif self.llm_provider == LLMProvider.GEMINI and not self.gemini_api_key:
            raise ValueError("Gemini API key is required when using Gemini provider")
        elif self.llm_provider == LLMProvider.ANTHROPIC and not self.anthropic_api_key:
            raise ValueError("Anthropic API key is required when using Anthropic provider")


# Global settings instance - lazy loaded
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
