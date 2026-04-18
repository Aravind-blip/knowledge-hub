from datetime import datetime, timezone
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user, get_request_db_session
from app.main import app
from app.models import ChatSession
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
        full_name="Avery Example",
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


def test_sessions_route_returns_paginated_history(monkeypatch) -> None:
    class ScalarResult:
        def __init__(self, value):
            self.value = value

        def scalar(self):
            return self.value

    class SessionResult:
        def __init__(self, items):
            self.items = items

        def scalars(self):
            return self.items

    class FakeSession:
        def __init__(self):
            self.calls = 0

        async def scalar(self, statement):
            return 3

        async def execute(self, statement):
            self.calls += 1
            return SessionResult(
                [
                    ChatSession(
                        id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                        organization_id=UUID("22222222-2222-2222-2222-222222222222"),
                        user_id=UUID("11111111-1111-1111-1111-111111111111"),
                        title="Supplier escalation path",
                        created_at=datetime(2026, 4, 18, 12, 0, tzinfo=timezone.utc),
                        updated_at=datetime(2026, 4, 18, 12, 30, tzinfo=timezone.utc),
                    )
                ]
            )

    fake_session = FakeSession()

    async def override_fake_session():
        yield fake_session

    app.dependency_overrides[get_request_db_session] = override_fake_session
    app.dependency_overrides[get_current_user] = override_user
    client = TestClient(app)

    response = client.get("/api/chat/sessions?page=2&page_size=10")

    assert response.status_code == 200
    assert response.json()["page"] == 2
    assert response.json()["page_size"] == 10
    assert response.json()["total"] == 3
    assert response.json()["items"][0]["title"] == "Supplier escalation path"
    app.dependency_overrides.clear()
