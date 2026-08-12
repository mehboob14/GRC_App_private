"""Members, groups, roles, and assignments through the real app — permission
gates, 403-vs-404 semantics, idempotent invites, and the audit trail, with no
dependency overrides. The caller is a real signed-up admin whose session token
is validated against the database on every request.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from tests.support.iam import (
    INVITEE_PASSWORD,
    Workspace,
    invite_directly,
    signup_workspace,
    tenant_session_headers,
)
from verity.core.config import Settings
from verity.core.db import dispose_engine, get_sessionmaker, provider_session_scope
from verity.core.rls import bind_tenant_context
from verity.main import create_app
from verity.modules.audit.models import AuditLog
from verity.modules.audit.service import audit_service
from verity.modules.iam.models import RoleAssignment
from verity.modules.iam.service import iam_auth_service, iam_service

pytestmark = pytest.mark.integration

MEMBERS_URL = "/api/v1/members"
INVITE_URL = "/api/v1/members/invite"
GROUPS_URL = "/api/v1/groups"
ROLES_URL = "/api/v1/roles"
TENANT_URL = "/api/v1/tenant"

MEMBER_FIELDS = {
    "membership_id",
    "user_id",
    "full_name",
    "email",
    "status",
    "role_names",
    "group_names",
    "mfa_enabled",
}
ALL_WEEK1_KEYS = {
    "tenant:read",
    "members:read",
    "members:invite",
    "members:disable",
    "groups:read",
    "groups:manage",
    "roles:read",
    "roles:manage",
    "audit:read",
}


@pytest.fixture(autouse=True)
async def _clean_state(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> AsyncIterator[None]:
    await dispose_engine()
    yield
    await dispose_engine()


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


@pytest.fixture
async def workspace() -> Workspace:
    return await signup_workspace()


@pytest.fixture
def admin_headers(workspace: Workspace) -> dict[str, str]:
    return tenant_session_headers(workspace.membership_id)


async def _accepted_employee(
    workspace: Workspace, *, email: str = "employee@acme.example"
) -> uuid.UUID:
    """An invited-and-accepted Employee membership in the workspace."""
    invited = await invite_directly(
        workspace, email=email, full_name="Plain Employee", role_name="Employee"
    )
    await iam_auth_service.accept_invitation(
        token=invited.invite_token, full_name="Plain Employee", password=INVITEE_PASSWORD
    )
    return invited.member.membership_id


async def _role_id(client: httpx.AsyncClient, headers: dict[str, str], name: str) -> str:
    roles = (await client.get(ROLES_URL, headers=headers)).json()
    return str(next(role["id"] for role in roles if role["name"] == name))


async def _stream(tenant_id: uuid.UUID) -> list[AuditLog]:
    async with provider_session_scope() as session:
        entries, _ = await audit_service.list_page(session, tenant_id=tenant_id, limit=200)
    return entries


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


async def test_the_members_list_carries_roles_groups_and_mfa(
    client: httpx.AsyncClient, workspace: Workspace, admin_headers: dict[str, str]
) -> None:
    await _accepted_employee(workspace)
    response = await client.get(MEMBERS_URL, headers=admin_headers)
    assert response.status_code == 200
    members = {member["email"]: member for member in response.json()}
    assert set(members) == {workspace.email, "employee@acme.example"}
    for member in members.values():
        assert set(member) >= MEMBER_FIELDS

    assert members[workspace.email]["role_names"] == ["Admin"]
    assert members[workspace.email]["mfa_enabled"] is True
    assert members["employee@acme.example"]["role_names"] == ["Employee"]
    assert members["employee@acme.example"]["mfa_enabled"] is False
    assert members["employee@acme.example"]["status"] == "active"


async def test_invite_is_idempotent_and_an_active_member_is_409(
    client: httpx.AsyncClient, workspace: Workspace, admin_headers: dict[str, str]
) -> None:
    employee_role = await _role_id(client, admin_headers, "Employee")
    body = {"email": "new@acme.example", "full_name": "New Member", "role_id": employee_role}

    first = await client.post(INVITE_URL, json=body, headers=admin_headers)
    assert first.status_code == 201
    assert first.json()["member"]["status"] == "invited"
    assert first.json()["invite_token"]
    assert "/accept-invite?token=" in first.json()["accept_url"]

    # Re-inviting a pending membership re-issues the token, never a second row.
    again = await client.post(INVITE_URL, json=body, headers=admin_headers)
    assert again.status_code == 201
    assert again.json()["member"]["membership_id"] == first.json()["member"]["membership_id"]
    assert len((await client.get(MEMBERS_URL, headers=admin_headers)).json()) == 2

    # An active membership is a conflict, not a re-invite.
    await client.post(
        "/api/v1/auth/invitations/accept",
        json={
            "token": again.json()["invite_token"],
            "full_name": "New Member",
            "password": INVITEE_PASSWORD,
        },
    )
    conflict = await client.post(INVITE_URL, json=body, headers=admin_headers)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "already_member"


async def test_the_invite_window_lands_on_the_role_assignment(
    client: httpx.AsyncClient, workspace: Workspace, admin_headers: dict[str, str]
) -> None:
    """The guest-auditor path: the optional body window time-boxes the grant."""
    auditor_role = await _role_id(client, admin_headers, "Auditor")
    response = await client.post(
        INVITE_URL,
        json={
            "email": "guest@auditors.example",
            "full_name": "Guest Auditor",
            "role_id": auditor_role,
            "valid_from": "2026-08-12",
            "valid_until": "2026-09-11",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    membership_id = uuid.UUID(response.json()["member"]["membership_id"])

    async with provider_session_scope() as session:
        assignment = (
            (
                await session.execute(
                    select(RoleAssignment).where(RoleAssignment.assignee_id == membership_id)
                )
            )
            .scalars()
            .one()
        )
    assert str(assignment.valid_from) == "2026-08-12"
    assert str(assignment.valid_until) == "2026-09-11"

    inverted = await client.post(
        INVITE_URL,
        json={
            "email": "second-guest@auditors.example",
            "full_name": "Second Guest",
            "role_id": auditor_role,
            "valid_from": "2026-09-11",
            "valid_until": "2026-08-12",
        },
        headers=admin_headers,
    )
    assert inverted.status_code == 422


async def test_disable_revokes_the_session_and_reinvite_reactivates(
    client: httpx.AsyncClient, workspace: Workspace, admin_headers: dict[str, str]
) -> None:
    membership_id = await _accepted_employee(workspace)
    employee_headers = tenant_session_headers(membership_id)

    # A live token works until the row says otherwise (decision 17).
    assert (await client.get(TENANT_URL, headers=employee_headers)).status_code == 200

    disabled = await client.post(f"{MEMBERS_URL}/{membership_id}/disable", headers=admin_headers)
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"
    assert (await client.get(TENANT_URL, headers=employee_headers)).status_code == 401, (
        "enforcement is per-request database state, not token validity"
    )

    # Re-inviting the disabled membership is a reactivation, audited as update.
    employee_role = await _role_id(client, admin_headers, "Employee")
    revived = await client.post(
        INVITE_URL,
        json={
            "email": "employee@acme.example",
            "full_name": "Plain Employee",
            "role_id": employee_role,
        },
        headers=admin_headers,
    )
    assert revived.status_code == 201
    assert revived.json()["member"]["membership_id"] == str(membership_id)
    assert revived.json()["member"]["status"] == "invited"

    updates = [
        entry
        for entry in await _stream(workspace.tenant_id)
        if entry.object_type == "tenant_membership" and entry.action == "update"
    ]
    assert any(
        entry.before
        and entry.before.get("status") == "disabled"
        and entry.after
        and entry.after.get("status") == "invited"
        for entry in updates
    ), "the reactivation is an update with before/after, not a create"


async def test_put_member_roles_replaces_the_direct_role(
    client: httpx.AsyncClient, workspace: Workspace, admin_headers: dict[str, str]
) -> None:
    membership_id = await _accepted_employee(workspace)
    manager_role = await _role_id(client, admin_headers, "Compliance Manager")
    response = await client.put(
        f"{MEMBERS_URL}/{membership_id}/roles",
        json={"role_id": manager_role},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["role_names"] == ["Compliance Manager"]


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------


async def test_groups_hold_memberships_and_refuse_user_ids(
    client: httpx.AsyncClient, workspace: Workspace, admin_headers: dict[str, str]
) -> None:
    membership_id = await _accepted_employee(workspace)
    created = await client.post(GROUPS_URL, json={"name": "Engineering"}, headers=admin_headers)
    assert created.status_code == 201
    group_id = created.json()["id"]

    added = await client.post(
        f"{GROUPS_URL}/{group_id}/members",
        json={"membership_id": str(membership_id)},
        headers=admin_headers,
    )
    assert added.status_code == 200
    assert added.json()["member_count"] == 1
    assert added.json()["member_ids"] == [str(membership_id)]

    # A users.id is not a membership in this tenant: absent, not forbidden.
    members = {m["email"]: m for m in (await client.get(MEMBERS_URL, headers=admin_headers)).json()}
    user_id = members["employee@acme.example"]["user_id"]
    refused = await client.post(
        f"{GROUPS_URL}/{group_id}/members",
        json={"membership_id": user_id},
        headers=admin_headers,
    )
    assert refused.status_code == 404

    duplicate_name = await client.post(
        GROUPS_URL, json={"name": "Engineering"}, headers=admin_headers
    )
    assert duplicate_name.status_code == 409
    assert duplicate_name.json()["error"]["code"] == "name_conflict"

    listed = (await client.get(GROUPS_URL, headers=admin_headers)).json()
    assert [group["name"] for group in listed] == ["Engineering"]
    assert members["employee@acme.example"]["group_names"] == ["Engineering"], (
        "the members list mirrors the group membership"
    )


# ---------------------------------------------------------------------------
# Roles and assignments
# ---------------------------------------------------------------------------


async def test_admin_lists_every_key_and_built_ins_refuse_delete(
    client: httpx.AsyncClient, workspace: Workspace, admin_headers: dict[str, str]
) -> None:
    response = await client.get(ROLES_URL, headers=admin_headers)
    assert response.status_code == 200
    roles = {role["name"]: role for role in response.json()}
    assert set(roles) == {"Admin", "Compliance Manager", "Control Owner", "Employee", "Auditor"}
    assert all(role["built_in"] for role in roles.values())
    # Decision 13: Admin's bundle is every key that exists, resolved at read time.
    assert set(roles["Admin"]["permission_keys"]) == ALL_WEEK1_KEYS
    assert roles["Admin"]["assignment_count"] == 1

    refused = await client.delete(f"{ROLES_URL}/{roles['Employee']['id']}", headers=admin_headers)
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "built_in_role_immutable"


async def test_a_custom_role_grants_and_revokes_permissions_live(
    client: httpx.AsyncClient, workspace: Workspace, admin_headers: dict[str, str]
) -> None:
    membership_id = await _accepted_employee(workspace)
    employee_headers = tenant_session_headers(membership_id)

    # Employee holds tenant:read only: the flat check refuses with a stable code.
    denied = await client.get(GROUPS_URL, headers=employee_headers)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "permission_denied"

    unknown_key = await client.post(
        ROLES_URL,
        json={"name": "Analyst", "permission_keys": ["groups:read", "widgets:fly"]},
        headers=admin_headers,
    )
    assert unknown_key.status_code == 422

    created = await client.post(
        ROLES_URL,
        json={"name": "Analyst", "permission_keys": ["groups:read", "roles:read"]},
        headers=admin_headers,
    )
    assert created.status_code == 201
    role_id = created.json()["id"]
    assert created.json()["built_in"] is False
    assert created.json()["permission_keys"] == ["groups:read", "roles:read"]

    assigned = await client.post(
        f"{ROLES_URL}/{role_id}/assignments",
        json={"assignee_type": "membership", "assignee_id": str(membership_id)},
        headers=admin_headers,
    )
    assert assigned.status_code == 201
    assignment_id = assigned.json()["id"]

    duplicate = await client.post(
        f"{ROLES_URL}/{role_id}/assignments",
        json={"assignee_type": "membership", "assignee_id": str(membership_id)},
        headers=admin_headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "duplicate_assignment"

    # The grant is live on the next request — no re-login, no cache.
    assert (await client.get(GROUPS_URL, headers=employee_headers)).status_code == 200

    removed = await client.delete(
        f"{ROLES_URL}/{role_id}/assignments/{assignment_id}", headers=admin_headers
    )
    assert removed.status_code == 204
    assert (await client.get(GROUPS_URL, headers=employee_headers)).status_code == 403

    deleted = await client.delete(f"{ROLES_URL}/{role_id}", headers=admin_headers)
    assert deleted.status_code == 204


# ---------------------------------------------------------------------------
# 403 vs 404, the tenant summary, and the same-transaction audit rule
# ---------------------------------------------------------------------------


async def test_no_permission_is_403_and_cross_tenant_is_404(
    client: httpx.AsyncClient, workspace: Workspace, admin_headers: dict[str, str]
) -> None:
    """The flat check answers 403; an identifier from another tenant — even a
    real one — reads as absent, because a 403 would confirm it exists."""
    membership_id = await _accepted_employee(workspace)
    employee_headers = tenant_session_headers(membership_id)

    other = await signup_workspace(company="Bravo Assurance", email="founder@bravo.example")

    forbidden = await client.post(
        f"{MEMBERS_URL}/{membership_id}/disable", headers=employee_headers
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "permission_denied"

    for url in (
        f"{MEMBERS_URL}/{other.membership_id}/disable",
        f"{MEMBERS_URL}/{uuid.uuid4()}/disable",
    ):
        absent = await client.post(url, headers=admin_headers)
        assert absent.status_code == 404, url
        assert absent.json()["error"]["code"] == "not_found"


async def test_the_tenant_summary_serves_the_frontend_contract(
    client: httpx.AsyncClient, workspace: Workspace, admin_headers: dict[str, str]
) -> None:
    """GET /api/v1/tenant carries at least {id, name, slug, status}, where name
    is the display name (trading_name falling back to legal_name)."""
    response = await client.get(TENANT_URL, headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert {"id", "name", "slug", "status"} <= set(body)
    assert body["id"] == str(workspace.tenant_id)
    assert body["name"] == "Acme Compliance"
    assert body["status"] == "active"


async def test_a_rolled_back_invite_leaves_no_audit_row(
    client: httpx.AsyncClient, workspace: Workspace, admin_headers: dict[str, str]
) -> None:
    """Task 4.5: the audit rows ride the same transaction as the change — a
    rollback takes both, never one."""
    baseline = len(await _stream(workspace.tenant_id))

    factory = get_sessionmaker()
    result: Any = None
    async with factory() as session:
        await session.begin()
        await bind_tenant_context(session, workspace.tenant_id)
        result = await iam_service.invite_member(
            session,
            tenant_id=workspace.tenant_id,
            actor_membership_id=workspace.membership_id,
            email="vanishing@acme.example",
            full_name="Vanishing Invite",
            role_id=uuid.UUID(await _role_id(client, admin_headers, "Employee")),
        )
        await session.rollback()
    assert result is not None, "the service call itself succeeded before the rollback"

    assert len(await _stream(workspace.tenant_id)) == baseline
    members = (await client.get(MEMBERS_URL, headers=admin_headers)).json()
    assert [member["email"] for member in members] == [workspace.email]
