from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import AliasChoices, Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Knowledge Hub API"
    app_env: str = "development"
    log_level: str = "INFO"
    api_port: int = 8000
    allowed_origins_raw: str = "http://localhost:3000"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/knowledge_hub"
    max_upload_size_mb: int = 15
    upload_dir: Path = Path("./data/uploads")
    chunk_size: int = 1000
    chunk_overlap: int = 150
    retrieval_limit: int = 6
    retrieval_min_score: float = 0.3
    retrieval_min_term_overlap: int = 1
    answer_min_score: float = 0.35

    groq_api_key: Optional[str] = None
    groq_chat_model: str = "llama-3.1-8b-instant"
    openai_api_key: Optional[str] = None
    openai_chat_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    generation_provider: Literal["auto", "groq", "openai", "fallback"] = Field(
        default="auto",
        validation_alias=AliasChoices("GENERATION_PROVIDER", "PROVIDER_MODE"),
    )
    embedding_provider: Literal["auto", "openai", "fallback"] = "auto"
    allow_fallback_models: bool = Field(
        default=True,
        validation_alias=AliasChoices("ALLOW_FALLBACK_MODELS", "USE_FALLBACK_MODELS"),
    )

    langsmith_tracing: bool = Field(
        default=False,
        validation_alias=AliasChoices("LANGSMITH_TRACING", "ENABLE_LANGSMITH"),
    )
    langsmith_api_key: Optional[str] = None
    langsmith_project: str = "knowledge-hub"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    run_db_migrations_on_startup: bool = False

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        if not isinstance(value, str):
            return value

        if value.startswith("postgresql+asyncpg://"):
            normalized = value
        elif value.startswith("postgresql://"):
            normalized = value.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif value.startswith("postgres://"):
            normalized = value.replace("postgres://", "postgresql+asyncpg://", 1)
        else:
            return value

        parts = urlsplit(normalized)
        query_items = []
        for key, item_value in parse_qsl(parts.query, keep_blank_values=True):
            if key == "sslmode":
                query_items.append(("ssl", item_value))
            else:
                query_items.append((key, item_value))

        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query_items), parts.fragment))

    @computed_field
    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins_raw.split(",") if origin.strip()]

    @computed_field
    @property
    def resolved_generation_provider(self) -> Literal["groq", "openai", "fallback"]:
        if self.generation_provider == "groq":
            return "groq"
        if self.generation_provider == "openai":
            return "openai"
        if self.generation_provider == "fallback":
            return "fallback"
        if self.groq_api_key:
            return "groq"
        if self.openai_api_key:
            return "openai"
        return "fallback"

    @computed_field
    @property
    def resolved_embedding_provider(self) -> Literal["openai", "fallback"]:
        if self.embedding_provider == "openai":
            return "openai"
        if self.embedding_provider == "fallback":
            return "fallback"
        if self.openai_api_key:
            return "openai"
        return "fallback"

    def validate_runtime(self) -> None:
        if self.generation_provider == "groq" and not self.groq_api_key:
            raise ValueError("GENERATION_PROVIDER=groq requires GROQ_API_KEY to be set.")

        if self.generation_provider == "openai" and not self.openai_api_key:
            raise ValueError("GENERATION_PROVIDER=openai requires OPENAI_API_KEY to be set.")

        if self.embedding_provider == "openai" and not self.openai_api_key:
            raise ValueError("EMBEDDING_PROVIDER=openai requires OPENAI_API_KEY to be set.")

        if (
            self.generation_provider == "auto"
            and not self.groq_api_key
            and not self.openai_api_key
            and not self.allow_fallback_models
        ):
            raise ValueError(
                "No generation provider is available. Set GROQ_API_KEY, OPENAI_API_KEY, or enable ALLOW_FALLBACK_MODELS."
            )

        if self.embedding_provider == "auto" and not self.openai_api_key and not self.allow_fallback_models:
            raise ValueError(
                "No embedding provider is available. Set OPENAI_API_KEY or enable ALLOW_FALLBACK_MODELS."
            )

        if self.generation_provider == "fallback" and not self.allow_fallback_models:
            raise ValueError("GENERATION_PROVIDER=fallback requires ALLOW_FALLBACK_MODELS=true.")

        if self.embedding_provider == "fallback" and not self.allow_fallback_models:
            raise ValueError("EMBEDDING_PROVIDER=fallback requires ALLOW_FALLBACK_MODELS=true.")

        if self.langsmith_tracing and not self.langsmith_api_key:
            raise ValueError("LANGSMITH_TRACING=true requires LANGSMITH_API_KEY to be set.")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings
