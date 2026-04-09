from uuid import uuid4

import pytest

from app.schemas.common import SourceCitation
from app.services.generation import ExtractiveGenerationService


def build_citation(score: float, snippet: str) -> SourceCitation:

    return SourceCitation(
        chunk_id=uuid4(),
        document_id=uuid4(),
        file_name="finance_controls.txt",
        snippet=snippet,
        page_number=1,
        relevance_score=score,
    )


@pytest.mark.anyio
async def test_extractive_generation_returns_insufficient_information_for_weak_evidence():
    service = ExtractiveGenerationService()
    weak_citation = build_citation(0.23, "Late shipment escalation steps for carrier delays.")

    result = await service.answer(
        "What file formats are accepted for invoices?",
        [weak_citation],
        [],
    )

    assert result.insufficient_information is True
    assert result.answer == "Not enough information found in indexed documents."
    assert result.confidence_note == "Evidence was too weak to support a reliable result."


@pytest.mark.anyio
async def test_extractive_generation_uses_strong_evidence():
    service = ExtractiveGenerationService()
    strong_citation = build_citation(
        0.82,
        "Invoices are accepted in PDF, CSV, or EDI 810 format.",
    )

    result = await service.answer(
        "What file formats are accepted for invoices?",
        [strong_citation],
        [],
    )

    assert result.insufficient_information is False
    assert "Invoices are accepted in PDF, CSV, or EDI 810 format." in result.answer
