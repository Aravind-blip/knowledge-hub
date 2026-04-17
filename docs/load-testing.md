# Load Testing

Knowledge Hub uses k6 for reusable API performance testing.

## Covered Flows

- `GET /api/documents`
- `POST /api/chat/ask`
- optional `POST /api/documents/upload`

The main script lives at [tests/load/knowledge_hub.js](/Users/aravindbandipelli/Desktop/AravindCode-bot/tests/load/knowledge_hub.js).

## Metrics

- p50 and p95 query latency
- p50 and p95 document-list latency
- p50 and p95 ingestion latency
- error rate
- throughput
- ingestion success rate

Artifacts are written to [artifacts/load/latest.json](/Users/aravindbandipelli/Desktop/AravindCode-bot/artifacts/load/.gitkeep).

## Commands

Unauthenticated local fallback mode:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot
k6 run -e BASE_URL=http://localhost:8000 tests/load/knowledge_hub.js
```

Authenticated environment:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot
k6 run \
  -e BASE_URL=https://YOUR_BACKEND_HOST \
  -e K6_BEARER_TOKEN=YOUR_SUPABASE_ACCESS_TOKEN \
  tests/load/knowledge_hub.js
```

Optional upload/index scenario:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot
k6 run \
  -e BASE_URL=http://localhost:8000 \
  -e ENABLE_UPLOAD=true \
  tests/load/knowledge_hub.js
```

## Concurrency Coverage

The default scenarios exercise:

- 5 concurrent users on the ask/search endpoint
- 10 concurrent users on the ask/search endpoint
- 5 concurrent users on document listing

If upload testing is enabled, the script also runs a small shared-iteration ingestion scenario.
