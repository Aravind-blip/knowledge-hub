import json
from pathlib import Path


def test_benchmark_dataset_has_expected_shape() -> None:
    path = Path(__file__).resolve().parents[2] / "docs" / "evaluation" / "organization_eval_dataset.jsonl"
    payload = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert 30 <= len(payload) <= 50
    for item in payload:
        assert item["id"]
        assert item["category"] in {"positive", "ambiguous", "negative"}
        assert item["question"]
        assert isinstance(item["expected_sources"], list)
        assert isinstance(item["grounding_terms"], list)
        assert isinstance(item["should_fallback"], bool)
