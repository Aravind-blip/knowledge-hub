from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


@dataclass
class CheckResult:
    label: str
    status: str
    detail: str


def _env_present(name: str) -> CheckResult:
    value = os.getenv(name)
    return CheckResult(name, "ok" if value else "missing", "set" if value else "not set")


def _boolean_setting(name: str, value: str | None) -> CheckResult:
    normalized = (value or "").strip().lower()
    enabled = normalized in {"1", "true", "yes", "on"}
    return CheckResult(name, "ok" if enabled else "warning", "enabled" if enabled else "disabled")


def _load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


async def _database_check(database_url: str | None) -> CheckResult:
    if not database_url:
        return CheckResult("database", "missing", "DATABASE_URL is not set")

    engine = create_async_engine(database_url, future=True)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return CheckResult("database", "ok", "connected")
    except Exception as exc:  # pragma: no cover - exercised during manual local runs
        return CheckResult("database", "error", f"connection failed: {exc.__class__.__name__}")
    finally:
        await engine.dispose()


async def _health_check(base_url: str) -> CheckResult:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url.rstrip('/')}/api/health")
        if response.status_code != 200:
            return CheckResult("backend-health", "error", f"unexpected status {response.status_code}")
        payload = response.json()
        detail = (
            f"status={payload.get('status')} "
            f"database={payload.get('database_status')} "
            f"auth_enabled={payload.get('auth_enabled')}"
        )
        return CheckResult("backend-health", "ok", detail)
    except Exception as exc:  # pragma: no cover - exercised during manual local runs
        return CheckResult("backend-health", "error", f"unreachable: {exc.__class__.__name__}")


async def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    backend_env = _load_env_file(repo_root / "backend" / ".env")
    frontend_env = _load_env_file(repo_root / "frontend" / ".env.local")

    backend_url = os.getenv("KNOWLEDGE_HUB_BACKEND_URL") or f"http://127.0.0.1:{backend_env.get('API_PORT', '8000')}"
    frontend_url = os.getenv("KNOWLEDGE_HUB_FRONTEND_URL") or frontend_env.get("NEXT_PUBLIC_APP_URL", "http://127.0.0.1:3000")
    database_url = os.getenv("DATABASE_URL") or backend_env.get("DATABASE_URL")

    os.environ.setdefault("NEXT_PUBLIC_SUPABASE_URL", frontend_env.get("NEXT_PUBLIC_SUPABASE_URL", ""))
    os.environ.setdefault("NEXT_PUBLIC_SUPABASE_ANON_KEY", frontend_env.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", ""))
    os.environ.setdefault("SUPABASE_URL", backend_env.get("SUPABASE_URL", ""))
    os.environ.setdefault("SUPABASE_ANON_KEY", backend_env.get("SUPABASE_ANON_KEY", ""))

    results = [
        _boolean_setting("REQUIRE_AUTH", os.getenv("REQUIRE_AUTH") or backend_env.get("REQUIRE_AUTH")),
        _env_present("SUPABASE_URL"),
        _env_present("SUPABASE_ANON_KEY"),
        _env_present("NEXT_PUBLIC_SUPABASE_URL"),
        _env_present("NEXT_PUBLIC_SUPABASE_ANON_KEY"),
        await _database_check(database_url),
        await _health_check(backend_url),
    ]

    print("Knowledge Hub local auth doctor")
    print(f"  Frontend URL: {frontend_url}")
    print(f"  Backend URL:  {backend_url}")
    for result in results:
        print(f"  [{result.status.upper():7}] {result.label}: {result.detail}")


if __name__ == "__main__":
    asyncio.run(main())
