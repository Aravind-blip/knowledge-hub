import json
from pathlib import Path


def test_benchmark_dataset_has_expected_shape() -> None:
    path = Path(__file__).resolve().parents[2] / "docs" / "evaluation" / "benchmark_questions.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert len(payload) == 10
    for item in payload:
        assert item["question"]
        assert item["expected_sources"]
        assert item["grounding_terms"]

