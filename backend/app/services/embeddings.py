import logging
from abc import ABC, abstractmethod

from langchain_openai import OpenAIEmbeddings

from app.core.config import get_settings
from app.services.observability.tracer import get_trace_service
from app.utils.text import stable_hash_embedding

settings = get_settings()
logger = logging.getLogger(__name__)


class EmbeddingService(ABC):
    provider_name: str
    model_name: str

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError


class OpenAIEmbeddingService(EmbeddingService):
    def __init__(self) -> None:
        self.provider_name = "openai"
        self.model_name = settings.openai_embedding_model
        self.client = OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            dimensions=settings.embedding_dimension,
        )

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        trace_service = get_trace_service()
        async with trace_service.trace(
            "embed_documents",
            run_type="embedding",
            metadata={"model_provider": self.provider_name, "model_name": self.model_name, "text_count": len(texts)},
        ) as span:
            vectors = await self.client.aembed_documents(texts)
            span.set_outputs(vector_count=len(vectors))
            return vectors

    async def embed_query(self, text: str) -> list[float]:
        trace_service = get_trace_service()
        async with trace_service.trace(
            "embed_query",
            run_type="embedding",
            metadata={"model_provider": self.provider_name, "model_name": self.model_name},
        ) as span:
            vector = await self.client.aembed_query(text)
            span.set_outputs(vector_dimensions=len(vector))
            return vector


class HashEmbeddingService(EmbeddingService):
    provider_name = "fallback"
    model_name = "stable-hash"

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [stable_hash_embedding(text, settings.embedding_dimension) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return stable_hash_embedding(text, settings.embedding_dimension)


def get_embedding_service() -> EmbeddingService:
    if settings.resolved_embedding_provider == "openai":
        logger.info(
            "Embedding provider selected",
            extra={"provider_mode": settings.resolved_embedding_provider, "model_provider": "openai", "model_name": settings.openai_embedding_model},
        )
        return OpenAIEmbeddingService()
    if settings.allow_fallback_models:
        logger.info(
            "Embedding provider selected",
            extra={"provider_mode": settings.resolved_embedding_provider, "model_provider": "fallback", "model_name": "stable-hash"},
        )
        return HashEmbeddingService()
    raise RuntimeError("Embedding provider is not configured.")
