from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    environment: str
    provider_mode: str
    embedding_provider: str
    auth_enabled: bool
    tracing_enabled: bool
    database_status: str
