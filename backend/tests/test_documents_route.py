from contextlib import asynccontextmanager
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.db.session import get_db_session
from app.main import app
from app.services.ingestion import IngestionService


class DummySession:
    pass


@asynccontextmanager
async def override_session():
    yield DummySession()


async def override_user():
    yield CurrentUser(
        user_id=UUID("11111111-1111-1111-1111-111111111111"),
        email="user@example.com",
        access_token="token",
    )


async def fake_list_documents(self, session, user_id):
    assert str(user_id) == "11111111-1111-1111-1111-111111111111"
    return []


def test_documents_route_returns_empty_list(monkeypatch) -> None:
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_current_user] = override_user
    monkeypatch.setattr(IngestionService, "list_documents", fake_list_documents)
    client = TestClient(app)

    response = client.get("/api/documents")

    assert response.status_code == 200
    assert response.json() == {"items": []}
    app.dependency_overrides.clear()
