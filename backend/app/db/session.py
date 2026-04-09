import asyncio
import logging
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.db.base import Base

settings = get_settings()
logger = logging.getLogger(__name__)
engine_kwargs = {"future": True}
if "pooler.supabase.com" in settings.database_url:
    engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(settings.database_url, **engine_kwargs)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
REQUIRED_TABLES = {"documents", "document_chunks", "chat_sessions", "chat_messages", "ingestion_jobs"}


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)


async def ensure_schema_ready() -> None:
    existing_tables = await _get_existing_tables_with_extension()
    missing_tables = REQUIRED_TABLES - existing_tables

    if missing_tables:
        logger.warning(
            "Schema tables missing after startup preparation; attempting direct metadata creation",
            extra={"missing_tables": sorted(missing_tables)},
        )
        await init_db()
        existing_tables = await _get_existing_tables_with_extension()
        missing_tables = REQUIRED_TABLES - existing_tables

    if missing_tables:
        missing = ", ".join(sorted(missing_tables))
        raise RuntimeError(
            f"Database schema is not ready. Missing tables: {missing}. Run migrations before starting the app."
        )


async def _get_existing_tables_with_extension() -> set[str]:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        result = await conn.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
        )
        return {row[0] for row in result}


async def run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[2]
    alembic_config = Config(str(repo_root / "alembic.ini"))
    alembic_config.set_main_option("sqlalchemy.url", settings.database_url)
    try:
        existing_tables = await _get_existing_tables()
        if REQUIRED_TABLES.issubset(existing_tables) and "alembic_version" not in existing_tables:
            await asyncio.to_thread(command.stamp, alembic_config, "head")
        await asyncio.to_thread(command.upgrade, alembic_config, "head")
    except Exception:
        logger.exception("Alembic migration failed during startup")
        raise


async def _get_existing_tables() -> set[str]:
    return await _get_existing_tables_with_extension()
