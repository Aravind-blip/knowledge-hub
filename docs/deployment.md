# Deployment Guide

## Required Services

- Frontend: Vercel
- Backend: Render or Railway
- Database: Neon or Supabase Postgres

## Database Setup

1. Create a PostgreSQL database on Neon or Supabase.
2. Ensure the backend database user can enable `pgvector`.
3. Set `DATABASE_URL` with the async driver:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DATABASE
```

4. Run migrations:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
alembic -c alembic.ini upgrade head
```

## Backend Environment Variables

- `APP_ENV=production`
- `ALLOWED_ORIGINS_RAW=https://YOUR_VERCEL_HOST`
- `DATABASE_URL=...`
- `REQUIRE_AUTH=true`
- `SUPABASE_URL=https://YOUR_PROJECT.supabase.co`
- `SUPABASE_ANON_KEY=...`
- `GENERATION_PROVIDER=auto`
- `EMBEDDING_PROVIDER=auto`
- `ALLOW_FALLBACK_MODELS=true`
- `GROQ_API_KEY=...`
- optional `OPENAI_API_KEY=...`
- optional `OPENAI_CHAT_MODEL=gpt-4.1-mini`
- optional `OPENAI_EMBEDDING_MODEL=text-embedding-3-small`
- `RUN_DB_MIGRATIONS_ON_STARTUP=true`
- optional:
  - `LANGSMITH_TRACING=true`
  - `LANGSMITH_API_KEY=...`
  - `LANGSMITH_PROJECT=knowledge-hub`

For the free public deployment path, use:

- Groq for generation
- fallback embeddings
- Supabase Postgres for storage
- LangSmith disabled

## Vercel

- Root directory: `frontend`
- Environment variables:
  - `API_BASE_URL=https://YOUR_BACKEND_HOST`
  - `NEXT_PUBLIC_APP_URL=https://YOUR_VERCEL_HOST`
  - `NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY=...`
- Repo config: [vercel.json](/Users/aravindbandipelli/Desktop/AravindCode-bot/vercel.json)
- Set the Vercel project root directory to `frontend` in the project settings

## Render

- Config file: [infra/render.yaml](/Users/aravindbandipelli/Desktop/AravindCode-bot/infra/render.yaml)
- Health check path: `/api/health`
- Dockerfile path: `backend/Dockerfile`

## Railway

- Config file: [infra/railway.json](/Users/aravindbandipelli/Desktop/AravindCode-bot/infra/railway.json)
- Dockerfile path: `backend/Dockerfile`

## Verification

After deployment:

1. Hit `GET /api/health`
2. Sign in through Supabase Auth
3. Upload a demo document
4. Ask a question against the uploaded content
5. Confirm the workspace summary loads quality/performance metrics or the expected `Run evals` / `Run tests` placeholders
6. If LangSmith is enabled, confirm new runs appear in the configured project
