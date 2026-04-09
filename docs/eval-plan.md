# Evaluation Plan

## Current Validation

- Demo seed content is stored in [docs/demo-data](/Users/aravindbandipelli/Desktop/AravindCode-bot/docs/demo-data)
- Benchmark prompts are stored in [benchmark_questions.json](/Users/aravindbandipelli/Desktop/AravindCode-bot/docs/evaluation/benchmark_questions.json)
- The evaluation script in [eval.py](/Users/aravindbandipelli/Desktop/AravindCode-bot/backend/scripts/eval.py) checks:
  - HTTP status
  - answer preview
  - retrieval count
  - insufficient-information behavior
  - whether expected source files appear in the citations

## Manual Validation Modes

- Fallback mode
  - verify the full upload and query flow without external secrets
- OpenAI mode
  - verify embeddings and answer generation through [verify_openai_provider.py](/Users/aravindbandipelli/Desktop/AravindCode-bot/backend/scripts/verify_openai_provider.py)
- LangSmith mode
  - verify trace creation through [verify_langsmith_tracing.py](/Users/aravindbandipelli/Desktop/AravindCode-bot/backend/scripts/verify_langsmith_tracing.py)

## Future Expansion

- citation span matching
- answer completeness scoring
- latency thresholds by question type
- retrieval precision and recall against a larger benchmark set
