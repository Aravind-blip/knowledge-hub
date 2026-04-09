from fastapi.testclient import TestClient

from app.main import app


def test_health_check() -> None:
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}
    assert payload["environment"] == "development"
    assert payload["provider_mode"] in {"fallback", "openai", "groq"}
    assert payload["embedding_provider"] in {"fallback", "openai"}
    assert isinstance(payload["auth_enabled"], bool)
    assert isinstance(payload["tracing_enabled"], bool)
    assert payload["database_status"] in {"ready", "unavailable"}
