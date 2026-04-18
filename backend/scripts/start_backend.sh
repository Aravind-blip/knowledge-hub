#!/usr/bin/env sh
set -e

if [ "${RUN_DB_MIGRATIONS_ON_STARTUP:-false}" = "true" ]; then
  alembic -c alembic.ini upgrade head
fi

PORT_TO_BIND="${PORT:-${API_PORT:-8000}}"

echo "Knowledge Hub backend starting"
echo "  URL: http://127.0.0.1:${PORT_TO_BIND}"
echo "  Auth configured: ${REQUIRE_AUTH:-false}"
echo "  Database URL present: $( [ -n "${DATABASE_URL:-}" ] && echo yes || echo no )"
echo "  Supabase URL present: $( [ -n "${SUPABASE_URL:-}" ] && echo yes || echo no )"

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT_TO_BIND}"
