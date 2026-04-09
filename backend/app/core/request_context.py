from contextvars import ContextVar
from typing import Optional

request_id_context: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_request_id() -> Optional[str]:
    return request_id_context.get()


def set_request_id(request_id: Optional[str]) -> None:
    request_id_context.set(request_id)
