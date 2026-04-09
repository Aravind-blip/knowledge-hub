# Knowledge Hub

Knowledge Hub is a full-stack document question-and-answer system for internal operations, policy, and support content. The application indexes uploaded business documents into PostgreSQL with pgvector, retrieves the most relevant evidence for a question, and returns a grounded result with source snippets and file names.

The repo is organized as a monorepo with a Next.js 15 frontend, a FastAPI backend, explicit database migrations, Supabase Auth for user isolation, Groq and OpenAI provider support, fallback provider support for local development, and LangSmith tracing that can be enabled through environment variables.

## Architecture

```mermaid
flowchart LR
    A["Supabase Auth"] --> G["Next.js dashboard"]
    G --> H["Bearer token to FastAPI"]
    I["Business documents"] --> B["FastAPI upload endpoint"]
    B --> C["Parser"]
    C --> D["Chunking service"]
    D --> E["Embedding provider"]
    E --> F["PostgreSQL + pgvector"]
    H --> J["User-scoped retrieval service"]
    J --> F
    J --> K["LangGraph orchestration"]
    K --> L["Generation provider"]
    L --> M["Result with citations"]
    M --> G
    F -. owner filters and RLS .-> J
    K -. optional trace spans .-> N["LangSmith"]
```

## Repository Layout

```text
knowledge-hub/
  frontend/
  backend/
  infra/
  docs/
  .github/workflows/
```

Key paths:

- [frontend](/Users/aravindbandipelli/Desktop/AravindCode-bot/frontend)
- [backend](/Users/aravindbandipelli/Desktop/AravindCode-bot/backend)
- [infra/docker-compose.yml](/Users/aravindbandipelli/Desktop/AravindCode-bot/infra/docker-compose.yml)
- [backend/alembic.ini](/Users/aravindbandipelli/Desktop/AravindCode-bot/backend/alembic.ini)
- [infra/db/migrations](/Users/aravindbandipelli/Desktop/AravindCode-bot/infra/db/migrations)

## Implemented Capabilities

- Next.js 15 frontend with document list, upload workflow, search workspace, and results view
- FastAPI backend with async SQLAlchemy models and typed Pydantic responses
- Supabase Auth-backed sign-in with per-user document and chat isolation
- Text-based PDF, Markdown, and plain text ingestion
- Chunking with LangChain text splitters
- Separate generation and embedding provider abstractions
- Groq chat generation support for free public demos
- Embedding provider abstraction with OpenAI and fallback modes
- Retrieval over pgvector-backed embeddings with lexical relevance safeguards
- LangGraph-based retrieval-plus-generation orchestration
- Grounded answers with cited snippets and source file names
- Optional LangSmith tracing for ingestion, retrieval, embeddings, generation, and request flows
- User ownership on documents, chunks, chat sessions, chat messages, and ingestion jobs
- User-scoped retrieval and API filtering to prevent cross-user access
- Supabase/Postgres row-level security policies for user-owned records
- Docker-based local development
- Alembic migration path for hosted deployment
- CI workflows for frontend build and backend checks

## Auth and Security Model

- Supabase Auth is the identity provider for deployed multi-user environments.
- The backend validates each bearer token against Supabase Auth before serving document, retrieval, or chat routes.
- `documents`, `document_chunks`, `chat_sessions`, `chat_messages`, and `ingestion_jobs` now carry a `user_id`.
- Backend queries explicitly filter by the authenticated user so retrieval and history stay isolated even before database policies are evaluated.
- Supabase/Postgres row-level security policies are created for the user-owned tables to mirror the same ownership boundary inside the database.
- Old shared demo rows are intentionally left with `user_id = NULL` during migration. They become inaccessible to signed-in users until they are re-uploaded or reassigned manually.

## Provider Configuration

Generation and embeddings are configured separately:

- `GENERATION_PROVIDER`
  - `auto`: prefer Groq, then OpenAI, then fallback
  - `groq`: require `GROQ_API_KEY`
  - `openai`: require `OPENAI_API_KEY`
  - `fallback`: use the extractive fallback answer generator
