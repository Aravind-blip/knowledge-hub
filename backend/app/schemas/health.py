from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    environment: str
    provider_mode: str
    embedding_provider: str
    tracing_enabled: bool
    database_status: str
