"""IAM isolation: the five tenant-scoped identity tables against bound sessions.

Everything goes through the real entry points — the signup / invite / accept
flows, ``session_scope`` / ``provider_session_scope``, the iam service — as the
application role, against the migrated tables with their policies. The
unfiltered raw selects are deliberate: RLS has to hold when the application
filter is absent.

The policy shape (add-identity-and-access/design.md plus the migration's
identity-resolution addition):

    users, credentials, user_identities, permissions, role_permissions
        no tenant policy — global identity / global content plane
    tenant_memberships, groups, group_members, roles, role_assignments
        tenant policy (USING + WITH CHECK on tenant_id), ENABLE + FORCE
    tenant_memberships, group_members, roles, role_assignments
        + SELECT-only identity-resolution policy on app.provider_plane

The sharpest case in this file is the one ADR-0011 exists for: one person with
memberships in two tenants. A session bound to tenant A must not see that
person's own tenant-B membership — the wall runs between workspaces, not
between people.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.iam import (
    INVITEE_PASSWORD,
    SIGNUP_PASSWORD,
    Workspace,
    invite_directly,
    set_require_admin_mfa,
    signup_workspace,
    tenant_id_for,
    verify_signup_email,
)
from verity.core.db import dispose_engine, provider_session_scope, session_scope
from verity.core.errors import InvalidToken, NotFound
from verity.core.security import decode_token
from verity.db.base import Base
from verity.modules.iam.models import (
    ADMIN_ROLE_NAME,
    Group,
    GroupMember,
    Role,
    RoleAssignment,
    TenantMembership,
)
from verity.modules.iam.service import (
    BUILT_IN_ROLE_KEYS,
    ChallengeIssued,
    EmailVerificationRequired,
    RoleView,
    SessionIssued,
    iam_auth_service,
    iam_service,
)
from verity.shared.ids import uuid7

pytestmark = [pytest.mark.isolation, pytest.mark.integration]

TenantModel = TenantMembership | Group | GroupMember | Role | RoleAssignment
TENANT_TABLES: tuple[type[TenantModel], ...] = (
    TenantMembership,
    Group,
    GroupMember,
    Role,
    RoleAssignment,
)


@pytest.fixture(autouse=True)
async def _fresh_state(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> AsyncIterator[None]:
    """``session_scope`` runs on the cached process engine; keep it per-test."""
    await dispose_engine()
    yield
    await dispose_engine()


@dataclass(frozen=True, slots=True)
class TwoTenants:
    a: Workspace
    b: Workspace


NON_ADMIN_ROLE_NAME: str = next(name for name in BUILT_IN_ROLE_KEYS if name != ADMIN_ROLE_NAME)
"""A seeded role that is not Admin, taken from the product's own list.

