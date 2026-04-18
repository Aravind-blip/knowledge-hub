from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user, get_request_db_session
from app.models import ChatSession, Document
from app.schemas.workspace import (
    MetricCardResponse,
    OrganizationActivityResponse,
    WorkspaceSummaryResponse,
)

router = APIRouter(prefix="/workspace", tags=["workspace"])
logger = logging.getLogger(__name__)


@router.get("/summary", response_model=WorkspaceSummaryResponse)
async def get_workspace_summary(
    session: AsyncSession = Depends(get_request_db_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> WorkspaceSummaryResponse:
    started = time.perf_counter()
    activity = await _build_activity_summary(session, current_user.organization_id)
    eval_metrics = _load_metrics("evals", "latest.json")
    load_metrics = _load_metrics("load", "latest.json")

    response = WorkspaceSummaryResponse(
        organization_name=current_user.organization_name,
        organization_slug=current_user.organization_slug,
        role=current_user.role,
        activity=activity,
        quality_metrics=[
            MetricCardResponse(
                label="Top-3 retrieval accuracy",
                value=_format_percentage(eval_metrics.get("top_3_retrieval_accuracy")),
                detail="Percentage of eval questions where an expected source appears in the top three citations.",
            ),
            MetricCardResponse(
                label="Grounded answer rate",
                value=_format_percentage(eval_metrics.get("grounded_answer_rate")),
                detail="Share of positive eval questions answered with grounded content tied to expected citations.",
            ),
            MetricCardResponse(
                label="Fallback precision",
                value=_format_percentage(eval_metrics.get("low_confidence_fallback_precision")),
                detail="How reliably ambiguous or negative questions trigger the explicit information-gap fallback.",
            ),
        ],
        performance_metrics=[
            MetricCardResponse(
                label="p95 answer latency",
                value=_format_milliseconds(eval_metrics.get("p95_answer_latency_ms")),
                detail="95th percentile time to complete an ask/answer request during automated evaluation.",
            ),
            MetricCardResponse(
                label="p95 search latency",
                value=_format_milliseconds(load_metrics.get("p95_query_latency_ms")),
                detail="95th percentile search latency from the reusable k6 workload.",
            ),
            MetricCardResponse(
                label="Ingestion success rate",
                value=_format_percentage(load_metrics.get("ingestion_success_rate")),
                detail="Upload/index success rate from the optional ingestion performance scenario.",
            ),
        ],
    )
    logger.info(
        "Built workspace summary",
        extra={
            "organization_id": str(current_user.organization_id),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "total_documents": activity.total_documents,
            "session_count": activity.session_count,
        },
    )
    return response


async def _build_activity_summary(session: AsyncSession, organization_id) -> OrganizationActivityResponse:
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    document_totals = await session.execute(
        select(
            func.count(Document.id),
            func.count(Document.id).filter(Document.status == "indexed"),
            func.count(Document.id).filter(Document.created_at >= thirty_days_ago),
        ).where(Document.organization_id == organization_id)
    )
    total_documents, indexed_documents, recent_uploads = document_totals.one()
    session_count = await session.scalar(
        select(func.count()).select_from(ChatSession).where(ChatSession.organization_id == organization_id)
    )
    return OrganizationActivityResponse(
        total_documents=int(total_documents or 0),
        indexed_documents=int(indexed_documents or 0),
        recent_uploads=int(recent_uploads or 0),
        session_count=int(session_count or 0),
    )


def _load_metrics(folder_name: str, file_name: str) -> dict:
    root = Path(__file__).resolve().parents[4]
    target = root / "artifacts" / folder_name / file_name
    if not target.exists():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload.get("metrics", {})


def _format_percentage(value: float | int | None) -> str:
    if value is None:
        return "Run evals"
    return f"{float(value) * 100:.0f}%"


def _format_milliseconds(value: float | int | None) -> str:
    if value is None:
        return "Run tests"
    return f"{float(value):.0f} ms"
