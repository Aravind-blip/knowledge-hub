from contextlib import asynccontextmanager
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user, get_request_db_session
from app.main import app
from app.schemas.common import SourceCitation
from app.services.retrieval import RetrievalResult, RetrievalService


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
        organization_id=UUID("22222222-2222-2222-2222-222222222222"),
        organization_name="Acme Workspace",
        organization_slug="acme-workspace",
        role="member",
    )


async def fake_retrieve(self, session, query, limit, organization_id, document_ids=None):
    assert str(organization_id) == "22222222-2222-2222-2222-222222222222"
    return RetrievalResult(
        citations=[
            SourceCitation(
                chunk_id=UUID("33333333-3333-3333-3333-333333333333"),
                document_id=UUID("44444444-4444-4444-4444-444444444444"),
                file_name="acme-policy.md",
                snippet="Acme-only organization snippet",
                relevance_score=0.91,
            )
        ],
        count=1,
    )


def test_retrieve_route_is_organization_scoped(monkeypatch) -> None:
    app.dependency_overrides[get_request_db_session] = override_session
    app.dependency_overrides[get_current_user] = override_user
    monkeypatch.setattr(RetrievalService, "retrieve", fake_retrieve)
    client = TestClient(app)

    response = client.post("/api/chat/retrieve", json={"question": "What is our policy?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["retrieval_count"] == 1
    assert payload["citations"][0]["file_name"] == "acme-policy.md"
    app.dependency_overrides.clear()
