from __future__ import annotations

from pydantic import BaseModel


class MetricCardResponse(BaseModel):
    label: str
    value: str
    detail: str


class OrganizationActivityResponse(BaseModel):
    total_documents: int
    indexed_documents: int
    recent_uploads: int
    session_count: int


class WorkspaceSummaryResponse(BaseModel):
    organization_name: str
    organization_slug: str
    role: str
    activity: OrganizationActivityResponse
    quality_metrics: list[MetricCardResponse]
    performance_metrics: list[MetricCardResponse]
