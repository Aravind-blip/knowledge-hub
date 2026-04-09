from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class SourceCitation(BaseModel):
    chunk_id: UUID
    document_id: UUID
    file_name: str
    snippet: str
    page_number: Optional[int] = None
    relevance_score: float


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    citations: list[SourceCitation]
    metadata: dict[str, Any]
    created_at: datetime
