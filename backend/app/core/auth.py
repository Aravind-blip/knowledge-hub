from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import httpx
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_unscoped_db_session
from app.models import Organization, OrganizationMember

logger = logging.getLogger(__name__)
settings = get_settings()
DEMO_USER_ID = UUID("00000000-0000-0000-0000-000000000000")
DEMO_ORG_ID = UUID("00000000-0000-0000-0000-000000000001")


@dataclass(frozen=True)
class AuthIdentity:
    user_id: UUID
    email: Optional[str]
    access_token: Optional[str]
    is_demo_user: bool = False


@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID
    email: Optional[str]
    access_token: Optional[str]
    organization_id: UUID
    organization_name: str
    organization_slug: str
    role: str
    is_demo_user: bool = False


def _slugify(value: str) -> str:
    lowered = value.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "workspace"


def _build_default_workspace_name(email: Optional[str]) -> tuple[str, str]:
    if email and "@" in email:
        local_part, domain = email.split("@", 1)
        domain_name = domain.split(".", 1)[0].replace("-", " ").strip()
        if domain_name:
            name = f"{domain_name.title()} Workspace"
        else:
            name = f"{local_part.title()} Workspace"
        slug_base = f"{_slugify(domain_name or local_part)}-{local_part[:8]}"
        return name, _slugify(slug_base)
    return "Demo Workspace", "demo-workspace"


async def get_auth_identity(authorization: Optional[str] = Header(default=None)) -> AuthIdentity:
    if not settings.require_auth:
        return AuthIdentity(user_id=DEMO_USER_ID, email=None, access_token=None, is_demo_user=True)

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

    return AuthIdentity(
        user_id=UUID(user_id),
        email=payload.get("email"),
        access_token=token,
        is_demo_user=False,
    )


async def get_current_user(
    identity: AuthIdentity = Depends(get_auth_identity),
    session: AsyncSession = Depends(get_unscoped_db_session),
) -> CurrentUser:
    membership = await _ensure_membership(session, identity)
    organization = membership.organization
    return CurrentUser(
        user_id=membership.user_id,
        email=identity.email,
        access_token=identity.access_token,
        organization_id=membership.organization_id,
        organization_name=organization.name,
        organization_slug=organization.slug,
        role=membership.role,
        is_demo_user=identity.is_demo_user,
    )


async def get_request_db_session(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_unscoped_db_session),
):
    await _set_request_context(session, current_user)
    try:
        yield session
    finally:
        await _reset_request_context(session)


async def require_org_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization admin access is required.")
    return current_user


async def _ensure_membership(session: AsyncSession, identity: AuthIdentity) -> OrganizationMember:
    result = await session.execute(
        select(OrganizationMember)
        .where(OrganizationMember.user_id == identity.user_id)
        .order_by(OrganizationMember.joined_at.asc())
    )
    membership = result.scalars().first()
    if membership:
        await session.refresh(membership, attribute_names=["organization"])
        return membership

    organization_id = DEMO_ORG_ID if identity.is_demo_user else uuid.uuid4()
    organization_name, organization_slug = _build_default_workspace_name(identity.email)
    if identity.is_demo_user:
        organization_name = "Demo Workspace"
        organization_slug = "demo-workspace"

    organization = await session.get(Organization, organization_id)
    if not organization:
        organization = Organization(
            id=organization_id,
            name=organization_name,
            slug=organization_slug,
        )
        session.add(organization)
        await session.flush()

    membership = OrganizationMember(
        organization_id=organization.id,
        user_id=identity.user_id,
        role="admin",
    )
    session.add(membership)
    await session.commit()
    await session.refresh(membership, attribute_names=["organization"])
    logger.info(
        "Provisioned default organization membership",
        extra={"organization_id": str(organization.id), "user_id": str(identity.user_id), "role": membership.role},
    )
    return membership


async def _set_request_context(session: AsyncSession, current_user: CurrentUser) -> None:
    await session.execute(
        text(
            """
            SELECT
                set_config('app.current_organization_id', :organization_id, false),
                set_config('app.current_user_id', :user_id, false),
                set_config('app.current_role', :role, false)
            """
        ),
        {
            "organization_id": str(current_user.organization_id),
            "user_id": str(current_user.user_id),
            "role": current_user.role,
        },
    )


async def _reset_request_context(session: AsyncSession) -> None:
    try:
        await session.execute(text("RESET app.current_organization_id"))
        await session.execute(text("RESET app.current_user_id"))
        await session.execute(text("RESET app.current_role"))
    except Exception:
        logger.debug("Request-scoped database context reset failed", exc_info=True)
