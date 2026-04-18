from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import MessageResponse, SourceCitation


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    session_id: Optional[UUID] = None


class AskResponse(BaseModel):
    session_id: UUID
    answer: str
    citations: list[SourceCitation]
    retrieval_count: int
    insufficient_information: bool
    confidence_note: Optional[str] = None
    answer_message: MessageResponse
    question_message: MessageResponse


class ChatSessionResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse]


class ChatSessionSummary(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ChatSessionListResponse(BaseModel):
    items: list[ChatSessionSummary]
    total: int
    page: int
    page_size: int


class RetrieveRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


class RetrieveResponse(BaseModel):
    question: str
    citations: list[SourceCitation]
    retrieval_count: int
    insufficient_information: bool
    confidence_note: Optional[str] = None
