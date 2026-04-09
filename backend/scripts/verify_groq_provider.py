import asyncio
import json
from uuid import UUID

from app.schemas.common import SourceCitation
from app.services.generation import GroqGenerationService


async def main() -> None:
    generation_service = GroqGenerationService()
    payload = await generation_service.answer(
        "What is the password reset turnaround time?",
        [
            SourceCitation(
                chunk_id=UUID("00000000-0000-0000-0000-000000000001"),
                document_id=UUID("00000000-0000-0000-0000-000000000002"),
                file_name="support_policy.md",
                snippet="Password reset requests are completed within one business day.",
                page_number=1,
                relevance_score=0.91,
            )
        ],
        [],
    )

    print(
        json.dumps(
            {
                "generation_provider": generation_service.provider_name,
                "generation_model": generation_service.model_name,
                "answer_preview": payload.answer[:160],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
