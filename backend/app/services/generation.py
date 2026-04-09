import logging
from abc import ABC, abstractmethod
from typing import Optional

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.config import get_settings
from app.schemas.common import SourceCitation
from app.services.observability.tracer import get_trace_service

settings = get_settings()
logger = logging.getLogger(__name__)


class AnswerPayload(BaseModel):
    answer: str
    insufficient_information: bool
    confidence_note: Optional[str] = None
    citations: list[SourceCitation]


class GenerationService(ABC):
    provider_name: str
    model_name: str

    @abstractmethod
    async def answer(
        self,
        question: str,
        retrieved_chunks: list[SourceCitation],
        history: list[tuple[str, str]],
    ) -> AnswerPayload:
        raise NotImplementedError


class OpenAIGenerationService(GenerationService):
    def __init__(self) -> None:
        self.provider_name = "openai"
        self.model_name = settings.openai_chat_model
        self.client = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.openai_chat_model,
            temperature=0,
        )
        self.structured_client = self.client.with_structured_output(AnswerPayload)

    async def answer(
        self,
        question: str,
        retrieved_chunks: list[SourceCitation],
        history: list[tuple[str, str]],
    ) -> AnswerPayload:
        trace_service = get_trace_service()
        async with trace_service.trace(
            "generate_answer",
            run_type="llm",
            metadata={
                "model_provider": self.provider_name,
                "model_name": self.model_name,
                "retrieval_count": len(retrieved_chunks),
            },
            inputs={"question": question},
        ) as span:
            if not retrieved_chunks:
                payload = AnswerPayload(
                    answer="Not enough information found in indexed documents.",
                    insufficient_information=True,
                    confidence_note="Evidence was too weak to support a reliable result.",
                    citations=[],
                )
                span.set_outputs(insufficient_information=True, citation_count=0)
                return payload

            history_lines = "\n".join([f"{role}: {content}" for role, content in history[-6:]])
            sources = "\n\n".join(
                [
                    f"Source {index + 1}\n"
                    f"File: {chunk.file_name}\n"
                    f"Page: {chunk.page_number}\n"
                    f"Snippet: {chunk.snippet}\n"
                    f"Score: {chunk.relevance_score:.4f}"
                    for index, chunk in enumerate(retrieved_chunks)
                ]
            )
            prompt = (
                "You answer questions using only the provided sources.\n"
                "Rules:\n"
                "- If the evidence is weak or missing, say 'Not enough information found in indexed documents.'\n"
                "- Do not invent policies, numbers, or procedures.\n"
                "- Keep the answer concise and professional.\n"
                "- When evidence is weak, set confidence_note to 'Evidence was too weak to support a reliable result.'\n"
                "- Return only citations that support the answer.\n\n"
                f"Conversation context:\n{history_lines or 'No previous context.'}\n\n"
                f"Question:\n{question}\n\n"
                f"Sources:\n{sources}"
            )
            payload = await self.structured_client.ainvoke(prompt)
            span.set_outputs(
                insufficient_information=payload.insufficient_information,
                citation_count=len(payload.citations),
            )
            return payload


