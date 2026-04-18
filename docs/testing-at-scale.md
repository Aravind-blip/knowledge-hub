# Automated Functional, Bulk Upload, Eval, and Load Testing

Knowledge Hub supports four complementary testing workflows:

- bulk upload automation for 10, 50, and 100 document batches
- Playwright browser tests for auth, organization sharing, and isolation
- retrieval evaluation against a labeled dataset
- k6 load testing for login, documents, ask/search, and optional upload

## Required Environment

Start the backend and frontend before running Playwright, bulk upload, eval, or most load tests.

Backend:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
set -a && source .env && set +a
./.venv/bin/alembic -c alembic.ini upgrade head
./scripts/start_backend.sh
```

Frontend:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/frontend
set -a && source .env.local && set +a
npm run dev:local
```

Local URLs:

- frontend: [http://127.0.0.1:3000/login](http://127.0.0.1:3000/login)
- backend: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

## Bulk Upload Automation

The bulk upload runner signs in a real Supabase user, generates a realistic document batch from the demo corpus, uploads files into that user's organization, and reports upload plus indexing outcomes.

Files:

- [backend/scripts/bulk_upload.py](/Users/aravindbandipelli/Desktop/AravindCode-bot/backend/scripts/bulk_upload.py)
- [backend/scripts/test_harness.py](/Users/aravindbandipelli/Desktop/AravindCode-bot/backend/scripts/test_harness.py)

Examples:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
source .venv/bin/activate
python scripts/bulk_upload.py \
  --base-url http://localhost:8000 \
  --email YOUR_TEST_USER_EMAIL \
  --password YOUR_TEST_USER_PASSWORD \
  --count 10 \
  --output ../artifacts/uploads/bulk-10.json
```

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
source .venv/bin/activate
python scripts/bulk_upload.py \
  --base-url http://localhost:8000 \
  --email YOUR_TEST_USER_EMAIL \
  --password YOUR_TEST_USER_PASSWORD \
  --count 50 \
  --concurrency 6 \
  --output ../artifacts/uploads/bulk-50.json
```

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
source .venv/bin/activate
python scripts/bulk_upload.py \
  --base-url http://localhost:8000 \
  --email YOUR_TEST_USER_EMAIL \
  --password YOUR_TEST_USER_PASSWORD \
  --count 100 \
  --concurrency 8 \
  --output ../artifacts/uploads/bulk-100.json
```

Metrics captured:

- requested files
- successful uploads
- failed uploads
- upload success rate
- indexing success rate
- average upload time
- p95 upload time
- per-file HTTP status and document status

## Playwright Functional Tests

Files:

- [frontend/playwright.config.ts](/Users/aravindbandipelli/Desktop/AravindCode-bot/frontend/playwright.config.ts)
- [frontend/e2e/org-workspace.spec.ts](/Users/aravindbandipelli/Desktop/AravindCode-bot/frontend/e2e/org-workspace.spec.ts)

These tests cover:

- signup
- login
- logout
- organization creation
- joining an existing organization by entering the same organization name with different casing
- same-organization file visibility
- same-organization retrieval and citations
- different-organization isolation

Important local test assumption:

- disable Supabase email confirmation for automated local signup, or use a testing setup where new accounts can sign in immediately

Install Playwright:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/frontend
npm install
npx playwright install chromium
```

Run:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/frontend
PLAYWRIGHT_E2E_PASSWORD='YOUR_TEST_PASSWORD' npm run test:e2e
```

Optional headed run:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/frontend
PLAYWRIGHT_E2E_PASSWORD='YOUR_TEST_PASSWORD' npm run test:e2e:headed
```

## Retrieval Evaluation

Files:

- [docs/evaluation/organization_eval_dataset.jsonl](/Users/aravindbandipelli/Desktop/AravindCode-bot/docs/evaluation/organization_eval_dataset.jsonl)
- [backend/scripts/run_evals.py](/Users/aravindbandipelli/Desktop/AravindCode-bot/backend/scripts/run_evals.py)

Run locally:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
source .venv/bin/activate
python scripts/run_evals.py \
  --base-url http://localhost:8000 \
  --output ../artifacts/evals/latest.json
```

Run against a protected deployment:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
source .venv/bin/activate
python scripts/get_test_token.py \
  --email YOUR_TEST_USER_EMAIL \
  --password YOUR_TEST_USER_PASSWORD > /tmp/knowledge-hub.token

python scripts/run_evals.py \
  --base-url https://YOUR_BACKEND_HOST \
  --bearer-token "$(cat /tmp/knowledge-hub.token)" \
  --output ../artifacts/evals/latest.json
```

Metrics captured:

- top-3 retrieval accuracy
- top-5 retrieval accuracy
- hit rate
- mean reciprocal rank
- grounded answer rate
- citation coverage rate
- low-confidence fallback precision
- hallucination rate
- average and p95 retrieval latency
- average and p95 answer latency

## k6 Load Testing

Script:

- [tests/load/knowledge_hub.js](/Users/aravindbandipelli/Desktop/AravindCode-bot/tests/load/knowledge_hub.js)

Run locally:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
source .venv/bin/activate
TOKEN=$(python scripts/get_test_token.py --email YOUR_TEST_USER_EMAIL --password YOUR_TEST_USER_PASSWORD)

cd /Users/aravindbandipelli/Desktop/AravindCode-bot
k6 run \
  -e BASE_URL=http://localhost:8000 \
  -e K6_BEARER_TOKEN="$TOKEN" \
  -e SUPABASE_URL=https://YOUR_PROJECT.supabase.co \
  -e SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY \
  -e K6_LOGIN_EMAIL=YOUR_TEST_USER_EMAIL \
  -e K6_LOGIN_PASSWORD=YOUR_TEST_USER_PASSWORD \
  tests/load/knowledge_hub.js
```

Optional upload scenario:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot
k6 run \
  -e BASE_URL=http://localhost:8000 \
  -e K6_BEARER_TOKEN="$TOKEN" \
  -e ENABLE_UPLOAD=true \
  tests/load/knowledge_hub.js
```

Metrics captured:

- p50 and p95 login latency
- p50 and p95 query latency
- p50 and p95 documents-list latency
- p50 and p95 ingestion latency
- error rate
- throughput
- ingestion success rate

## SQL Verification Queries

Organizations:

```sql
select id, name, slug, created_at
from public.organizations
order by created_at desc;
```

Memberships:

```sql
select organization_id, user_id, role, joined_at
from public.organization_members
order by joined_at desc;
```

Documents:

```sql
select organization_id, original_name, status, created_at
from public.documents
order by created_at desc;
```
