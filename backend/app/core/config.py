"""Core configuration for the Mindwell application."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql://mindwell:mindwell@localhost:5432/mindwell",
        description="PostgreSQL database URL",
    )

    # OpenAI API
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_api_base: str = Field(
        default="https://api.openai.com/v1", description="OpenAI API base URL"
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", description="Embedding model name"
    )
    openai_chat_model: str = Field(default="gpt-4-turbo-preview", description="Chat model name")

    # Application
    secret_key: str = Field(
        default="dev-secret-key-change-in-production", description="Secret key for JWT tokens"
    )
    environment: Literal["development", "staging", "production"] = Field(
        default="development", description="Application environment"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )

    # Auth
    access_token_expire_minutes: int = Field(
        default=60, description="Access token expiration time in minutes"
    )
    magic_link_expire_minutes: int = Field(
        default=15, description="Magic link expiration time in minutes"
    )

    # RAG
    chunk_size: int = Field(default=1000, description="Default chunk size for text splitting")
    chunk_overlap: int = Field(default=150, description="Overlap between chunks")
    top_k_retrieval: int = Field(default=5, description="Number of top chunks to retrieve")

    # CORS
    cors_origins: list[str] = Field(
        default=[],
        description="Allowed CORS origins for production (comma-separated via env var CORS_ORIGINS)",
    )

    # Safety
    enable_safety_checks: bool = Field(default=True, description="Enable safety guardrails")
    redact_pii: bool = Field(default=True, description="Redact PII from logs and storage")

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
