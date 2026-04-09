import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import ensure_schema_ready, get_db_session
from app.models import Document
from app.schemas.documents import DocumentListResponse, DocumentResponse
from app.services.embeddings import get_embedding_service
from app.services.ingestion import IngestionService
from app.services.parsers.document_parser import DocumentParser

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()
logger = logging.getLogger(__name__)


def serialize_document(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        file_name=document.file_name,
        original_name=document.original_name,
        status=document.status,
        content_type=document.content_type,
        file_size=document.file_size,
        created_at=document.created_at,
        metadata=document.metadata_json,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(session: AsyncSession = Depends(get_db_session)) -> DocumentListResponse:
    service = IngestionService(DocumentParser(), get_embedding_service())
    logger.info("Listing documents", extra={"path": "/api/documents", "method": "GET"})
    try:
        documents = await service.list_documents(session)
    except (OperationalError, ProgrammingError):
        logger.exception("Document listing failed; verifying database schema")
        await ensure_schema_ready()
        documents = await service.list_documents(session)

    if not documents:
        logger.info("No documents indexed yet", extra={"path": "/api/documents", "method": "GET"})
        return DocumentListResponse(items=[])

    payload = [serialize_document(item) for item in documents]
    logger.info(
        "Documents returned",
        extra={
            "path": "/api/documents",
            "method": "GET",
            "retrieved_count": len(payload),
        },
    )
    return DocumentListResponse(items=payload)


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    if file.content_type not in DocumentParser.supported_types:
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload a PDF, TXT, or Markdown file.")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(contents) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.max_upload_size_mb} MB limit.")

    document_id = uuid.uuid4()
    stored_name = f"{document_id}{Path(file.filename or 'upload').suffix.lower()}"
    target_path = settings.upload_dir / stored_name
    target_path.write_bytes(contents)

    document = Document(
        id=document_id,
        file_name=stored_name,
        original_name=file.filename or stored_name,
        content_type=file.content_type or "application/octet-stream",
        file_size=len(contents),
        status="processing",
        metadata_json={},
    )
    session.add(document)
    await session.commit()
    logger.info(
        "Document upload accepted",
        extra={"document_id": str(document.id), "path": "/api/documents/upload", "method": "POST"},
    )

    service = IngestionService(DocumentParser(), get_embedding_service())
    indexed_document = await service.ingest_document(session, document.id, target_path, document.content_type)
    return serialize_document(indexed_document)
