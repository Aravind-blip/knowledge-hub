from pathlib import Path

import pytest

from app.db import session as db_session
from app.db.migration_bootstrap import determine_bootstrap_revision


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

    monkeypatch.setattr(db_session, "_get_existing_tables_with_extension", fake_get_existing_tables_with_extension)
    monkeypatch.setattr(db_session, "init_db", fake_init_db)

    await db_session.ensure_schema_ready()

    assert calls["init_db_called"] is True


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
