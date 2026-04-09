from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from app.db.session import get_db_session
from app.main import app
from app.services.ingestion import IngestionService


class DummySession:
    pass


@asynccontextmanager
async def override_session():
    yield DummySession()


async def fake_list_documents(self, session):
    return []


def test_documents_route_returns_empty_list(monkeypatch) -> None:
    app.dependency_overrides[get_db_session] = override_session
    monkeypatch.setattr(IngestionService, "list_documents", fake_list_documents)
    client = TestClient(app)

    response = client.get("/api/documents")

    assert response.status_code == 200
    assert response.json() == {"items": []}
    app.dependency_overrides.clear()
