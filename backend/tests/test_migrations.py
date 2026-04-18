from pathlib import Path
from unittest.mock import Mock

import pytest

from app.db import session as db_session
from app.db.migration_bootstrap import (
    clear_implicit_transaction,
    determine_bootstrap_revision,
    stamp_legacy_revision,
)


def test_alembic_assets_exist() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    assert (repo_root / "backend" / "alembic.ini").exists()
    assert (repo_root / "infra" / "db" / "migrations" / "env.py").exists()
    assert (repo_root / "infra" / "db" / "migrations" / "versions" / "20260409_0002_user_ownership_and_rls.py").exists()
    assert (repo_root / "infra" / "db" / "migrations" / "versions" / "20260417_0003_organization_scope.py").exists()


@pytest.mark.anyio
async def test_run_migrations_uses_alembic_upgrade(monkeypatch) -> None:
    called = {}

    def fake_upgrade(config, revision):
        called["config_path"] = config.config_file_name
        called["revision"] = revision

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    async def fake_get_existing_tables():
        return set()

    monkeypatch.setattr("alembic.command.upgrade", fake_upgrade)
    monkeypatch.setattr(db_session.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(db_session, "_get_existing_tables", fake_get_existing_tables)

    await db_session.run_migrations()

    assert called["revision"] == "head"
    assert called["config_path"].endswith("backend/alembic.ini")


@pytest.mark.anyio
async def test_run_migrations_stamps_legacy_schema(monkeypatch) -> None:
    calls = []

    def fake_stamp(config, revision):
        calls.append(("stamp", revision, config.config_file_name))

    def fake_upgrade(config, revision):
        calls.append(("upgrade", revision, config.config_file_name))

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    async def fake_get_existing_tables():
        return set(db_session.REQUIRED_TABLES)

    monkeypatch.setattr("alembic.command.stamp", fake_stamp)
    monkeypatch.setattr("alembic.command.upgrade", fake_upgrade)
    monkeypatch.setattr(db_session.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(db_session, "_get_existing_tables", fake_get_existing_tables)

    await db_session.run_migrations()

    assert calls[0][0] == "stamp"
    assert calls[1][0] == "upgrade"


@pytest.mark.anyio
async def test_ensure_schema_ready_falls_back_to_metadata_create(monkeypatch) -> None:
    calls = {"count": 0, "init_db_called": False}

    async def fake_get_existing_tables_with_extension():
        calls["count"] += 1
        if calls["count"] == 1:
            return set()
        return set(db_session.REQUIRED_TABLES)

    async def fake_init_db():
        calls["init_db_called"] = True

    async def fake_get_missing_required_columns():
        return {}

    monkeypatch.setattr(db_session, "_get_existing_tables_with_extension", fake_get_existing_tables_with_extension)
    monkeypatch.setattr(db_session, "init_db", fake_init_db)
    monkeypatch.setattr(db_session, "_get_missing_required_columns", fake_get_missing_required_columns)

    await db_session.ensure_schema_ready()

    assert calls["init_db_called"] is True


@pytest.mark.anyio
async def test_ensure_schema_ready_fails_when_required_columns_missing(monkeypatch) -> None:
    async def fake_get_existing_tables_with_extension():
        return set(db_session.REQUIRED_TABLES)

    async def fake_get_missing_required_columns():
        return {"documents": {"organization_id"}}

    monkeypatch.setattr(db_session, "_get_existing_tables_with_extension", fake_get_existing_tables_with_extension)
    monkeypatch.setattr(db_session, "_get_missing_required_columns", fake_get_missing_required_columns)

    with pytest.raises(RuntimeError, match="Missing required columns: documents\\(organization_id\\)"):
        await db_session.ensure_schema_ready()


def test_determine_bootstrap_revision_prefers_org_schema() -> None:
    tables = set(db_session.REQUIRED_TABLES) | {"alembic_version"}
    tables.remove("alembic_version")

    def has_column(_table_name: str, column_name: str) -> bool:
        return column_name in {"user_id", "organization_id"}

    revision = determine_bootstrap_revision(tables, has_column, "20260417_0003")

    assert revision == "20260417_0003"


def test_determine_bootstrap_revision_uses_user_scope_for_pre_org_schema() -> None:
    tables = set(db_session.REQUIRED_TABLES) - {"organizations", "organization_members"}

    def has_column(_table_name: str, column_name: str) -> bool:
        return column_name == "user_id"

    revision = determine_bootstrap_revision(tables, has_column, "20260417_0003")

    assert revision == "20260409_0002"


def test_stamp_legacy_revision_commits_and_logs() -> None:
    calls = []
    logger = Mock()

    class DummyConnection:
        def execute(self, statement, params=None):
            calls.append((str(statement), params))

        def commit(self):
            calls.append("commit")

    stamp_legacy_revision(DummyConnection(), "20260409_0002", logger)

    assert "CREATE TABLE IF NOT EXISTS alembic_version" in calls[0][0]
    assert "DELETE FROM alembic_version" in calls[1][0]
    assert "INSERT INTO alembic_version" in calls[2][0]
    assert calls[2][1] == {"revision": "20260409_0002"}
    assert calls[3] == "commit"
    logger.info.assert_called_once_with(
        "Bootstrapped legacy schema revision",
        extra={"bootstrap_revision": "20260409_0002"},
    )


def test_clear_implicit_transaction_rolls_back_and_logs() -> None:
    logger = Mock()

    class DummyConnection:
        def __init__(self):
            self.rolled_back = False

        def in_transaction(self):
            return True

        def rollback(self):
            self.rolled_back = True

    connection = DummyConnection()
    clear_implicit_transaction(connection, logger)

    assert connection.rolled_back is True
    logger.debug.assert_called_once_with("Rolled back implicit schema inspection transaction before Alembic migration run")


def test_clear_implicit_transaction_noops_without_transaction() -> None:
    logger = Mock()

    class DummyConnection:
        def __init__(self):
            self.rolled_back = False

        def in_transaction(self):
            return False

        def rollback(self):
            self.rolled_back = True

    connection = DummyConnection()
    clear_implicit_transaction(connection, logger)

    assert connection.rolled_back is False
    logger.debug.assert_not_called()
