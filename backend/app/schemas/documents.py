from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: UUID
    file_name: str
    original_name: str
    status: str
    content_type: str
    file_size: int
    created_at: datetime
    metadata: dict


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]