- `EMBEDDING_PROVIDER`
  - `auto`: prefer OpenAI, then fallback
  - `openai`: require `OPENAI_API_KEY`
  - `fallback`: use the local hash embedding service

Recommended modes:

- free public deployment: Groq generation + fallback embeddings
- higher quality local or private demo: OpenAI generation + OpenAI embeddings
- secret-free local plumbing: fallback generation + fallback embeddings

## Retrieval and Evidence Tradeoffs

- `CHUNK_SIZE`
  Larger chunks preserve more context but increase noise in retrieval and can dilute citations. The default `1000` characters is tuned for policy and operations content.
- `CHUNK_OVERLAP`
  Overlap reduces boundary loss but increases duplicate evidence. The default `150` characters keeps adjacent procedure steps intact.
- `RETRIEVAL_LIMIT`
  More retrieved chunks can help recall, but too many weak chunks make grounded answers less reliable. The default `6` is a balanced working set.
- `RETRIEVAL_MIN_SCORE` and `RETRIEVAL_MIN_TERM_OVERLAP`
  These guard against low-quality matches, especially in fallback mode.
- `ANSWER_MIN_SCORE`
  If no citation clears this threshold, the backend returns `Not enough information found in indexed documents.` rather than forcing a weak answer.

## Local Setup

### Initial Setup

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd ../frontend
npm install
```

### Required Frontend Auth Environment

Set [frontend/.env.local](/Users/aravindbandipelli/Desktop/AravindCode-bot/frontend/.env.local):

```env
API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### Run PostgreSQL

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot
docker compose -f infra/docker-compose.yml up postgres -d
```

### Run Migrations

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
source .venv/bin/activate
alembic -c alembic.ini upgrade head
```

### Start Without Docker

Terminal 1:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Terminal 2:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/frontend
npm run dev
```

### Start With Docker

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot
docker compose -f infra/docker-compose.yml up --build
```

## Local Fallback Mode

Use this when you want the app to run without external model credentials.

Set [backend/.env](/Users/aravindbandipelli/Desktop/AravindCode-bot/backend/.env):

```env
REQUIRE_AUTH=false
GENERATION_PROVIDER=fallback
EMBEDDING_PROVIDER=fallback
ALLOW_FALLBACK_MODELS=true
OPENAI_API_KEY=
LANGSMITH_TRACING=false
RUN_DB_MIGRATIONS_ON_STARTUP=false
```

Then run:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
source .venv/bin/activate
alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload --port 8000
```

In this mode, the backend uses a single local demo user boundary instead of Supabase Auth so the original secret-free workflow still works on one machine.

## Local Multi-User Auth Mode

Use this when you want the same user-isolated behavior as production.

Set [backend/.env](/Users/aravindbandipelli/Desktop/AravindCode-bot/backend/.env):

```env
REQUIRE_AUTH=true
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
GENERATION_PROVIDER=groq
EMBEDDING_PROVIDER=fallback
ALLOW_FALLBACK_MODELS=true
GROQ_API_KEY=your_groq_key
LANGSMITH_TRACING=false
RUN_DB_MIGRATIONS_ON_STARTUP=false
```

Set [frontend/.env.local](/Users/aravindbandipelli/Desktop/AravindCode-bot/frontend/.env.local):

```env
API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

Then run the backend and frontend as normal. Each signed-in user will see only their own uploaded files and chat history.

## Local Groq Mode

Use this when you want hosted chat generation without paying for OpenAI.

Set [backend/.env](/Users/aravindbandipelli/Desktop/AravindCode-bot/backend/.env):

```env
GENERATION_PROVIDER=groq
EMBEDDING_PROVIDER=fallback
ALLOW_FALLBACK_MODELS=true
GROQ_API_KEY=your_groq_key
GROQ_CHAT_MODEL=llama-3.1-8b-instant
OPENAI_API_KEY=
LANGSMITH_TRACING=false
RUN_DB_MIGRATIONS_ON_STARTUP=false
```

