from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

DEFAULT_SUPABASE_URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
DEFAULT_SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")


@dataclass(frozen=True)
class SupabaseSession:
    access_token: str
    refresh_token: str
    user_id: str
    email: str


def slugify(value: str) -> str:
    lowered = value.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "workspace"


def build_backend_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
    }


async def sign_in_with_supabase(
    *,
    email: str,
    password: str,
    supabase_url: str | None = None,
    supabase_anon_key: str | None = None,
) -> SupabaseSession:
    url = (supabase_url or DEFAULT_SUPABASE_URL or "").rstrip("/")
    anon_key = supabase_anon_key or DEFAULT_SUPABASE_ANON_KEY
    if not url or not anon_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY are required to sign in test users.")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{url}/auth/v1/token?grant_type=password",
            headers={
                "apikey": anon_key,
                "Content-Type": "application/json",
            },
            json={
                "email": email,
                "password": password,
            },
        )
    if response.status_code != 200:
        detail = response.text
        raise RuntimeError(f"Supabase sign-in failed: {response.status_code} {detail}")
    payload = response.json()
    user = payload.get("user") or {}
    return SupabaseSession(
        access_token=payload["access_token"],
        refresh_token=payload["refresh_token"],
        user_id=user.get("id", ""),
        email=user.get("email", email),
    )


def write_json_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
