import asyncio
import json
from pathlib import Path

import httpx

BENCHMARKS_PATH = Path(__file__).resolve().parents[2] / "docs" / "evaluation" / "benchmark_questions.json"


async def main() -> None:
    benchmarks = json.loads(BENCHMARKS_PATH.read_text(encoding="utf-8"))
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        results: list[dict] = []
        for benchmark in benchmarks:
            response = await client.post("/api/chat/ask", json={"question": benchmark["question"]})
            payload = response.json()
            cited_files = [item["file_name"] for item in payload.get("citations", [])]
            results.append(
                {
                    "question": benchmark["question"],
                    "status_code": response.status_code,
                    "answer_preview": payload.get("answer", "")[:160],
                    "retrieval_count": payload.get("retrieval_count", 0),
                    "insufficient_information": payload.get("insufficient_information"),
                    "expected_sources": benchmark["expected_sources"],
                    "grounding_terms": benchmark["grounding_terms"],
                    "cited_files": cited_files,
                    "matched_expected_source": any(file_name in cited_files for file_name in benchmark["expected_sources"]),
                }
            )
        print(json.dumps({"results": results}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
