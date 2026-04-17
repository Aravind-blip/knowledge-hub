from __future__ import annotations

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
