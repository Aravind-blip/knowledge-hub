import logging

from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.db.session import engine, ensure_schema_ready

logger = logging.getLogger(__name__)


async def initialize_runtime() -> None:
    settings = get_settings()
    settings.validate_runtime()

    logger.info(
        "Runtime configuration loaded",
        extra={
            "environment": settings.app_env,
            "provider_mode": settings.resolved_generation_provider,
            "generation_provider": settings.resolved_generation_provider,
            "embedding_provider": settings.resolved_embedding_provider,
            "tracing_enabled": settings.langsmith_tracing,
            "database_url_masked": mask_database_url(settings.database_url),
        },
    )

    await verify_database(settings)
    await ensure_schema_ready()

    logger.info(
        "Startup checks completed",
        extra={
            "environment": settings.app_env,
            "provider_mode": settings.resolved_generation_provider,
            "generation_provider": settings.resolved_generation_provider,
            "embedding_provider": settings.resolved_embedding_provider,
            "tracing_enabled": settings.langsmith_tracing,
            "database_status": "ready",
        },
    )


async def verify_database(settings: Settings) -> None:
    try:
        async with engine.begin() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise RuntimeError(
            "Database connectivity check failed. Confirm DATABASE_URL is reachable and migrations have been run."
        ) from exc


def mask_database_url(database_url: str) -> str:
    if "@" not in database_url:
        return database_url
    credentials, host = database_url.split("@", 1)
    if "://" not in credentials:
        return database_url
    scheme, _ = credentials.split("://", 1)
    return f"{scheme}://***@{host}"
