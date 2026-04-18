from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import httpx
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
    full_name: Optional[str] = None
    organization_name: Optional[str] = None
    is_demo_user: bool = False


@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID
    email: Optional[str]
    access_token: Optional[str]
    full_name: Optional[str]
    organization_id: UUID
    organization_name: str
    organization_slug: str
    role: str
    is_demo_user: bool = False


def _slugify(value: str) -> str:
    lowered = value.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "workspace"


def _normalize_organization_name(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = " ".join(value.split()).strip()
    if not normalized:
        return None
    return normalized[:255]


def _resolve_signup_organization_name(metadata: dict) -> Optional[str]:
    for key in ("organization_name", "organization", "workspace_name"):
        organization_name = _normalize_organization_name(metadata.get(key))
        if organization_name:
            return organization_name
    return None


def _resolve_full_name(metadata: dict) -> Optional[str]:
    for key in ("full_name", "name"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:255]
    return None


def _default_organization_id(identity: AuthIdentity) -> UUID:
    if identity.is_demo_user:
        return DEMO_ORG_ID
    organization_name = _normalize_organization_name(identity.organization_name)
    if organization_name:
        return uuid.uuid5(uuid.NAMESPACE_URL, f"knowledge-hub:organization:{_slugify(organization_name)}")
    return uuid.uuid5(uuid.NAMESPACE_URL, f"knowledge-hub:organization:{identity.user_id}")


def _build_default_workspace_profile(identity: AuthIdentity) -> tuple[UUID, str, str]:
    organization_id = _default_organization_id(identity)
    if identity.is_demo_user:
        return organization_id, "Demo Workspace", "demo-workspace"

    organization_name = _normalize_organization_name(identity.organization_name)
    if not organization_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Your account is missing an organization workspace. Create a workspace during signup or contact an administrator.",
        )
    return organization_id, organization_name, _slugify(organization_name)


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
    user_metadata = payload.get("user_metadata") or {}

    return AuthIdentity(
        user_id=UUID(user_id),
        email=payload.get("email"),
        access_token=token,
        full_name=_resolve_full_name(user_metadata),
        organization_name=_resolve_signup_organization_name(user_metadata),
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
        full_name=identity.full_name,
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
        .options(selectinload(OrganizationMember.organization))
        .where(OrganizationMember.user_id == identity.user_id)
        .order_by(OrganizationMember.joined_at.asc())
    )
    membership = result.scalars().first()
    if membership:
        return membership

    organization_id, organization_name, organization_slug = _build_default_workspace_profile(identity)
    organization_insert = await session.execute(
        insert(Organization)
        .values(
            id=organization_id,
            name=organization_name,
            slug=organization_slug,
        )
        .on_conflict_do_nothing(constraint="uq_organizations_slug")
        .returning(Organization.id)
    )
    created_organization_id = organization_insert.scalar_one_or_none()
    organization_lookup = await session.execute(select(Organization).where(Organization.slug == organization_slug))
    organization = organization_lookup.scalars().first()
    if not organization:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="We couldn't finish setting up your organization workspace. Please try again.",
        )

    role = "admin" if created_organization_id else "member"
    if not created_organization_id:
        member_count = await session.scalar(
            select(func.count()).select_from(OrganizationMember).where(OrganizationMember.organization_id == organization.id)
        )
        if int(member_count or 0) == 0:
            role = "admin"

    await session.execute(
        insert(OrganizationMember)
        .values(
            organization_id=organization.id,
            user_id=identity.user_id,
            role=role,
        )
        .on_conflict_do_nothing(constraint="uq_organization_members_org_user")
    )
    await session.commit()

    result = await session.execute(
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.organization))
        .where(OrganizationMember.user_id == identity.user_id)
        .order_by(OrganizationMember.joined_at.asc())
    )
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to provision organization membership.",
        )
    logger.info(
        "Provisioned organization membership",
        extra={
            "organization_id": str(membership.organization_id),
            "organization_slug": membership.organization.slug,
            "user_id": str(identity.user_id),
            "role": membership.role,
        },
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
