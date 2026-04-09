import json
import logging
from datetime import datetime, timezone

from app.core.request_context import get_request_id


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None) or get_request_id()
        if request_id:
            payload["request_id"] = request_id
        for key in (
            "request_id",
            "document_id",
            "session_id",
            "latency_ms",
            "retrieved_count",
            "chunk_count",
            "provider_mode",
            "generation_provider",
            "embedding_provider",
            "model_provider",
            "model_name",
            "tracing_enabled",
            "database_status",
            "environment",
            "database_url_masked",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        for key in ("path", "method", "status_code"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.handlers = [handler]
