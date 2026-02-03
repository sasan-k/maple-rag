"""
Application settings using Pydantic Settings.

All configuration is loaded from environment variables.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===================
    # General Settings
    # ===================
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    # ===================
    # API Settings
    # ===================
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"

    # ===================
    # LLM Provider Settings
    # ===================
    llm_provider: Literal["azure_openai", "openai", "anthropic", "aws_bedrock"] = (
        "aws_bedrock"
    )

    # Azure OpenAI
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_deployment_name: str = "gpt-4o"
    azure_openai_embedding_deployment: str = "text-embedding-3-large"
    azure_openai_api_version: str = "2024-02-01"

    # OpenAI Direct (alternative)
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-large"

    # Anthropic (alternative)
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-sonnet-20240229"

    # AWS Bedrock
    aws_region: str = "ca-central-1"  # Canada Central region
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_bedrock_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    aws_bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"

    # ===================
    # Database Settings
    # ===================
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/canadaca",
        description="PostgreSQL connection URL with asyncpg driver",
    )
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # ===================
    # Redis Settings
    # ===================
    redis_url: str = "redis://localhost:6379"
    redis_ttl_seconds: int = 3600  # 1 hour default cache TTL

    # ===================
    # Security Settings
    # ===================
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 3600  # 1 hour

    # ===================
    # RAG Settings
    # ===================
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retrieval_top_k: int = 5
    embedding_dimensions: int = (
        1024  # amazon.titan-embed-text-v2:0 (use 3072 for OpenAI)
    )

    # ===================
    # Scraper Settings
    # ===================
    scraper_rate_limit_seconds: float = 1.0
    scraper_user_agent: str = "Canada.ca-ChatBot/1.0"
    scraper_timeout_seconds: int = 30

    # ===================
    # Observability
    # ===================
    langchain_tracing_v2: bool = False
    langchain_api_key: str | None = None
    langchain_project: str = "canadaca-chat"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL uses asyncpg driver."""
        if v and "postgresql://" in v and "asyncpg" not in v:
            v = v.replace("postgresql://", "postgresql+asyncpg://")
        return v

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
