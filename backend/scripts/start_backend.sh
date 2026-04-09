#!/usr/bin/env sh
set -e

if [ "${RUN_DB_MIGRATIONS_ON_STARTUP:-false}" = "true" ]; then
  alembic -c alembic.ini upgrade head
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${API_PORT:-8000}"
