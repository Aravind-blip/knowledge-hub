from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    detail: str
    request_id: Optional[str] = None
