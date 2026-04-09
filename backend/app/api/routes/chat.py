from __future__ import annotations

import logging
import time
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.qa_graph import build_qa_graph
from app.core.auth import CurrentUser, get_current_user
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models import ChatMessage, ChatSession
from app.schemas.chat import (
    AskRequest,
    AskResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatSessionSummary,
    RetrieveRequest,
    RetrieveResponse,
)
from app.schemas.common import MessageResponse
from app.services.embeddings import get_embedding_service
from app.services.generation import get_generation_service
from app.services.observability.tracer import get_trace_service
from app.services.retrieval import RetrievalService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()


def serialize_message(message: ChatMessage) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        citations=message.citations_json,
        metadata=message.metadata_json,
        created_at=message.created_at,
    )


@router.post("/ask", response_model=AskResponse)
async def ask_question(
    payload: AskRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> AskResponse:
    started = time.perf_counter()
    trace_service = get_trace_service()
    retrieval_service = RetrievalService(get_embedding_service())
    generation_service = get_generation_service()
    qa_graph = build_qa_graph(generation_service)

    async with trace_service.trace(
        "ask_question",
        metadata={
            "session_id": str(payload.session_id) if payload.session_id else None,
            "model_provider": generation_service.provider_name,
            "model_name": generation_service.model_name,
        },
        inputs={"question": payload.question},
    ) as span:
        chat_session = await ensure_session(session, payload.session_id, payload.question, current_user.user_id)
        history = await get_history(session, chat_session.id, current_user.user_id)
        retrieval_query = " ".join([entry[1] for entry in history[-4:] if entry[0] == "user"] + [payload.question])
        retrieval = await retrieval_service.retrieve(session, retrieval_query, settings.retrieval_limit, current_user.user_id)
        graph_result = await qa_graph.ainvoke(
            {
                "question": payload.question,
                "history": history,
                "retrieval_result": retrieval,
                "citations": [],
                "retrieval_count": 0,
                "answer": "",
                "insufficient_information": False,
            }
        )

        user_message = ChatMessage(
            user_id=current_user.user_id,
            session_id=chat_session.id,
            role="user",
            content=payload.question,
            citations_json=[],
            metadata_json={},
        )
        answer_message = ChatMessage(
            user_id=current_user.user_id,
            session_id=chat_session.id,
            role="system",
            content=graph_result["answer"],
            citations_json=[citation.model_dump(mode="json") for citation in graph_result["citations"]],
            metadata_json={
                "insufficient_information": graph_result["insufficient_information"],
                "retrieval_count": graph_result["retrieval_count"],
                "confidence_note": graph_result.get("confidence_note"),
            },
        )
        session.add_all([user_message, answer_message])
        await session.commit()
        await session.refresh(user_message)
        await session.refresh(answer_message)

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "Question answered",
            extra={
                "session_id": str(chat_session.id),
                "latency_ms": latency_ms,
                "retrieved_count": retrieval.count,
                "model_provider": generation_service.provider_name,
                "model_name": generation_service.model_name,
                "user_id": str(current_user.user_id),
            },
        )
        span.set_outputs(
            retrieval_count=graph_result["retrieval_count"],
            insufficient_information=graph_result["insufficient_information"],
            citation_count=len(graph_result["citations"]),
        )

        return AskResponse(
            session_id=chat_session.id,
            answer=graph_result["answer"],
            citations=graph_result["citations"],
            retrieval_count=graph_result["retrieval_count"],
            insufficient_information=graph_result["insufficient_information"],
            confidence_note=graph_result.get("confidence_note"),
            answer_message=serialize_message(answer_message),
            question_message=serialize_message(user_message),
        )


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_sources(
    payload: RetrieveRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> RetrieveResponse:
    trace_service = get_trace_service()
    retrieval_service = RetrievalService(get_embedding_service())
    async with trace_service.trace(
        "retrieve_sources",
        metadata={
            "model_provider": retrieval_service.embedding_service.provider_name,
            "model_name": retrieval_service.embedding_service.model_name,
        },
        inputs={"question": payload.question},
    ) as span:
        retrieval = await retrieval_service.retrieve(session, payload.question, settings.retrieval_limit, current_user.user_id)
        insufficient_information = len(retrieval.citations) == 0 or all(
            citation.relevance_score < settings.answer_min_score for citation in retrieval.citations
        )
        confidence_note = (
            "Evidence was too weak to support a reliable result."
            if insufficient_information
            else None
        )
        span.set_outputs(retrieval_count=retrieval.count, insufficient_information=insufficient_information)
        return RetrieveResponse(
            question=payload.question,
            citations=retrieval.citations,
            retrieval_count=retrieval.count,
            insufficient_information=insufficient_information,
            confidence_note=confidence_note,
        )


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_sessions(
    session: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> ChatSessionListResponse:
    result = await session.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.user_id)
        .order_by(ChatSession.updated_at.desc())
    )
    sessions = list(result.scalars())
    return ChatSessionListResponse(
        items=[
            ChatSessionSummary(
                id=item.id,
                title=item.title,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in sessions
        ]
    )


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> ChatSessionResponse:
    result = await session.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == current_user.user_id)
    )
    chat_session = result.scalar_one_or_none()
    if not chat_session:
        raise HTTPException(status_code=404, detail="Session not found.")
    await session.refresh(chat_session, attribute_names=["messages"])
    ordered_messages = sorted(
        [item for item in chat_session.messages if item.user_id == current_user.user_id],
        key=lambda item: item.created_at,
    )
    return ChatSessionResponse(
        id=chat_session.id,
        title=chat_session.title,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at,
        messages=[serialize_message(item) for item in ordered_messages],
    )


async def ensure_session(session: AsyncSession, session_id: Optional[UUID], question: str, user_id: UUID) -> ChatSession:
    if session_id:
        result = await session.execute(
            select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        raise HTTPException(status_code=404, detail="Session not found.")

    title = question[:80].strip() or "New session"
    new_session = ChatSession(title=title, user_id=user_id)
    session.add(new_session)
    await session.commit()
    await session.refresh(new_session)
    return new_session


async def get_history(session: AsyncSession, session_id: UUID, user_id: UUID) -> list[tuple[str, str]]:
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id, ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = list(result.scalars())
    return [(message.role, message.content) for message in messages]