class GroqGenerationService(GenerationService):
    def __init__(self) -> None:
        self.provider_name = "groq"
        self.model_name = settings.groq_chat_model
        self.client = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_chat_model,
            temperature=0,
        )
        self.structured_client = self.client.with_structured_output(AnswerPayload)

    async def answer(
        self,
        question: str,
        retrieved_chunks: list[SourceCitation],
        history: list[tuple[str, str]],
    ) -> AnswerPayload:
        trace_service = get_trace_service()
        async with trace_service.trace(
            "generate_answer",
            run_type="llm",
            metadata={
                "model_provider": self.provider_name,
                "model_name": self.model_name,
                "retrieval_count": len(retrieved_chunks),
            },
            inputs={"question": question},
        ) as span:
            if not retrieved_chunks:
                payload = AnswerPayload(
                    answer="Not enough information found in indexed documents.",
                    insufficient_information=True,
                    confidence_note="Evidence was too weak to support a reliable result.",
                    citations=[],
                )
                span.set_outputs(insufficient_information=True, citation_count=0)
                return payload

            history_lines = "\n".join([f"{role}: {content}" for role, content in history[-6:]])
            sources = "\n\n".join(
                [
                    f"Source {index + 1}\n"
                    f"File: {chunk.file_name}\n"
                    f"Page: {chunk.page_number}\n"
                    f"Snippet: {chunk.snippet}\n"
                    f"Score: {chunk.relevance_score:.4f}"
                    for index, chunk in enumerate(retrieved_chunks)
                ]
            )
            prompt = (
                "You answer questions using only the provided sources.\n"
                "Rules:\n"
                "- If the evidence is weak or missing, say 'Not enough information found in indexed documents.'\n"
                "- Do not invent policies, numbers, or procedures.\n"
                "- Keep the answer concise and professional.\n"
                "- When evidence is weak, set confidence_note to 'Evidence was too weak to support a reliable result.'\n"
                "- Return only citations that support the answer.\n\n"
                f"Conversation context:\n{history_lines or 'No previous context.'}\n\n"
                f"Question:\n{question}\n\n"
                f"Sources:\n{sources}"
            )
            payload = await self.structured_client.ainvoke(prompt)
            span.set_outputs(
                insufficient_information=payload.insufficient_information,
                citation_count=len(payload.citations),
            )
            return payload


class ExtractiveGenerationService(GenerationService):
    provider_name = "fallback"
    model_name = "extractive-summary"

    async def answer(
        self,
        question: str,
        retrieved_chunks: list[SourceCitation],
        history: list[tuple[str, str]],
    ) -> AnswerPayload:
        trace_service = get_trace_service()
        async with trace_service.trace(
            "generate_answer",
            run_type="tool",
            metadata={
                "model_provider": self.provider_name,
                "model_name": self.model_name,
                "retrieval_count": len(retrieved_chunks),
            },
            inputs={"question": question},
        ) as span:
            if not retrieved_chunks:
                payload = AnswerPayload(
                    answer="Not enough information found in indexed documents.",
                    insufficient_information=True,
                    confidence_note="Evidence was too weak to support a reliable result.",
                    citations=[],
                )
                span.set_outputs(insufficient_information=True, citation_count=0)
                return payload

            strong_chunks = [chunk for chunk in retrieved_chunks if chunk.relevance_score >= settings.answer_min_score]
            if not strong_chunks:
                payload = AnswerPayload(
                    answer="Not enough information found in indexed documents.",
                    insufficient_information=True,
                    confidence_note="Evidence was too weak to support a reliable result.",
                    citations=retrieved_chunks[:2],
                )
                span.set_outputs(insufficient_information=True, citation_count=len(payload.citations))
                return payload

            summary_lines = [chunk.snippet.strip().replace("\n", " ") for chunk in strong_chunks[:3]]
            answer = " ".join(summary_lines)
            if len(answer) > 900:
                answer = answer[:900].rsplit(" ", 1)[0] + "..."
            payload = AnswerPayload(
                answer=answer,
                insufficient_information=False,
                confidence_note=None,
                citations=strong_chunks[:3],
            )
            span.set_outputs(insufficient_information=False, citation_count=len(payload.citations))
            return payload


def get_generation_service() -> GenerationService:
    if settings.resolved_generation_provider == "groq":
        logger.info(
            "Generation provider selected",
            extra={"provider_mode": settings.resolved_generation_provider, "model_provider": "groq", "model_name": settings.groq_chat_model},
        )
        return GroqGenerationService()
    if settings.resolved_generation_provider == "openai":
        logger.info(
            "Generation provider selected",
            extra={"provider_mode": settings.resolved_generation_provider, "model_provider": "openai", "model_name": settings.openai_chat_model},
        )
        return OpenAIGenerationService()
    if settings.allow_fallback_models:
        logger.info(
            "Generation provider selected",
            extra={"provider_mode": settings.resolved_generation_provider, "model_provider": "fallback", "model_name": "extractive-summary"},
        )
        return ExtractiveGenerationService()
    raise RuntimeError("Generation provider is not configured.")
