from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, AsyncIterator, Optional

from langsmith import Client
from langsmith.run_trees import RunTree

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
_current_span: ContextVar["TraceSpan | None"] = ContextVar("trace_span", default=None)


@dataclass
class TraceSpan:
    enabled: bool
    name: str
    run_type: str
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=time.perf_counter)
    run_tree: Optional[RunTree] = None
    token: Optional[Token] = None

    def add_metadata(self, **values: Any) -> None:
        self.metadata.update({key: value for key, value in values.items() if value is not None})

    def set_outputs(self, **values: Any) -> None:
        self.outputs.update({key: value for key, value in values.items() if value is not None})


class TraceService:
    def __init__(self) -> None:
        self.enabled = settings.langsmith_tracing
        self.client = (
            Client(
                api_key=settings.langsmith_api_key,
                api_url=settings.langsmith_endpoint,
            )
            if self.enabled
            else None
        )

    @asynccontextmanager
    async def trace(
        self,
        name: str,
        *,
        run_type: str = "chain",
        metadata: Optional[dict[str, Any]] = None,
        inputs: Optional[dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
    ) -> AsyncIterator[TraceSpan]:
        span = self._start_span(
            name=name,
            run_type=run_type,
            metadata=metadata or {},
            inputs=inputs or {},
            tags=tags or [],
        )
        try:
            yield span
        except Exception as exc:
            span.add_metadata(error_type=exc.__class__.__name__)
            self._finish_span(span, error=str(exc))
            raise
        else:
            self._finish_span(span)

    def _start_span(
        self,
        *,
        name: str,
        run_type: str,
        metadata: dict[str, Any],
        inputs: dict[str, Any],
        tags: list[str],
    ) -> TraceSpan:
        span = TraceSpan(
            enabled=self.enabled,
            name=name,
            run_type=run_type,
            metadata=dict(metadata),
            inputs=dict(inputs),
            tags=list(tags),
        )
        parent_span = _current_span.get()
        if self.enabled and self.client:
            if parent_span and parent_span.run_tree:
                span.run_tree = parent_span.run_tree.create_child(
                    name=name,
                    run_type=run_type,
                    inputs=span.inputs,
                    extra={"metadata": span.metadata},
                    tags=span.tags,
                )
            else:
                span.run_tree = RunTree(
                    name=name,
                    run_type=run_type,
                    inputs=span.inputs,
                    extra={"metadata": span.metadata},
                    tags=span.tags,
                    project_name=settings.langsmith_project,
                    ls_client=self.client,
                    start_time=datetime.now(timezone.utc),
                )
            span.run_tree.post()
        span.token = _current_span.set(span)
        return span

    def _finish_span(self, span: TraceSpan, error: Optional[str] = None) -> None:
        latency_ms = round((time.perf_counter() - span.started_at) * 1000, 2)
        span.add_metadata(latency_ms=latency_ms)
        if span.enabled and span.run_tree:
            try:
                span.run_tree.end(
                    outputs=span.outputs or None,
                    error=error,
                    metadata=span.metadata,
                    end_time=datetime.now(timezone.utc),
                )
                span.run_tree.patch()
            except Exception:
                logger.exception("LangSmith trace update failed", extra={"trace_name": span.name})
        if span.token is not None:
            _current_span.reset(span.token)


@lru_cache
def get_trace_service() -> TraceService:
    return TraceService()
