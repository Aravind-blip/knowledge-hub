from __future__ import annotations

import argparse
import asyncio
import json
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx

DEFAULT_DATASET = Path(__file__).resolve().parents[2] / "docs" / "evaluation" / "organization_eval_dataset.jsonl"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "artifacts" / "evals" / "latest.json"
FALLBACK_ANSWER = "Not enough information found in indexed documents."


@dataclass
class EvalCase:
    id: str
    category: str
    question: str
    expected_sources: list[str]
    grounding_terms: list[str]
    should_fallback: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run retrieval and answer evaluations against a Knowledge Hub deployment.")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="Path to a JSONL evaluation dataset.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to write the JSON evaluation artifact.")
    parser.add_argument("--bearer-token", default=None, help="Optional bearer token for protected environments.")
    return parser.parse_args()


def load_dataset(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        cases.append(
            EvalCase(
                id=payload["id"],
                category=payload["category"],
                question=payload["question"],
                expected_sources=payload["expected_sources"],
                grounding_terms=payload["grounding_terms"],
                should_fallback=payload["should_fallback"],
            )
        )
    return cases


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def build_headers(token: str | None) -> dict[str, str]:
    if not token:
        return {"Content-Type": "application/json"}
    return {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}


async def call_json(
    client: httpx.AsyncClient,
    path: str,
    payload: dict[str, Any],
    token: str | None,
) -> tuple[dict[str, Any], float, int]:
    started = perf_counter()
    response = await client.post(path, json=payload, headers=build_headers(token))
    latency_ms = (perf_counter() - started) * 1000
    body = response.json()
    return body, latency_ms, response.status_code


def first_expected_rank(cited_files: list[str], expected_sources: list[str]) -> int | None:
    for index, file_name in enumerate(cited_files, start=1):
        if file_name in expected_sources:
            return index
    return None


async def run_evals(base_url: str, dataset_path: Path, output_path: Path, token: str | None) -> dict[str, Any]:
    cases = load_dataset(dataset_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=60.0) as client:
        case_results: list[dict[str, Any]] = []
        retrieval_latencies: list[float] = []
        answer_latencies: list[float] = []

        for case in cases:
            retrieve_payload, retrieval_latency_ms, retrieve_status = await call_json(
                client, "/api/chat/retrieve", {"question": case.question}, token
            )
            ask_payload, answer_latency_ms, ask_status = await call_json(
                client, "/api/chat/ask", {"question": case.question, "session_id": None}, token
            )

            retrieval_latencies.append(retrieval_latency_ms)
            answer_latencies.append(answer_latency_ms)

            retrieval_citations = retrieve_payload.get("citations", [])
            answer_citations = ask_payload.get("citations", [])
            retrieval_files = [item.get("file_name") for item in retrieval_citations]
            answer_files = [item.get("file_name") for item in answer_citations]
            answer_text = (ask_payload.get("answer") or "").lower()
            grounding_hits = [term for term in case.grounding_terms if term.lower() in answer_text]
            rank = first_expected_rank(retrieval_files, case.expected_sources)
            matched_top_3 = rank is not None and rank <= 3
            matched_top_5 = rank is not None and rank <= 5
            answer_expected_source = any(file_name in case.expected_sources for file_name in answer_files)
            grounded_answer = (not case.should_fallback) and (not ask_payload.get("insufficient_information", False)) and (
                answer_expected_source and (not case.grounding_terms or bool(grounding_hits))
            )
            fell_back = bool(ask_payload.get("insufficient_information")) or ask_payload.get("answer") == FALLBACK_ANSWER

            case_results.append(
                {
                    "id": case.id,
                    "category": case.category,
                    "question": case.question,
                    "expected_sources": case.expected_sources,
                    "should_fallback": case.should_fallback,
                    "retrieve_status_code": retrieve_status,
                    "ask_status_code": ask_status,
                    "retrieval_latency_ms": round(retrieval_latency_ms, 2),
                    "answer_latency_ms": round(answer_latency_ms, 2),
                    "retrieval_count": retrieve_payload.get("retrieval_count", 0),
                    "answer_retrieval_count": ask_payload.get("retrieval_count", 0),
                    "retrieval_files": retrieval_files,
                    "answer_files": answer_files,
                    "matched_top_3": matched_top_3,
                    "matched_top_5": matched_top_5,
                    "expected_rank": rank,
                    "grounded_answer": grounded_answer,
                    "fell_back": fell_back,
                    "grounding_hits": grounding_hits,
                    "answer_preview": (ask_payload.get("answer") or "")[:220],
                }
            )

    positive_cases = [item for item in case_results if not item["should_fallback"]]
    fallback_cases = [item for item in case_results if item["should_fallback"]]
    reciprocal_ranks = [1 / item["expected_rank"] for item in positive_cases if item["expected_rank"]]
    metrics = {
        "dataset_size": len(case_results),
        "positive_case_count": len(positive_cases),
        "fallback_case_count": len(fallback_cases),
        "top_3_retrieval_accuracy": _ratio(sum(1 for item in positive_cases if item["matched_top_3"]), len(positive_cases)),
        "top_5_retrieval_accuracy": _ratio(sum(1 for item in positive_cases if item["matched_top_5"]), len(positive_cases)),
        "hit_rate": _ratio(sum(1 for item in positive_cases if item["expected_rank"]), len(positive_cases)),
        "mean_reciprocal_rank": round(statistics.fmean(reciprocal_ranks), 4) if reciprocal_ranks else 0.0,
        "grounded_answer_rate": _ratio(sum(1 for item in positive_cases if item["grounded_answer"]), len(positive_cases)),
        "citation_coverage_rate": _ratio(
            sum(1 for item in positive_cases if any(file_name in item["expected_sources"] for file_name in item["answer_files"])),
            len(positive_cases),
        ),
        "low_confidence_fallback_precision": _ratio(sum(1 for item in fallback_cases if item["fell_back"]), len(fallback_cases)),
        "hallucination_rate": _ratio(sum(1 for item in fallback_cases if not item["fell_back"]), len(fallback_cases)),
        "average_retrieval_latency_ms": round(statistics.fmean(retrieval_latencies), 2) if retrieval_latencies else 0.0,
        "p95_retrieval_latency_ms": round(percentile(retrieval_latencies, 0.95), 2),
        "average_answer_latency_ms": round(statistics.fmean(answer_latencies), 2) if answer_latencies else 0.0,
        "p95_answer_latency_ms": round(percentile(answer_latencies, 0.95), 2),
    }
    artifact = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "dataset_path": str(dataset_path),
        "metrics": metrics,
        "cases": case_results,
    }
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    return artifact


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def print_summary(artifact: dict[str, Any]) -> None:
    metrics = artifact["metrics"]
    lines = [
        "Knowledge Hub evaluation summary",
        f"- Dataset size: {metrics['dataset_size']}",
        f"- Top-3 retrieval accuracy: {metrics['top_3_retrieval_accuracy'] * 100:.1f}%",
        f"- Top-5 retrieval accuracy: {metrics['top_5_retrieval_accuracy'] * 100:.1f}%",
        f"- Mean reciprocal rank: {metrics['mean_reciprocal_rank']:.3f}",
        f"- Grounded answer rate: {metrics['grounded_answer_rate'] * 100:.1f}%",
        f"- Citation coverage rate: {metrics['citation_coverage_rate'] * 100:.1f}%",
        f"- Fallback precision: {metrics['low_confidence_fallback_precision'] * 100:.1f}%",
        f"- Hallucination rate: {metrics['hallucination_rate'] * 100:.1f}%",
        f"- Average retrieval latency: {metrics['average_retrieval_latency_ms']:.1f} ms",
        f"- p95 retrieval latency: {metrics['p95_retrieval_latency_ms']:.1f} ms",
        f"- Average answer latency: {metrics['average_answer_latency_ms']:.1f} ms",
        f"- p95 answer latency: {metrics['p95_answer_latency_ms']:.1f} ms",
    ]
    print("\n".join(lines))


async def main() -> None:
    args = parse_args()
    artifact = await run_evals(
        base_url=args.base_url,
        dataset_path=Path(args.dataset),
        output_path=Path(args.output),
        token=args.bearer_token,
    )
    print_summary(artifact)


if __name__ == "__main__":
    asyncio.run(main())
