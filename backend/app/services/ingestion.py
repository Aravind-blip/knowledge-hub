import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentChunk, IngestionJob
from app.services.embeddings import EmbeddingService
from app.services.observability.tracer import get_trace_service
from app.services.parsers.document_parser import DocumentParser
from app.utils.text import build_text_splitter, compact_metadata, estimate_token_count

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self, parser: DocumentParser, embedding_service: EmbeddingService) -> None:
        self.parser = parser
        self.embedding_service = embedding_service
        self.splitter = build_text_splitter()

    async def ingest_document(
        self,
        session: AsyncSession,
        document_id: UUID,
        file_path: Path,
        content_type: str,
    ) -> Document:
        document = await session.get(Document, document_id)
        if not document:
            raise ValueError("Document not found")

        job = IngestionJob(document_id=document.id, status="processing")
        session.add(job)
        await session.flush()

        trace_service = get_trace_service()
        async with trace_service.trace(
            "ingest_document",
            metadata={
                "document_id": str(document.id),
                "content_type": content_type,
                "model_provider": self.embedding_service.provider_name,
                "model_name": self.embedding_service.model_name,
            },
            inputs={"file_path": str(file_path)},
        ) as span:
            try:
                parsed_pages = await self.parser.parse(file_path, content_type)
                chunk_payloads: list[dict] = []
                for page in parsed_pages:
                    page_text = page["text"].strip()
                    if not page_text:
                        continue
                    chunks = self.splitter.split_text(page_text)
                    for index, chunk in enumerate(chunks):
                        chunk_payloads.append(
                            {
                                "content": chunk,
                                "page_number": page.get("page_number"),
                                "token_count": estimate_token_count(chunk),
                                "metadata_json": compact_metadata({"page_number": page.get("page_number"), "part_index": index}),
                            }
                        )

                if not chunk_payloads:
                    raise ValueError("No extractable text was found in the uploaded document.")

                vectors = await self.embedding_service.embed_documents([item["content"] for item in chunk_payloads])

                if len(chunk_payloads) != len(vectors):
                    raise ValueError("Embedding result count did not match chunk count.")

                for index, (payload, vector) in enumerate(zip(chunk_payloads, vectors)):
                    session.add(
                        DocumentChunk(
                            document_id=document.id,
                            chunk_index=index,
                            content=payload["content"],
                            page_number=payload["page_number"],
                            token_count=payload["token_count"],
                            embedding=vector,
                            metadata_json=payload["metadata_json"],
                        )
                    )

                document.status = "indexed"
                document.metadata_json = compact_metadata(
                    {
                        "chunk_count": len(chunk_payloads),
                        "content_type": content_type,
                    }
                )
                job.status = "completed"
                job.metrics_json = {"chunk_count": len(chunk_payloads)}
                await session.commit()
                await session.refresh(document)
                span.set_outputs(chunk_count=len(chunk_payloads), status=document.status)
                logger.info("Document indexed", extra={"document_id": str(document.id), "chunk_count": len(chunk_payloads)})
                return document
            except Exception as exc:
                document.status = "failed"
                job.status = "failed"
                job.error_message = str(exc)
                await session.commit()
                logger.exception("Document ingestion failed", extra={"document_id": str(document.id)})
                raise

    async def list_documents(self, session: AsyncSession) -> list[Document]:
        result = await session.execute(select(Document).order_by(Document.created_at.desc()))
        return list(result.scalars())
