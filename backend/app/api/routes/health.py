from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine
from app.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    settings = get_settings()
    database_status = "ready"
    try:
        async with engine.begin() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        database_status = "unavailable"
    return HealthResponse(
        status="ok" if database_status == "ready" else "degraded",
        environment=settings.app_env,
        provider_mode=settings.resolved_generation_provider,
        embedding_provider=settings.resolved_embedding_provider,
        tracing_enabled=settings.langsmith_tracing,
        database_status=database_status,
    )
