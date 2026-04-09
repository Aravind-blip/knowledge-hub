# Knowledge Hub Architecture

## Overview

Knowledge Hub uses a Next.js 15 frontend and a FastAPI backend backed by PostgreSQL with pgvector. The backend supports explicit provider selection for embeddings and answer generation, plus optional LangSmith tracing.

## Request Flow

1. A user uploads a PDF, Markdown, or plain text file.
2. FastAPI validates the file, stores it locally, and creates a `documents` record.
3. The ingestion service parses text, chunks the content, generates embeddings, and stores `document_chunks` rows in PostgreSQL.
4. A user submits a search request from the dashboard.
5. The retrieval service embeds the query, runs pgvector similarity search, applies lexical relevance safeguards, and returns source citations.
6. LangGraph coordinates retrieval and answer generation.
7. The result and its citations are saved in `chat_messages` and returned to the frontend.

## Main Components

- Frontend
  - Next.js App Router
  - route handlers under `frontend/app/api/*` proxying browser requests to the backend
  - React Query mutations for upload and search workflows
- Backend
  - FastAPI route modules for health, documents, and chat
  - SQLAlchemy models for documents, chunks, chat sessions, chat messages, and ingestion jobs
  - LangChain text splitting
  - provider abstractions for embeddings and generation
  - LangGraph state graph for retrieval-plus-generation orchestration
  - LangSmith trace service with clean degradation when disabled
- Database
  - PostgreSQL
  - pgvector for embedding storage and similarity search
  - Alembic migrations for schema management

## Replaceable Interfaces

- `EmbeddingService`
- `GenerationService`
- `TraceService`

These interfaces keep the route handlers stable while allowing provider or observability changes underneath.
