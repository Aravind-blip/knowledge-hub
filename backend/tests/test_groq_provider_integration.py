import os

import pytest

from app.schemas.common import SourceCitation
from app.services.generation import GroqGenerationService


@pytest.mark.anyio
@pytest.mark.skipif(not os.getenv("GROQ_API_KEY"), reason="GROQ_API_KEY is not configured.")
async def test_groq_generation_service_is_callable() -> None:
    generation_service = GroqGenerationService()

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

    assert payload.answer
