"""Application configuration via pydantic-settings.

All settings are loaded from environment variables.
Use get_settings() to access the singleton instance.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """LexGrid application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── OpenAI ────────────────────────────────────────────────────────────
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI-compatible API base URL (override for OpenRouter etc.)",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model name",
    )
    llm_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI chat model name",
    )
    llm_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="LLM sampling temperature (0 = deterministic)",
    )
    llm_max_tokens: int = Field(
        default=1000,
        ge=100,
        le=4096,
        description="Maximum tokens for LLM response",
    )

    # ── Database ──────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://lexgrid:lexgrid@localhost:5432/lexgrid",
        description="Async PostgreSQL connection URL",
    )

    # ── Redis ─────────────────────────────────────────────────────────────
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching",
    )
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        description="Celery broker URL",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        description="Celery result backend URL",
    )

    # ── Pipeline ──────────────────────────────────────────────────────────
    embedding_batch_size: int = Field(
        default=100,
        ge=1,
        le=2048,
        description="Number of texts per OpenAI embedding batch",
    )
    top_k_retrieval: int = Field(
        default=20,
        ge=1,
        le=50,
        description="Number of chunks to retrieve before re-ranking",
    )
    top_k_rerank: int = Field(
        default=8,
        ge=1,
        le=20,
        description="Number of chunks to pass to LLM after re-ranking",
    )
    context_max_tokens: int = Field(
        default=6000,
        description="Maximum tokens in LLM context window",
    )

    # ── Cache ─────────────────────────────────────────────────────────────
    cache_ttl_seconds: int = Field(
        default=3600,
        description="Redis cache TTL in seconds",
    )

    # ── Paths ─────────────────────────────────────────────────────────────
    legal_acts_dir: str = Field(
        default="/app/legal-acts",
        description="Path to the legal-acts data directory",
    )

    # ── Logging ───────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO", description="Logging level")
    environment: str = Field(default="development", description="Runtime environment")

    # ── Derived properties ────────────────────────────────────────────────
    @property
    def legal_acts_path(self) -> Path:
        """Resolved Path to the legal-acts directory."""
        return Path(self.legal_acts_dir).resolve()

    @property
    def is_production(self) -> bool:
        """True if running in production environment."""
        return self.environment.lower() == "production"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return upper

    def __repr__(self) -> str:
        """Safe repr that masks the API key."""
        key = self.openai_api_key
        masked = f"{key[:7]}...{key[-4:]}" if len(key) > 11 else "***"
        return (
            f"Settings(model={self.llm_model!r}, "
            f"embedding={self.embedding_model!r}, "
            f"env={self.environment!r}, "
            f"openai_api_key={masked!r})"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings singleton.

    Use this everywhere instead of instantiating Settings() directly:
        from app.config import get_settings
        settings = get_settings()
    """
    return Settings()
