from app.core.config import Settings


def test_generation_provider_resolves_to_groq_when_key_present() -> None:
    settings = Settings(
        _env_file=None,
        groq_api_key="groq-key",
        openai_api_key="test-key",
        generation_provider="auto",
        embedding_provider="auto",
        allow_fallback_models=True,
    )

    assert settings.resolved_generation_provider == "groq"
    assert settings.resolved_embedding_provider == "openai"


def test_provider_validation_fails_without_available_provider() -> None:
    settings = Settings.model_construct(
        groq_api_key=None,
        openai_api_key=None,
        generation_provider="auto",
        embedding_provider="auto",
        allow_fallback_models=False,
        langsmith_tracing=False,
        langsmith_api_key=None,
    )

    try:
        settings.validate_runtime()
    except ValueError as exc:
        assert "No generation provider is available" in str(exc)
    else:
        raise AssertionError("Expected validate_runtime to fail when no provider is configured.")


def test_langsmith_requires_api_key_when_enabled() -> None:
    settings = Settings.model_construct(
        groq_api_key=None,
        openai_api_key=None,
        generation_provider="fallback",
        embedding_provider="fallback",
        allow_fallback_models=True,
        langsmith_tracing=True,
        langsmith_api_key=None,
    )

    try:
        settings.validate_runtime()
    except ValueError as exc:
        assert "LANGSMITH_TRACING=true requires LANGSMITH_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected validate_runtime to fail when LangSmith is enabled without an API key.")


def test_database_url_normalizes_postgresql_scheme_for_asyncpg() -> None:
    settings = Settings(_env_file=None, database_url="postgresql://user:pass@db.example.com:5432/postgres")

    assert settings.database_url == "postgresql+asyncpg://user:pass@db.example.com:5432/postgres"


def test_database_url_normalizes_postgres_scheme_for_asyncpg() -> None:
    settings = Settings(_env_file=None, database_url="postgres://user:pass@db.example.com:5432/postgres")

    assert settings.database_url == "postgresql+asyncpg://user:pass@db.example.com:5432/postgres"


def test_database_url_converts_sslmode_to_asyncpg_ssl_param() -> None:
    settings = Settings(
        _env_file=None,
        database_url=(
            "postgresql://postgres.project:pass@aws-1-us-west-2.pooler.supabase.com:5432/postgres?sslmode=require"
        ),
    )

    assert (
        settings.database_url
        == "postgresql+asyncpg://postgres.project:pass@aws-1-us-west-2.pooler.supabase.com:5432/postgres?ssl=require"
    )
