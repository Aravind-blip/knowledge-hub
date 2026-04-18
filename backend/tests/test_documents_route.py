from contextlib import asynccontextmanager
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.exc import ProgrammingError

from app.core.auth import CurrentUser, get_current_user, get_request_db_session
from app.main import app
from app.services.ingestion import IngestionService


class DummySession:
    def __init__(self):
        self.rollback_called = False

    async def rollback(self):
        self.rollback_called = True


@asynccontextmanager
async def override_session():
    yield DummySession()


async def override_user():
    yield CurrentUser(
        user_id=UUID("11111111-1111-1111-1111-111111111111"),
        email="user@example.com",
        access_token="token",
        full_name="Avery Example",
        organization_id=UUID("22222222-2222-2222-2222-222222222222"),
        organization_name="Acme Workspace",
        organization_slug="acme-workspace",
        role="admin",
    )


async def fake_list_documents(self, session, organization_id, *, offset=0, limit=20):
    assert str(organization_id) == "22222222-2222-2222-2222-222222222222"
    assert offset == 0
    assert limit == 20
    return [], 0


def test_documents_route_returns_empty_list(monkeypatch) -> None:
    app.dependency_overrides[get_request_db_session] = override_session
    app.dependency_overrides[get_current_user] = override_user
    monkeypatch.setattr(IngestionService, "list_documents", fake_list_documents)
    client = TestClient(app)

    response = client.get("/api/documents")

    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "page_size": 20, "total": 0}
    app.dependency_overrides.clear()


def test_documents_route_rolls_back_before_schema_retry(monkeypatch) -> None:
    session = DummySession()

    async def override_session_with_rollback():
        yield session

    calls = {"count": 0, "schema_checked": False}

    async def flaky_list_documents(self, db_session, organization_id, *, offset=0, limit=20):
        calls["count"] += 1
        assert str(organization_id) == "22222222-2222-2222-2222-222222222222"
        if calls["count"] == 1:
            raise ProgrammingError("SELECT 1", {}, Exception("missing column"))
        return [], 0

    async def fake_ensure_schema_ready():
        calls["schema_checked"] = True

    app.dependency_overrides[get_request_db_session] = override_session_with_rollback
    app.dependency_overrides[get_current_user] = override_user
    monkeypatch.setattr(IngestionService, "list_documents", flaky_list_documents)
    monkeypatch.setattr("app.api.routes.documents.ensure_schema_ready", fake_ensure_schema_ready)
    client = TestClient(app)

    response = client.get("/api/documents")

    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "page_size": 20, "total": 0}
    assert session.rollback_called is True
    assert calls["schema_checked"] is True
    assert calls["count"] == 2
    app.dependency_overrides.clear()
