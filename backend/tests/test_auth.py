from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.core.auth import (
    AuthIdentity,
    _build_default_workspace_profile,
    _default_organization_id,
    _ensure_membership,
    _normalize_organization_name,
    _resolve_full_name,
    _resolve_signup_organization_name,
)


def test_resolve_signup_organization_name_accepts_multiple_metadata_keys() -> None:
    assert _resolve_signup_organization_name({"organization_name": "Acme Partners"}) == "Acme Partners"
    assert _resolve_signup_organization_name({"organization": "Northwind"}) == "Northwind"
    assert _resolve_signup_organization_name({"workspace_name": "Campus IT"}) == "Campus IT"
    assert _resolve_signup_organization_name({"organization_name": "   "}) is None


def test_resolve_full_name_accepts_supported_metadata_keys() -> None:
    assert _resolve_full_name({"full_name": "Ava Johnson"}) == "Ava Johnson"
    assert _resolve_full_name({"name": "Taylor Chen"}) == "Taylor Chen"
    assert _resolve_full_name({"name": "   "}) is None


def test_build_default_workspace_profile_uses_signup_org_name_not_email_domain() -> None:
    identity = AuthIdentity(
        user_id=UUID("12df5a43-c2ba-404e-ad93-5ddee27f5c7b"),
        email="person@gmail.com",
        access_token="token",
        full_name="Person Example",
        organization_name="Testing Workspace",
        is_demo_user=False,
    )

    organization_id, organization_name, organization_slug = _build_default_workspace_profile(identity)

    assert organization_id == _default_organization_id(identity)
    assert organization_name == "Testing Workspace"
    assert organization_slug == "testing-workspace"


def test_build_default_workspace_profile_requires_org_name_for_real_users() -> None:
    identity = AuthIdentity(
        user_id=UUID("12df5a43-c2ba-404e-ad93-5ddee27f5c7b"),
        email="person@gmail.com",
        access_token="token",
        organization_name=None,
        is_demo_user=False,
    )

    with pytest.raises(HTTPException) as exc_info:
        _build_default_workspace_profile(identity)

    assert exc_info.value.status_code == 409
    assert "organization workspace" in exc_info.value.detail


def test_organization_name_normalization_and_matching_are_case_insensitive() -> None:
    assert _normalize_organization_name(" C3U ") == "C3U"

    first = AuthIdentity(
        user_id=UUID("12df5a43-c2ba-404e-ad93-5ddee27f5c7b"),
        email="first@example.com",
        access_token="token",
        organization_name="C3U",
        is_demo_user=False,
    )
    second = AuthIdentity(
        user_id=UUID("aaaaaaaa-c2ba-404e-ad93-5ddee27f5c7b"),
        email="second@example.com",
        access_token="token",
        organization_name="c3u",
        is_demo_user=False,
    )
    third = AuthIdentity(
        user_id=UUID("bbbbbbbb-c2ba-404e-ad93-5ddee27f5c7b"),
        email="third@example.com",
        access_token="token",
        organization_name=" C3U ",
        is_demo_user=False,
    )

    assert _build_default_workspace_profile(first)[2] == "c3u"
    assert _build_default_workspace_profile(second)[2] == "c3u"
    assert _build_default_workspace_profile(third)[2] == "c3u"
    assert _default_organization_id(first) == _default_organization_id(second) == _default_organization_id(third)


@pytest.mark.anyio
async def test_ensure_membership_creates_admin_for_new_org() -> None:
    identity = AuthIdentity(
        user_id=UUID("12df5a43-c2ba-404e-ad93-5ddee27f5c7b"),
        email="person@gmail.com",
        access_token="token",
        full_name="Person Example",
        organization_name="Testing Workspace",
        is_demo_user=False,
    )
    membership = SimpleNamespace(
        user_id=identity.user_id,
        organization_id=UUID("6d5196f0-0834-5f9b-85cb-593f1f9708fa"),
        role="admin",
        organization=SimpleNamespace(name="Testing Workspace", slug="testing-workspace"),
    )
    execute_calls: list[str] = []
    execute_params: list[dict] = []

    class DummyScalarResult:
        def __init__(self, item):
            self._item = item

        def first(self):
            return self._item

    class DummyResult:
        def __init__(self, item):
            self._item = item

        def scalars(self):
            return DummyScalarResult(self._item)

        def scalar_one_or_none(self):
            return self._item

    class DummySession:
        def __init__(self):
            self._results = [
                DummyResult(None),
                DummyResult(UUID("6d5196f0-0834-5f9b-85cb-593f1f9708fa")),
                DummyResult(SimpleNamespace(id=UUID("6d5196f0-0834-5f9b-85cb-593f1f9708fa"), slug="testing-workspace")),
                DummyResult(None),
                DummyResult(membership),
            ]
            self.committed = 0
            self.rolled_back = 0

        async def execute(self, statement):
            execute_calls.append(str(statement))
            execute_params.append(statement.compile().params)
            return self._results.pop(0)

        async def scalar(self, statement):
            raise AssertionError("scalar() should not run for a newly created organization")

        async def commit(self):
            self.committed += 1

        async def rollback(self):
            self.rolled_back += 1

    session = DummySession()
    provisioned = await _ensure_membership(session, identity)

    assert provisioned is membership
    assert session.committed == 1
    assert session.rolled_back == 0
    assert "INSERT INTO organizations" in execute_calls[1]
    assert "ON CONFLICT ON CONSTRAINT uq_organizations_slug DO NOTHING" in execute_calls[1]
    assert "INSERT INTO organization_members" in execute_calls[3]
    assert execute_params[3]["role"] == "admin"


@pytest.mark.anyio
async def test_ensure_membership_joins_existing_org_as_member() -> None:
    identity = AuthIdentity(
        user_id=UUID("12df5a43-c2ba-404e-ad93-5ddee27f5c7b"),
        email="person@outlook.com",
        access_token="token",
        full_name="Person Example",
        organization_name="Testing Workspace",
        is_demo_user=False,
    )
    organization = SimpleNamespace(id=UUID("6d5196f0-0834-5f9b-85cb-593f1f9708fa"), slug="testing-workspace")
    membership = SimpleNamespace(
        user_id=identity.user_id,
        organization_id=organization.id,
        role="member",
        organization=SimpleNamespace(name="Testing Workspace", slug="testing-workspace"),
    )
    execute_calls: list[str] = []
    execute_params: list[dict] = []

    class DummyScalarResult:
        def __init__(self, item):
            self._item = item

        def first(self):
            return self._item

    class DummyResult:
        def __init__(self, item):
            self._item = item

        def scalars(self):
            return DummyScalarResult(self._item)

        def scalar_one_or_none(self):
            return self._item

    class DummySession:
        def __init__(self):
            self._results = [
                DummyResult(None),
                DummyResult(None),
                DummyResult(organization),
                DummyResult(None),
                DummyResult(membership),
            ]
            self._scalar_results = [1]
            self.committed = 0

        async def execute(self, statement):
            execute_calls.append(str(statement))
            execute_params.append(statement.compile().params)
            return self._results.pop(0)

        async def scalar(self, statement):
            return self._scalar_results.pop(0)

        async def commit(self):
            self.committed += 1

        async def rollback(self):
            raise AssertionError("rollback() should not run for a successful join")

    session = DummySession()
    provisioned = await _ensure_membership(session, identity)

    assert provisioned is membership
    assert session.committed == 1
    assert "INSERT INTO organization_members" in execute_calls[3]
    assert execute_params[3]["role"] == "member"
