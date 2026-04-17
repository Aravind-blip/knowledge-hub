from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import Document, DocumentChunk
from app.schemas.common import SourceCitation
from app.services.embeddings import EmbeddingService
from app.services.observability.tracer import get_trace_service
from app.utils.text import keyword_overlap

settings = get_settings()


@dataclass
class RetrievalResult:
    citations: list[SourceCitation]
    count: int


class RetrievalService:
    def __init__(self, embedding_service: EmbeddingService) -> None:
        self.embedding_service = embedding_service

    async def retrieve(
        self,
        session: AsyncSession,
        query: str,
        limit: int,
        organization_id: UUID,
        document_ids: Optional[list[UUID]] = None,
    ) -> RetrievalResult:
        trace_service = get_trace_service()
        async with trace_service.trace(
            "retrieve_documents",
            run_type="retriever",
            metadata={
                "model_provider": self.embedding_service.provider_name,
                "model_name": self.embedding_service.model_name,
                "limit": limit,
            },
            inputs={"query": query, "document_id_count": len(document_ids or [])},
        ) as span:
            query_embedding = await self.embedding_service.embed_query(query)
            distance = DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
            statement: Select[tuple[DocumentChunk, Document]] = (
                select(DocumentChunk, Document, distance)
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(
                    Document.status == "indexed",
                    Document.organization_id == organization_id,
                    DocumentChunk.organization_id == organization_id,
                )
                .order_by(distance)
                .limit(limit)
            )
            if document_ids:
                statement = statement.where(Document.id.in_(document_ids))
            rows = (await session.execute(statement)).all()
            citations: list[SourceCitation] = []
            for chunk, document, chunk_distance in rows:
                vector_score = max(0.0, 1.0 - float(chunk_distance))
                overlap_count = keyword_overlap(query, chunk.content)
                overlap_ratio = min(1.0, overlap_count / 3.0)
                score = round((vector_score * 0.45) + (overlap_ratio * 0.55), 4)
                if overlap_count < settings.retrieval_min_term_overlap or score < settings.retrieval_min_score:
                    continue
                citations.append(
                    SourceCitation(
                        chunk_id=chunk.id,
                        document_id=document.id,
                        file_name=document.original_name,
                        snippet=chunk.content[:500],
                        page_number=chunk.page_number,
                        relevance_score=score,
                    )
                )
            citations.sort(key=lambda item: item.relevance_score, reverse=True)
            span.set_outputs(retrieval_count=len(citations))
            return RetrievalResult(citations=citations, count=len(citations))
