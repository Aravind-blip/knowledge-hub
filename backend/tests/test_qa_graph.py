from uuid import uuid4

import pytest

from app.agents.qa_graph import build_qa_graph
from app.schemas.common import SourceCitation
from app.services.generation import AnswerPayload, GenerationService
from app.services.retrieval import RetrievalResult


class DummyGenerationService(GenerationService):
    async def answer(self, question, retrieved_chunks, history):
        return AnswerPayload(
            answer=f"Answer for: {question}",
            insufficient_information=False,
            confidence_note=None,
            citations=retrieved_chunks,
        )


@pytest.mark.anyio
async def test_qa_graph_preserves_retrieval_result():
    graph = build_qa_graph(DummyGenerationService())
    citation = SourceCitation(
        chunk_id=uuid4(),
        document_id=uuid4(),
        file_name="support_policy.md",
        snippet="Password resets are completed within one business day.",
        page_number=1,
        relevance_score=0.92,
    )

    result = await graph.ainvoke(
        {
            "question": "What is the password reset turnaround time?",
            "history": [],
            "retrieval_result": RetrievalResult(citations=[citation], count=1),
            "citations": [],
            "retrieval_count": 0,
            "answer": "",
            "insufficient_information": False,
            "confidence_note": None,
        }
    )

    assert result["retrieval_count"] == 1
    assert result["citations"][0].file_name == "support_policy.md"
    assert result["answer"] == "Answer for: What is the password reset turnaround time?"
