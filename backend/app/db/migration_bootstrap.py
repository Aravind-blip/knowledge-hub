from __future__ import annotations

from sqlalchemy import text

CORE_TABLES_WITH_USER_SCOPE = ("documents", "document_chunks", "chat_sessions", "chat_messages", "ingestion_jobs")
ORGANIZATION_TABLES = {"organizations", "organization_members"}


def determine_bootstrap_revision(table_names: set[str], has_column, head_revision: str) -> str:
    has_user_scope = all(has_column(table_name, "user_id") for table_name in CORE_TABLES_WITH_USER_SCOPE)
    has_org_scope = ORGANIZATION_TABLES.issubset(table_names) and all(
        has_column(table_name, "organization_id") for table_name in CORE_TABLES_WITH_USER_SCOPE
    )

    if has_org_scope:
        return head_revision
    if has_user_scope:
        return "20260409_0002"
    return "20260408_0001"


def stamp_legacy_revision(connection, revision: str, logger) -> None:
    connection.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"))
    connection.execute(text("DELETE FROM alembic_version"))
    connection.execute(
        text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
        {"revision": revision},
    )
    connection.commit()

    logger.info("Bootstrapped legacy schema revision", extra={"bootstrap_revision": revision})


def clear_implicit_transaction(connection, logger) -> None:
    if not connection.in_transaction():
        return

    connection.rollback()
    logger.debug("Rolled back implicit schema inspection transaction before Alembic migration run")
