"""The tenant-plane dependencies: token plane matrix, the flat check, the
window, the union, and the object-scope hook — everything provable without a
database. The database-backed halves live in the integration and isolation
suites.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import column, select

from verity.core import security
from verity.core.deps import (
    EngagementScope,
    Principal,
    RoleGrant,
    TenantContext,
    active_role_ids,
    assignment_window_active,
    get_current_principal,
    get_tenant_context,
    require,
)
from verity.core.errors import AuthenticationRequired, InvalidToken, PermissionDenied
from verity.core.security import issue_token

TODAY = date(2026, 8, 12)


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _principal(**overrides: object) -> Principal:
    base = Principal(
        user_id=uuid.uuid4(),
        membership_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        permissions=frozenset({"members:read"}),
    )
    return replace(base, **overrides)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Principal — unchanged contract from the foundation change
# ---------------------------------------------------------------------------


def test_a_principal_carries_the_membership_not_only_the_user() -> None:
    """ADR-0011: every in-tenant reference to a person is the membership."""
    principal = _principal(permissions=frozenset({"controls:read"}))
    assert principal.membership_id is not None
    assert principal.has("controls:read")
    assert not principal.has("controls:edit")


def test_a_principal_denies_by_default() -> None:
    assert not Principal(user_id=uuid.uuid4()).has("controls:read")


def test_a_principal_is_immutable() -> None:
    principal = Principal(user_id=uuid.uuid4())
    with pytest.raises(AttributeError):
        principal.is_platform_admin = True  # type: ignore[misc]


def test_repr_does_not_dump_every_permission() -> None:
    principal = Principal(
        user_id=uuid.uuid4(), permissions=frozenset({f"module{n}:read" for n in range(50)})
    )
    assert "module7:read" not in repr(principal)


def test_tenant_context_records_impersonation() -> None:
    context = TenantContext(tenant_id=uuid.uuid4(), via_impersonation=True)
    assert context.membership_id is None
    assert context.via_impersonation


# ---------------------------------------------------------------------------
# Token plane matrix — every rejection happens before any database is touched
# ---------------------------------------------------------------------------


async def test_no_bearer_token_is_401() -> None:
    with pytest.raises(AuthenticationRequired):
        await get_current_principal(None)


async def test_garbage_token_is_invalid() -> None:
    with pytest.raises(InvalidToken):
        await get_current_principal(_bearer("not-a-token"))


async def test_provider_session_token_is_403_on_the_tenant_plane() -> None:
    """The caller is authenticated, just categorically not a tenant user."""
    issued = issue_token(subject=uuid.uuid4(), plane="provider", typ="session")
    with pytest.raises(PermissionDenied):
        await get_current_principal(_bearer(issued.token))


@pytest.mark.parametrize("typ", ["challenge", "selection", "invite"])
async def test_non_session_tenant_tokens_are_rejected(typ: str) -> None:
    """The challenge/session split holds: a partial credential opens nothing."""
    issued = issue_token(subject=uuid.uuid4(), plane="tenant", typ=typ)
    with pytest.raises(InvalidToken):
        await get_current_principal(_bearer(issued.token))


async def test_expired_session_token_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    real_now = security._now
    monkeypatch.setattr(security, "_now", lambda: real_now() - 13 * 3600)
    issued = issue_token(subject=uuid.uuid4(), plane="tenant", typ="session")
    monkeypatch.setattr(security, "_now", real_now)
    with pytest.raises(InvalidToken):
        await get_current_principal(_bearer(issued.token))


# ---------------------------------------------------------------------------
# require — the flat check
# ---------------------------------------------------------------------------


async def test_require_passes_and_returns_the_principal() -> None:
    principal = _principal()
    assert await require("members:read")(principal=principal) is principal


async def test_require_denies_with_403_when_the_key_is_absent() -> None:
    with pytest.raises(PermissionDenied):
        await require("members:invite")(principal=_principal())


def test_require_exposes_its_declaration_for_introspection() -> None:
    dependency = require("evidence:approve")
    assert dependency.required_permission == "evidence:approve"  # type: ignore[attr-defined]
    assert dependency.object_scope is None  # type: ignore[attr-defined]


async def test_get_tenant_context_comes_from_the_membership() -> None:
    principal = _principal()
    context = await get_tenant_context(principal)
    assert context.tenant_id == principal.tenant_id
    assert context.membership_id == principal.membership_id


async def test_get_tenant_context_refuses_a_principal_without_a_membership() -> None:
    with pytest.raises(AuthenticationRequired):
        await get_tenant_context(Principal(user_id=uuid.uuid4()))


# ---------------------------------------------------------------------------
# The time-box and the union
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("valid_from", "valid_until", "expected"),
    [
        (None, None, True),
        (TODAY, TODAY, True),
        (TODAY - timedelta(days=1), TODAY + timedelta(days=1), True),
        (TODAY + timedelta(days=1), None, False),  # not yet begun
        (None, TODAY - timedelta(days=1), False),  # expired means invisible
        (TODAY, None, True),
        (None, TODAY, True),
    ],
)
def test_assignment_window(
    valid_from: date | None, valid_until: date | None, expected: bool
) -> None:
    assert assignment_window_active(valid_from, valid_until, TODAY) is expected


def test_active_role_ids_unions_direct_and_group_grants() -> None:
    membership = uuid.uuid4()
    group = uuid.uuid4()
    direct_role, group_role = uuid.uuid4(), uuid.uuid4()
    grants = [
        RoleGrant(role_id=direct_role, assignee_type="membership", assignee_id=membership),
        RoleGrant(role_id=group_role, assignee_type="group", assignee_id=group),
    ]
    assert active_role_ids(
        grants, membership_id=membership, group_ids=[group], today=TODAY
    ) == frozenset({direct_role, group_role})


def test_active_role_ids_excludes_expired_and_foreign_grants() -> None:
    membership = uuid.uuid4()
    group = uuid.uuid4()
    expired, foreign_member, foreign_group, future = (
        uuid.uuid4(),
        uuid.uuid4(),
        uuid.uuid4(),
        uuid.uuid4(),
    )
    grants = [
        RoleGrant(
            role_id=expired,
            assignee_type="membership",
            assignee_id=membership,
            valid_until=TODAY - timedelta(days=1),
        ),
        RoleGrant(
            role_id=future,
            assignee_type="membership",
            assignee_id=membership,
            valid_from=TODAY + timedelta(days=1),
        ),
        RoleGrant(role_id=foreign_member, assignee_type="membership", assignee_id=uuid.uuid4()),
        RoleGrant(role_id=foreign_group, assignee_type="group", assignee_id=uuid.uuid4()),
    ]
    assert (
        active_role_ids(grants, membership_id=membership, group_ids=[group], today=TODAY)
        == frozenset()
    )


# ---------------------------------------------------------------------------
# EngagementScope — the object-scope hook (SQL half proven against the DB)
# ---------------------------------------------------------------------------


def _scope_with_ids(monkeypatch: pytest.MonkeyPatch, ids: frozenset[uuid.UUID]) -> EngagementScope:
    async def fake_ids(
        self: EngagementScope, session: object, principal: object
    ) -> frozenset[uuid.UUID]:
        return ids

    monkeypatch.setattr(EngagementScope, "active_engagement_ids", fake_ids)
    return EngagementScope()


async def test_engagement_scope_allows_only_its_engagements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engagement = uuid.uuid4()
    scope = _scope_with_ids(monkeypatch, frozenset({engagement}))
    principal = _principal()
    assert await scope.allows(None, principal, engagement)  # type: ignore[arg-type]
    assert not await scope.allows(None, principal, uuid.uuid4())  # type: ignore[arg-type]


async def test_engagement_scope_filter_narrows_to_the_active_engagements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engagement = uuid.uuid4()
    scope = _scope_with_ids(monkeypatch, frozenset({engagement}))
    query = await scope.filter(None, _principal(), select(column("engagement_id")))  # type: ignore[arg-type]
    sql = str(query)
    assert "engagement_id IN" in sql


async def test_engagement_scope_with_no_engagements_matches_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = _scope_with_ids(monkeypatch, frozenset())
    query = await scope.filter(None, _principal(), select(column("engagement_id")))  # type: ignore[arg-type]
    assert "false" in str(query).lower()


def test_windows_are_evaluated_in_utc_not_local_time() -> None:
    """A grant expiring 'today' stays valid until the UTC day rolls over."""
    now_utc = datetime.now(UTC).date()
    assert assignment_window_active(None, now_utc, now_utc)