Then start the backend:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
source .venv/bin/activate
alembic -c alembic.ini upgrade head
python scripts/verify_groq_provider.py
uvicorn app.main:app --reload --port 8000
```

## Local OpenAI Mode

Use this when you want real OpenAI embeddings and chat completions.

Set [backend/.env](/Users/aravindbandipelli/Desktop/AravindCode-bot/backend/.env):

```env
GENERATION_PROVIDER=openai
EMBEDDING_PROVIDER=openai
ALLOW_FALLBACK_MODELS=false
OPENAI_API_KEY=your_real_key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4.1-mini
LANGSMITH_TRACING=false
RUN_DB_MIGRATIONS_ON_STARTUP=false
```

Then re-run migrations if needed and start the backend:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
source .venv/bin/activate
alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload --port 8000
```

Important:

- If you switch from fallback embeddings to OpenAI embeddings, reindex the documents.
- The simplest reset for local Docker Postgres is:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot
docker compose -f infra/docker-compose.yml down -v
docker compose -f infra/docker-compose.yml up postgres -d
```

## LangSmith Setup

Set [backend/.env](/Users/aravindbandipelli/Desktop/AravindCode-bot/backend/.env):

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=knowledge-hub
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

Tracing is wired into:

- document ingestion
- embedding calls
- retrieval
- answer generation
- `/api/chat/ask`
- `/api/chat/retrieve`

Verify tracing locally:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
source .venv/bin/activate
python scripts/verify_langsmith_tracing.py
```

Then perform a normal upload or search request and confirm runs appear in your LangSmith project.

## Verification Scripts

Groq generation verification:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
source .venv/bin/activate
python scripts/verify_groq_provider.py
```

Real OpenAI provider verification:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
source .venv/bin/activate
python scripts/verify_openai_provider.py
```

Evaluation script:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
source .venv/bin/activate
python scripts/eval.py
```

Demo data seed:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
source .venv/bin/activate
python scripts/seed_demo.py
```

## API Surface

- `GET /api/health`
- `GET /api/documents`
- `POST /api/documents/upload`
- `POST /api/chat/retrieve`
- `POST /api/chat/ask`
- `GET /api/chat/sessions`
- `GET /api/chat/sessions/{session_id}`

All document and chat routes are authenticated when `REQUIRE_AUTH=true`.

## Common Commands

Backend checks:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
source .venv/bin/activate
ruff check app tests scripts
pytest
```

Frontend checks:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/frontend
npm run lint
npm run typecheck
npm run build
```

## Deployment

### Database: Neon or Supabase Postgres

1. Create a Postgres database.
2. Ensure the database user can run `CREATE EXTENSION vector`.
3. Set `DATABASE_URL` for the backend using the async SQLAlchemy form:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DATABASE
```

4. Run migrations:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
alembic -c alembic.ini upgrade head
```

5. For Supabase deployments, enable auth in the dashboard and make sure email/password sign-in is available.
6. The auth migration adds `user_id` columns and RLS policies. Existing demo rows remain unowned and are not exposed to signed-in users.

### Frontend: Vercel

1. Import the repository into Vercel.
2. Set the root directory to `frontend`.
3. Add environment variables:
   - `API_BASE_URL=https://YOUR_BACKEND_HOST`
   - `NEXT_PUBLIC_APP_URL=https://YOUR_VERCEL_HOST`
   - `NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key`
4. Deploy.

The repo config is in [vercel.json](/Users/aravindbandipelli/Desktop/AravindCode-bot/vercel.json). Set the Vercel project root directory to `frontend` in the dashboard.

### Backend: Render

1. Create a new Web Service from the repository root.
2. Use Docker with [infra/render.yaml](/Users/aravindbandipelli/Desktop/AravindCode-bot/infra/render.yaml).
3. Set environment variables:
   - `APP_ENV=production`
   - `REQUIRE_AUTH=true`
   - `GENERATION_PROVIDER=auto`
   - `EMBEDDING_PROVIDER=auto`
   - `ALLOW_FALLBACK_MODELS=true`
   - `GROQ_API_KEY=...`
   - `DATABASE_URL=...`
   - `SUPABASE_URL=https://YOUR_PROJECT.supabase.co`
   - `SUPABASE_ANON_KEY=...`
   - `ALLOWED_ORIGINS_RAW=https://YOUR_VERCEL_HOST`
   - `RUN_DB_MIGRATIONS_ON_STARTUP=true`
   - optionally `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY=...`, `LANGSMITH_PROJECT=knowledge-hub`
