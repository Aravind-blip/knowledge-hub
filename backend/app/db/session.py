import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.base import Base

settings = get_settings()
engine = create_async_engine(settings.database_url, future=True)
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
        existing_tables = {row[0] for row in result}

    missing_tables = REQUIRED_TABLES - existing_tables
    if missing_tables:
        missing = ", ".join(sorted(missing_tables))
        raise RuntimeError(
            f"Database schema is not ready. Missing tables: {missing}. Run migrations before starting the app."
        )


async def run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[2]
    alembic_config = Config(str(repo_root / "alembic.ini"))
    alembic_config.set_main_option("sqlalchemy.url", settings.database_url)
    existing_tables = await _get_existing_tables()
    if REQUIRED_TABLES.issubset(existing_tables) and "alembic_version" not in existing_tables:
        await asyncio.to_thread(command.stamp, alembic_config, "head")
    await asyncio.to_thread(command.upgrade, alembic_config, "head")


async def _get_existing_tables() -> set[str]:
    async with engine.begin() as conn:
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
