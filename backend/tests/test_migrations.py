from pathlib import Path

import pytest

from app.db import session as db_session


def test_alembic_assets_exist() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    assert (repo_root / "backend" / "alembic.ini").exists()
    assert (repo_root / "infra" / "db" / "migrations" / "env.py").exists()


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
