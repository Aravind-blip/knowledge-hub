# Knowledge Hub

Knowledge Hub is a full-stack document question-and-answer system for internal operations, policy, and support content. The application indexes uploaded business documents into PostgreSQL with pgvector, retrieves the most relevant evidence for a question, and returns a grounded result with source snippets and file names.

The repo is organized as a monorepo with a Next.js 15 frontend, a FastAPI backend, explicit database migrations, Groq and OpenAI provider support, fallback provider support for local development, and LangSmith tracing that can be enabled through environment variables.

## Architecture

```mermaid
flowchart LR
    A["Business documents"] --> B["FastAPI upload endpoint"]
    B --> C["Parser"]
    C --> D["Chunking service"]
    D --> E["Embedding provider"]
    E --> F["PostgreSQL + pgvector"]
    G["Next.js dashboard"] --> H["Search request"]
    H --> I["Retrieval service"]
    I --> F
    I --> J["LangGraph orchestration"]
    J --> K["Generation provider"]
    K --> L["Result with citations"]
    L --> G
    J -. optional trace spans .-> M["LangSmith"]
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
- Text-based PDF, Markdown, and plain text ingestion
- Chunking with LangChain text splitters
- Separate generation and embedding provider abstractions
- Groq chat generation support for free public demos
- Embedding provider abstraction with OpenAI and fallback modes
- Retrieval over pgvector-backed embeddings with lexical relevance safeguards
- LangGraph-based retrieval-plus-generation orchestration
- Grounded answers with cited snippets and source file names
- Optional LangSmith tracing for ingestion, retrieval, embeddings, generation, and request flows
- Docker-based local development
- Alembic migration path for hosted deployment
- CI workflows for frontend build and backend checks

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
- `GET /api/chat/sessions/{session_id}`

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

### Frontend: Vercel

1. Import the repository into Vercel.
2. Set the root directory to `frontend`.
3. Add environment variables:
   - `API_BASE_URL=https://YOUR_BACKEND_HOST`
   - `NEXT_PUBLIC_APP_URL=https://YOUR_VERCEL_HOST`
4. Deploy.

The repo config is in [infra/vercel.json](/Users/aravindbandipelli/Desktop/AravindCode-bot/infra/vercel.json).

### Backend: Render

1. Create a new Web Service from the repository root.
2. Use Docker with [infra/render.yaml](/Users/aravindbandipelli/Desktop/AravindCode-bot/infra/render.yaml).
3. Set environment variables:
   - `APP_ENV=production`
   - `GENERATION_PROVIDER=auto`
   - `EMBEDDING_PROVIDER=auto`
   - `ALLOW_FALLBACK_MODELS=true`
   - `GROQ_API_KEY=...`
   - `DATABASE_URL=...`
   - `ALLOWED_ORIGINS_RAW=https://YOUR_VERCEL_HOST`
   - `RUN_DB_MIGRATIONS_ON_STARTUP=true`
   - optionally `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY=...`, `LANGSMITH_PROJECT=knowledge-hub`
4. Confirm the health check path is `/api/health`.

### Backend: Railway

1. Create a new service from the repository.
2. Use [infra/railway.json](/Users/aravindbandipelli/Desktop/AravindCode-bot/infra/railway.json).
3. Set environment variables:
   - `APP_ENV=production`
   - `GENERATION_PROVIDER=auto`
   - `EMBEDDING_PROVIDER=auto`
   - `ALLOW_FALLBACK_MODELS=true`
   - `GROQ_API_KEY=...`
   - `DATABASE_URL=...`
   - `ALLOWED_ORIGINS_RAW=https://YOUR_VERCEL_HOST`
   - `RUN_DB_MIGRATIONS_ON_STARTUP=true`
   - optionally `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY=...`

### Free Public Deployment Recommendation

For a no-cost public demo:

- frontend on Vercel
- backend on Render
- database on Supabase Postgres
- `GENERATION_PROVIDER=auto`
- `EMBEDDING_PROVIDER=auto`
- `GROQ_API_KEY=...`
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
- Fallback mode still exists to keep the project runnable without secrets. It is not the recommended mode for accuracy-sensitive demos.
- OpenAI and LangSmith are fully env-driven. No secrets are stored in the frontend or committed to the repository.
- The backend now expects an explicit migration path for hosted deployment instead of relying on table auto-creation at startup.
- OCR is intentionally out of scope for this version. Text-based PDFs, Markdown, and plain text are the supported ingestion formats.
