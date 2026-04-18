from __future__ import annotations

import logging
from logging.config import fileConfig

from alembic import context
from alembic.script import ScriptDirectory
from sqlalchemy import inspect
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.db.base import Base
from app.db.migration_bootstrap import clear_implicit_transaction, determine_bootstrap_revision, stamp_legacy_revision
from app.models import *  # noqa: F403

config = context.config
logger = logging.getLogger(__name__)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata
required_tables = {
    "documents",
    "document_chunks",
    "chat_sessions",
    "chat_messages",
    "ingestion_jobs",
}


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    if bootstrap_legacy_schema(connection):
        return

    clear_implicit_transaction(connection, logger)
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def bootstrap_legacy_schema(connection) -> bool:
    table_names = set(inspect(connection).get_table_names(schema="public"))
    if not required_tables.issubset(table_names) or "alembic_version" in table_names:
        return False

    inspector = inspect(connection)

    def has_column(table_name: str, column_name: str) -> bool:
        return any(column["name"] == column_name for column in inspector.get_columns(table_name, schema="public"))

    revision = determine_bootstrap_revision(
        table_names=table_names,
        has_column=has_column,
        head_revision=ScriptDirectory.from_config(config).get_current_head(),
    )

    stamp_legacy_revision(connection, revision, logger)
    return True



async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_migrations_online())
