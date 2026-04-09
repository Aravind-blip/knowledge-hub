from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import httpx
from fastapi import Header, HTTPException, status

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
DEMO_USER_ID = UUID("00000000-0000-0000-0000-000000000000")


@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID
    email: Optional[str]
    access_token: Optional[str]
    is_demo_user: bool = False


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> CurrentUser:
    if not settings.require_auth:
        return CurrentUser(user_id=DEMO_USER_ID, email=None, access_token=None, is_demo_user=True)

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": settings.supabase_anon_key or "",
                },
            )
    except httpx.HTTPError as exc:
        logger.exception("Supabase auth verification failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication provider is unavailable.",
        ) from exc

    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")

    payload = response.json()
    user_id = payload.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")

    return CurrentUser(
        user_id=UUID(user_id),
        email=payload.get("email"),
        access_token=token,
        is_demo_user=False,
    )
