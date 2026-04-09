import asyncio
import json

from app.schemas.common import SourceCitation
from app.services.embeddings import get_embedding_service
from app.services.generation import get_generation_service


async def main() -> None:
    embedding_service = get_embedding_service()
    generation_service = get_generation_service()

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

    print(
        json.dumps(
            {
                "embedding_provider": embedding_service.provider_name,
                "embedding_model": embedding_service.model_name,
                "embedding_dimensions": len(vector),
                "generation_provider": generation_service.provider_name,
                "generation_model": generation_service.model_name,
                "answer_preview": payload.answer[:160],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
