import os

import pytest

from app.schemas.common import SourceCitation
from app.services.embeddings import OpenAIEmbeddingService
from app.services.generation import OpenAIGenerationService


@pytest.mark.anyio
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY is not configured.")
async def test_openai_services_are_callable() -> None:
    embedding_service = OpenAIEmbeddingService()
    generation_service = OpenAIGenerationService()

    vector = await embedding_service.embed_query("What is the password reset turnaround time?")
    payload = await generation_service.answer(
        "What is the password reset turnaround time?",
        [
            SourceCitation(
                chunk_id="00000000-0000-0000-0000-000000000001",
                document_id="00000000-0000-0000-0000-000000000002",
                file_name="support_policy.md",
                snippet="Password reset requests are completed within one business day.",
                page_number=1,
                relevance_score=0.91,
            )
        ],
        [],
    )

    assert len(vector) > 0
    assert payload.answer
