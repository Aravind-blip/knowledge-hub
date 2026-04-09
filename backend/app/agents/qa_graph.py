from typing import Optional, TypedDict

from langgraph.graph import END, StateGraph

from app.schemas.common import SourceCitation
from app.services.generation import GenerationService
from app.services.retrieval import RetrievalResult


class GraphState(TypedDict):
    question: str
    history: list[tuple[str, str]]
    retrieval_result: RetrievalResult
    citations: list[SourceCitation]
    retrieval_count: int
    answer: str
    insufficient_information: bool
    confidence_note: Optional[str]


def build_qa_graph(generation_service: GenerationService):
    async def run_retrieval(state: GraphState) -> GraphState:
        result = state["retrieval_result"]
        return {**state, "citations": result.citations, "retrieval_count": result.count}

    async def run_generation(state: GraphState) -> GraphState:
        payload = await generation_service.answer(state["question"], state["citations"], state["history"])
        return {
            **state,
            "answer": payload.answer,
            "insufficient_information": payload.insufficient_information,
            "confidence_note": payload.confidence_note,
            "citations": payload.citations,
        }

    graph = StateGraph(GraphState)
    graph.add_node("run_retrieval", run_retrieval)
    graph.add_node("run_generation", run_generation)
    graph.set_entry_point("run_retrieval")
    graph.add_edge("run_retrieval", "run_generation")
    graph.add_edge("run_generation", END)
    return graph.compile()
