# Evaluation Plan

## Current Validation

- Demo seed content is stored in [docs/demo-data](/Users/aravindbandipelli/Desktop/AravindCode-bot/docs/demo-data)
- The labeled evaluation set is stored in [organization_eval_dataset.jsonl](/Users/aravindbandipelli/Desktop/AravindCode-bot/docs/evaluation/organization_eval_dataset.jsonl)
- The evaluation runner is [run_evals.py](/Users/aravindbandipelli/Desktop/AravindCode-bot/backend/scripts/run_evals.py)
- The evaluation artifact is written to [artifacts/evals/latest.json](/Users/aravindbandipelli/Desktop/AravindCode-bot/artifacts/evals/.gitkeep) by default

## Reported Metrics

- Top-3 retrieval accuracy
- Top-5 retrieval accuracy
- Hit rate
- Mean reciprocal rank
- Grounded answer rate
- Citation coverage rate
- Low-confidence fallback precision
- Hallucination rate
- Average and p95 retrieval latency
- Average and p95 answer latency

## Run Commands

Local backend:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
source .venv/bin/activate
python scripts/run_evals.py --base-url http://localhost:8000 --output ../artifacts/evals/latest.json
```

Protected backend:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
source .venv/bin/activate
python scripts/run_evals.py \
  --base-url https://YOUR_BACKEND_HOST \
  --bearer-token YOUR_SUPABASE_ACCESS_TOKEN \
  --output ../artifacts/evals/latest.json
```

## Dataset Shape

Each line in the JSONL dataset includes:

- `id`
- `category`
- `question`
- `expected_sources`
- `grounding_terms`
- `should_fallback`

## Future Expansion

- organization-specific eval fixtures
- citation span matching
- answer completeness scoring
- latency thresholds by question type
- retrieval precision and recall against a larger benchmark set