4. Confirm the health check path is `/api/health`.

### Backend: Railway

1. Create a new service from the repository.
2. Use [infra/railway.json](/Users/aravindbandipelli/Desktop/AravindCode-bot/infra/railway.json).
3. Set environment variables:
   - `APP_ENV=production`
   - `REQUIRE_AUTH=true`
   - `GENERATION_PROVIDER=auto`
   - `EMBEDDING_PROVIDER=auto`
   - `ALLOW_FALLBACK_MODELS=true`
   - `GROQ_API_KEY=...`
   - `DATABASE_URL=...`
    - `SUPABASE_URL=https://YOUR_PROJECT.supabase.co`
    - `SUPABASE_ANON_KEY=...`
   - `ALLOWED_ORIGINS_RAW=https://YOUR_VERCEL_HOST`
   - `RUN_DB_MIGRATIONS_ON_STARTUP=true`
   - optionally `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY=...`

### Free Public Deployment Recommendation

For a no-cost public demo:

- frontend on Vercel
- backend on Render
- database on Supabase Postgres
- auth on Supabase Auth
- `GENERATION_PROVIDER=auto`
- `EMBEDDING_PROVIDER=auto`
- `REQUIRE_AUTH=true`
- `GROQ_API_KEY=...`
- `SUPABASE_URL=https://YOUR_PROJECT.supabase.co`
- `SUPABASE_ANON_KEY=...`
- leave `OPENAI_API_KEY` empty
- keep `LANGSMITH_TRACING=false`

## Troubleshooting

- If startup fails with a provider error:
  - check `GENERATION_PROVIDER` and `EMBEDDING_PROVIDER`
  - if `GENERATION_PROVIDER=groq`, ensure `GROQ_API_KEY` is set
  - if `GENERATION_PROVIDER=openai` or `EMBEDDING_PROVIDER=openai`, ensure `OPENAI_API_KEY` is set
  - if either provider is `auto`, provide the relevant key or keep `ALLOW_FALLBACK_MODELS=true`
- If startup fails with a schema error:
  - run `alembic -c alembic.ini upgrade head`
- If authenticated users cannot see old demo content after migration:
  - this is expected unless those rows were re-uploaded under a signed-in account
  - rows with `user_id = NULL` are intentionally hidden by the new ownership model
- If auth requests fail:
  - confirm `REQUIRE_AUTH=true` on the backend
  - confirm `SUPABASE_URL` and `SUPABASE_ANON_KEY` are set on the backend
  - confirm `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` are set on the frontend
  - confirm the frontend is forwarding a bearer token to the backend after sign-in
- If queries return poor results in fallback mode:
  - switch to OpenAI mode
  - reset and reindex the documents
- If LangSmith is enabled but no runs appear:
  - confirm `LANGSMITH_TRACING=true`
  - confirm `LANGSMITH_API_KEY` and `LANGSMITH_PROJECT`
  - run `python scripts/verify_langsmith_tracing.py`
- If Docker services cannot connect:
  - confirm Docker Desktop is running
  - use `docker compose -f infra/docker-compose.yml logs backend`
- If hosted startup fails on migrations:
  - confirm the database user can create the `vector` extension
  - run migrations manually once against the hosted database if your platform blocks extension creation during boot

## Production Notes

- The free deployment path uses Groq for chat generation and fallback embeddings by default.
- Deployed multi-user environments should run with `REQUIRE_AUTH=true` so all document and chat data is user-owned and isolated.
- Fallback mode still exists to keep the project runnable without secrets. It is not the recommended mode for accuracy-sensitive demos.
- Local fallback mode uses a single demo user identity so the pre-auth workflow still operates for solo development.
- OpenAI and LangSmith are fully env-driven. No secrets are stored in the frontend or committed to the repository.
- The backend now expects an explicit migration path for hosted deployment instead of relying on table auto-creation at startup.
- OCR is intentionally out of scope for this version. Text-based PDFs, Markdown, and plain text are the supported ingestion formats.