Three tests here used to name "Auditor" and "Employee", neither of which the
product seeds any more. Deriving the name means these tests follow the built-in
roles instead of pinning names that quietly stop existing."""


def _a_non_admin_role(roles: Sequence[RoleView]) -> RoleView:
    """Any seeded role that is not Admin — the group grant only has to exist."""
    named = sorted(role.name for role in roles)
    role = next((r for r in roles if r.name != ADMIN_ROLE_NAME), None)
    assert role is not None, f"tenant seeded no role other than Admin; got {named}"
    return role


async def _populate(workspace: Workspace, group_name: str) -> None:
    """A group holding the admin, and a built-in role assigned to that group —
    rows on every one of the five tables, written through the real service.

    The role is picked out of what the tenant was actually seeded with rather
    than pinned by name. These tests are about isolation, not about which role,
    and the previous version named "Auditor", which the product stopped seeding:
    a bare ``next()`` over an empty generator turned that into
    ``RuntimeError: coroutine raised StopIteration`` at fixture setup, which
    says nothing about the real cause and took seven tests down with it.
    """
    async with session_scope(workspace.tenant_id) as session:
        group = await iam_service.create_group(
            session,
            tenant_id=workspace.tenant_id,
            actor_membership_id=workspace.membership_id,
            name=group_name,
        )
        await iam_service.add_group_member(
            session,
            tenant_id=workspace.tenant_id,
            actor_membership_id=workspace.membership_id,
            group_id=group.id,
            membership_id=workspace.membership_id,
        )
        roles = await iam_service.list_roles(session, tenant_id=workspace.tenant_id)
        granted = _a_non_admin_role(roles)
        await iam_service.create_assignment(
            session,
            tenant_id=workspace.tenant_id,
            actor_membership_id=workspace.membership_id,
            role_id=granted.id,
            assignee_type="group",
            assignee_id=group.id,
        )


@pytest.fixture
async def tenants() -> TwoTenants:
    """Two signed-up tenants, each with memberships, a group, five built-in
    roles, and role assignments (the admin's plus a group grant)."""
    a = await signup_workspace(company="Alpha Compliance", email="founder@alpha.example")
    b = await signup_workspace(company="Bravo Assurance", email="founder@bravo.example")
    await _populate(a, "Alpha Engineering")
    await _populate(b, "Bravo Operations")
    return TwoTenants(a=a, b=b)


async def _count(session: AsyncSession, model: type[Base]) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar_one()


# ---------------------------------------------------------------------------
# 6.1 — lists and by-id reads from an A session touch nothing of B
# ---------------------------------------------------------------------------


async def test_an_a_session_lists_only_a_rows_on_every_tenant_table(
    tenants: TwoTenants,
) -> None:
    """No WHERE clause anywhere: the policy, not the query, bounds every row set."""
    async with session_scope(tenants.a.tenant_id) as session:
        for model in TENANT_TABLES:
            owners = list((await session.execute(select(model.tenant_id))).scalars())
            assert owners, f"{model.__name__}: the seed should have written rows"
            assert set(owners) == {tenants.a.tenant_id}, model.__name__


async def test_a_b_row_reads_as_absent_by_id_not_forbidden(tenants: TwoTenants) -> None:
    """404-not-403 at the API is this database fact: the row simply is not there."""
    async with session_scope(tenants.a.tenant_id) as session:
        assert await session.get(TenantMembership, tenants.b.membership_id) is None

    async with session_scope(tenants.a.tenant_id) as session:
        with pytest.raises(NotFound):
            await iam_service.disable_member(
                session,
                tenant_id=tenants.a.tenant_id,
                actor_membership_id=tenants.a.membership_id,
                membership_id=tenants.b.membership_id,
            )


async def test_an_unbound_session_sees_nothing_on_any_tenant_table(
    tenants: TwoTenants,
) -> None:
    """Fail closed: no tenant bound, not provider plane — zero rows, no error."""
    async with session_scope(None) as session:
        for model in TENANT_TABLES:
            assert await _count(session, model) == 0, model.__name__


# ---------------------------------------------------------------------------
# 6.2 — one person in both tenants: the wall runs between workspaces
# ---------------------------------------------------------------------------


async def test_a_user_in_both_tenants_cannot_see_their_own_b_membership(
    tenants: TwoTenants,
) -> None:
    """The founder of A is invited into B and accepts. Bound to A, the person's
    own B membership — and everything reachable through it — does not exist."""
    invited = await invite_directly(
        tenants.b,
        email=tenants.a.email,
        full_name="Alpha Founder",
        role_name=NON_ADMIN_ROLE_NAME,
    )
    await iam_auth_service.accept_invitation(token=invited.invite_token)

    shared_user_id = None
    async with session_scope(tenants.a.tenant_id) as session:
        memberships = (await session.execute(select(TenantMembership))).scalars().all()
        mine = [m for m in memberships if m.tenant_id == tenants.a.tenant_id]
        assert {m.tenant_id for m in memberships} == {tenants.a.tenant_id}
        shared_user_id = next(m.user_id for m in mine if m.id == tenants.a.membership_id)
        # The person's own rows, addressed directly, still answer only for A.
        own_rows = (
            (
                await session.execute(
                    select(TenantMembership).where(TenantMembership.user_id == shared_user_id)
                )
            )
            .scalars()
            .all()
        )
        assert [row.id for row in own_rows] == [tenants.a.membership_id]

    # Both memberships exist — the identity plane can see them; tenant A cannot.
    async with provider_session_scope() as session:
        all_rows = (
            (
                await session.execute(
                    select(TenantMembership).where(TenantMembership.user_id == shared_user_id)
                )
            )
            .scalars()
            .all()
        )
        assert {row.tenant_id for row in all_rows} == {
            tenants.a.tenant_id,
            tenants.b.tenant_id,
        }


# ---------------------------------------------------------------------------
# 6.3 — WITH CHECK refuses writes carrying the wrong tenant
# ---------------------------------------------------------------------------


async def test_a_write_carrying_tenant_b_is_refused_by_with_check(
    tenants: TwoTenants,
) -> None:
    """Forgeries from an A-bound session, including the cross-tenant
    (group_in_A, membership_in_B) pair the denormalised tenant_id exists for."""
    async with session_scope(tenants.a.tenant_id) as session:
        a_group_id = (await session.execute(select(Group.id).limit(1))).scalar_one()
        a_role_id = (await session.execute(select(Role.id).limit(1))).scalar_one()

    forgeries = (
        Group(id=uuid7(), tenant_id=tenants.b.tenant_id, name="Forged"),
        TenantMembership(
            id=uuid7(),
            tenant_id=tenants.b.tenant_id,
            user_id=uuid.uuid4(),
            status="invited",
        ),
        GroupMember(
            id=uuid7(),
            tenant_id=tenants.b.tenant_id,
            group_id=a_group_id,
            tenant_membership_id=tenants.b.membership_id,
        ),
        RoleAssignment(
            id=uuid7(),
            tenant_id=tenants.b.tenant_id,
            role_id=a_role_id,
            assignee_type="membership",
            assignee_id=tenants.b.membership_id,
        ),
    )

    async def forge(instance: Base) -> None:
        async with session_scope(tenants.a.tenant_id) as session:
            session.add(instance)
            await session.flush()

    for instance in forgeries:
        with pytest.raises(DBAPIError, match="row-level security"):
            await forge(instance)


# ---------------------------------------------------------------------------
# 6.4 — the MFA policy holds at the session boundary
# ---------------------------------------------------------------------------


async def test_an_admin_without_totp_never_obtains_a_session(tenants: TwoTenants) -> None:
    """A fresh signup's founder holds Admin and is unenrolled: every login stops
    at the enrollment challenge, and the challenge opens no session-consuming
    dependency."""
    outcome = await iam_auth_service.signup(
        company_name="Charlie Governance",
        full_name="Charlie Founder",
        email="founder@charlie.example",
        password=SIGNUP_PASSWORD,
        accept_terms=True,
    )
    assert isinstance(outcome, EmailVerificationRequired)
    # MFA is off by default; require it so an admin without TOTP is actually gated.
    await set_require_admin_mfa(await tenant_id_for("founder@charlie.example"))
    # Verifying the email is what opens enrollment — still no session.
    challenge = await verify_signup_email("founder@charlie.example")
    assert challenge.next_step == "mfa_enrollment_required"

    retry = await iam_auth_service.login(email="founder@charlie.example", password=SIGNUP_PASSWORD)
    assert isinstance(retry, ChallengeIssued)
    assert retry.next_step == "mfa_enrollment_required"

    # The challenge is not a session: the session decoder refuses it, so
    # get_current_principal (which every tenant route depends on) refuses it.
    with pytest.raises(InvalidToken):
        decode_token(retry.challenge_token, expected_typ="session")


async def test_a_non_admin_logs_in_without_totp(tenants: TwoTenants) -> None:
    """Decision 19: TOTP is required for Admin memberships; everyone else is
    password-only in Week 1."""
    invited = await invite_directly(
        tenants.a,
        email="employee@alpha.example",
        full_name="Plain Employee",
        role_name=NON_ADMIN_ROLE_NAME,
    )
    await iam_auth_service.accept_invitation(
        token=invited.invite_token, full_name="Plain Employee", password=INVITEE_PASSWORD
    )

    outcome = await iam_auth_service.login(
        email="employee@alpha.example", password=INVITEE_PASSWORD
    )
    assert isinstance(outcome, SessionIssued)
    claims = decode_token(outcome.token, expected_typ="session", expected_plane="tenant")
    assert claims.subject is not None
    assert outcome.principal.tenant_id == tenants.a.tenant_id
