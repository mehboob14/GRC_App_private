"""Tenant authentication through the real app: signup, login, MFA, workspaces,
invitations. No dependency overrides anywhere — routes, services, tokens, RLS
policies, and the audit trail are all real. The flows commit rows (a failed
attempt's audit row must outlive its 401), so the clean fixtures truncate as
the owner around each test.

The response shapes asserted here are the frontend contract
(``frontend/src/lib/api/types.ts``): the login union discriminated on
``status``, the invite response carrying the one-time token (decision 15), and
the accept response ``{status: "accepted", tenant_name}``.
"""

from __future__ import annotations

import statistics
import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from tests.support.iam import (
    INVITEE_PASSWORD,
    SIGNUP_PASSWORD,
    invite_directly,
    signup_workspace,
    tenant_session_headers,
)
from tests.support.tenancy import (
    provider_session_headers,
    register_tenant_directly,
    seed_admin,
    totp_code,
)
from verity.core.config import Settings
from verity.core.db import dispose_engine, provider_session_scope
from verity.core.security import decode_token
from verity.main import create_app
from verity.modules.audit.models import AuditLog
from verity.modules.audit.service import audit_service
from verity.modules.iam.models import TenantMembership, User, UserIdentity
from verity.modules.tenancy.service import tenancy_service
from verity.shared.ids import uuid7

pytestmark = pytest.mark.integration

SIGNUP_URL = "/api/v1/auth/signup"
LOGIN_URL = "/api/v1/auth/login"
VERIFY_URL = "/api/v1/auth/mfa/verify"
ENROLL_URL = "/api/v1/auth/mfa/enroll"
CONFIRM_URL = "/api/v1/auth/mfa/confirm"
WORKSPACES_URL = "/api/v1/auth/workspaces"
SELECT_URL = "/api/v1/auth/workspaces/select"
SWITCH_URL = "/api/v1/auth/workspaces/switch"
ACCEPT_URL = "/api/v1/auth/invitations/accept"

PRINCIPAL_FIELDS = {
    "user",
    "membership_id",
    "tenant_id",
    "tenant_name",
    "permissions",
    "role_names",
}
WORKSPACE_FIELDS = {
    "membership_id",
    "tenant_id",
    "tenant_name",
    "tenant_slug",
    "role_name",
    "status",
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


def _signup_body(company: str, email: str, password: str = SIGNUP_PASSWORD) -> dict[str, str]:
    return {
        "company_name": company,
        "full_name": "Founding Admin",
        "email": email,
        "password": password,
    }


async def _stream(tenant_id: uuid.UUID | None) -> list[AuditLog]:
    """One tenant's committed audit stream (or the provider stream), newest first."""
    async with provider_session_scope() as session:
        entries, _ = await audit_service.list_page(session, tenant_id=tenant_id, limit=100)
    return entries


def _attempt_outcomes(entries: list[AuditLog]) -> list[str]:
    return [
        str(entry.after["outcome"])
        for entry in entries
        if entry.object_type == "auth_attempt" and entry.after
    ]


async def _tenant_of_membership(membership_id: str) -> uuid.UUID:
    async with provider_session_scope() as session:
        row = await session.get(TenantMembership, uuid.UUID(membership_id))
        assert row is not None
        return row.tenant_id


async def _tenant_status(tenant_id: uuid.UUID) -> str:
    async with provider_session_scope() as session:
        return (await tenancy_service.get_tenant(session, tenant_id)).status


async def _enroll_and_confirm(
    client: httpx.AsyncClient, challenge_token: str
) -> tuple[dict[str, Any], str]:
    """The enrollment leg shared by signup and first-login: returns the
    confirmed (authenticated) body and the TOTP secret."""
    enroll = await client.post(ENROLL_URL, json={"challenge_token": challenge_token})
    assert enroll.status_code == 200
    secret = enroll.json()["secret"]
    confirm = await client.post(
        CONFIRM_URL, json={"challenge_token": challenge_token, "code": totp_code(secret)}
    )
    assert confirm.status_code == 200
    return confirm.json(), secret


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------


async def test_signup_returns_the_enrollment_challenge_and_activates_the_tenant(
    client: httpx.AsyncClient,
) -> None:
    """Decision 10: a self-signup tenant reaches `active` inside the signup
    transaction; decision 19: the first user holds Admin, so no session exists
    until TOTP enrollment is confirmed."""
    response = await client.post(SIGNUP_URL, json=_signup_body("Acme", "founder@acme.example"))
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "mfa_enrollment_required"
    assert body["challenge_token"]
    assert "access_token" not in body, "a password alone must never buy a session"

    tenant_id = await _tenant_of_membership(body["membership_id"])
    assert await _tenant_status(tenant_id) == "active"

    # Every creation is in the new tenant's stream, in the same transaction.
    object_types = {entry.object_type for entry in await _stream(tenant_id)}
    assert {"tenant", "user", "credentials", "tenant_membership", "role", "role_assignment"} <= (
        object_types
    )

    # The federation seam stays empty (spec: "The table is empty after signup").
    async with provider_session_scope() as session:
        seam_rows = (
            await session.execute(select(func.count()).select_from(UserIdentity))
        ).scalar_one()
    assert seam_rows == 0


async def test_full_signup_matches_the_frontend_contract(client: httpx.AsyncClient) -> None:
    signup = await client.post(SIGNUP_URL, json=_signup_body("Acme", "founder@acme.example"))
    body, _secret = await _enroll_and_confirm(client, signup.json()["challenge_token"])

    assert body["status"] == "authenticated"
    assert body["access_token"]
    assert body["expires_at"].endswith("Z")
    assert body["recovery_codes"], "enrollment confirmation mints the recovery codes"

    principal = body["principal"]
    assert set(principal) >= PRINCIPAL_FIELDS
    assert principal["user"]["email"] == "founder@acme.example"
    assert principal["user"]["mfa_enabled"] is True
    assert principal["tenant_name"] == "Acme"
    assert principal["role_names"] == ["Admin"]
    # Decision 13: Admin is every key that exists at check time.
    assert set(principal["permissions"]) == ALL_WEEK1_KEYS

    assert len(body["workspaces"]) == 1
    assert set(body["workspaces"][0]) >= WORKSPACE_FIELDS

    claims = decode_token(body["access_token"], expected_typ="session", expected_plane="tenant")
    assert str(claims.subject) == principal["membership_id"]

    # Secrets never leave the server (spec scenario) — the one deliberate
    # exception is the plaintext recovery codes in this single response.
    for marker in ("password_hash", "mfa_secret", "recovery_codes_encrypted"):
        assert marker not in signup.text
        assert marker not in str(body)


async def test_a_duplicate_email_signup_is_409_with_zero_partial_rows(
    client: httpx.AsyncClient,
) -> None:
    """The email check fails *after* the tenant register write, so a 409 here
    proves the one-transaction rule: nothing survives, including the tenant."""
    first = await client.post(SIGNUP_URL, json=_signup_body("Acme", "founder@acme.example"))
    assert first.status_code == 201

    second = await client.post(SIGNUP_URL, json=_signup_body("Rival Corp", "founder@acme.example"))
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "email_taken"

    async with provider_session_scope() as session:
        tenants, _ = await tenancy_service.list_tenants(session, limit=10)
        users = (await session.execute(select(func.count()).select_from(User))).scalar_one()
        memberships = (
            await session.execute(select(func.count()).select_from(TenantMembership))
        ).scalar_one()
    assert [t.legal_name for t in tenants] == ["Acme"], "no orphan company in the register"
    assert users == 1
    assert memberships == 1


async def test_signup_replays_idempotently_under_the_same_key(
    client: httpx.AsyncClient,
) -> None:
    body = _signup_body("Acme", "founder@acme.example")
    headers = {"Idempotency-Key": "signup-once"}
    first = await client.post(SIGNUP_URL, json=body, headers=headers)
    replay = await client.post(SIGNUP_URL, json=body, headers=headers)
    assert first.status_code == 201
    assert replay.status_code == 201
    assert replay.json()["status"] == "mfa_enrollment_required"
    assert replay.json()["membership_id"] == first.json()["membership_id"]

    async with provider_session_scope() as session:
        tenants, _ = await tenancy_service.list_tenants(session, limit=10)
    assert len(tenants) == 1


async def test_a_weak_password_is_422_with_the_stable_code(client: httpx.AsyncClient) -> None:
    response = await client.post(
        SIGNUP_URL,
        json=_signup_body("Acme", "founder@acme.example", password="short-one"),  # noqa: S106 — deliberately weak
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "weak_password"


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


async def test_unknown_email_matches_wrong_password_in_content_and_wall_time(
    client: httpx.AsyncClient,
) -> None:
    workspace = await signup_workspace()

    async def timed(email: str) -> tuple[float, dict[str, str]]:
        start = time.perf_counter()
        response = await client.post(
            LOGIN_URL, json={"email": email, "password": "not-the-password"}
        )
        elapsed = time.perf_counter() - start
        assert response.status_code == 401
        return elapsed, response.json()["error"]

    await timed("warm-the-dummy-hash@nowhere.example")  # first call builds the dummy hash

    unknown_times, wrong_times = [], []
    for _ in range(3):
        elapsed, unknown_error = await timed("ghost@nowhere.example")
        unknown_times.append(elapsed)
        elapsed, wrong_error = await timed(workspace.email)
        wrong_times.append(elapsed)
        assert unknown_error["code"] == wrong_error["code"]
        assert unknown_error["message"] == wrong_error["message"]

    unknown, wrong = statistics.median(unknown_times), statistics.median(wrong_times)
    # Both paths burn one argon2 verification (~tens of ms); an unknown email
    # that skipped it would return an order of magnitude faster. Loose, no flake.
    assert unknown > wrong / 3
    assert wrong > unknown / 3

    # Decision 3: failures are auth_attempt events; unknown emails carry the
    # reason on the unattributable provider stream, never the address itself.
    provider_outcomes = _attempt_outcomes(await _stream(None))
    tenant_outcomes = _attempt_outcomes(await _stream(workspace.tenant_id))
    assert provider_outcomes.count("failed_password") == 4
    assert tenant_outcomes.count("failed_password") == 3
    attempts = [
        entry
        for entry in await _stream(None) + await _stream(workspace.tenant_id)
        if entry.object_type == "auth_attempt" and entry.after
    ]
    assert attempts
    assert all("ghost" not in str(entry.after) for entry in attempts)
    assert all(workspace.email not in str(entry.after) for entry in attempts), (
        "decision 3: never an email address in an attempt snapshot"
    )


async def test_an_enrolled_admin_gets_a_challenge_and_a_totp_replay_is_refused(
    client: httpx.AsyncClient,
) -> None:
    workspace = await signup_workspace()

    login = await client.post(
        LOGIN_URL, json={"email": workspace.email, "password": SIGNUP_PASSWORD}
    )
    assert login.status_code == 200
    assert login.json()["status"] == "mfa_required"

    # The code the enrollment confirmation consumed is still inside its ±1-step
    # acceptance window — only the persisted counter stands between it and a
    # second session.
    replay = await client.post(
        VERIFY_URL,
        json={
            "challenge_token": login.json()["challenge_token"],
            "code": totp_code(workspace.totp_secret),
        },
    )
    assert replay.status_code == 401
    assert "failed_totp" in _attempt_outcomes(await _stream(workspace.tenant_id))

    # The *next* window's code is fine — the guard is the counter, not a lockout.
    challenge = (
        await client.post(LOGIN_URL, json={"email": workspace.email, "password": SIGNUP_PASSWORD})
    ).json()["challenge_token"]
    fresh = await client.post(
        VERIFY_URL,
        json={
            "challenge_token": challenge,
            "code": totp_code(workspace.totp_secret, step_offset=1),
        },
    )
    assert fresh.status_code == 200
    assert fresh.json()["status"] == "authenticated"


async def test_a_completed_login_writes_a_session_row_in_the_tenant_stream(
    client: httpx.AsyncClient,
) -> None:
    workspace = await signup_workspace()
    login = await client.post(
        LOGIN_URL, json={"email": workspace.email, "password": SIGNUP_PASSWORD}
    )
    verified = await client.post(
        VERIFY_URL,
        json={
            "challenge_token": login.json()["challenge_token"],
            "code": totp_code(workspace.totp_secret, step_offset=1),
        },
    )
    claims = decode_token(
        verified.json()["access_token"], expected_typ="session", expected_plane="tenant"
    )
    sessions = [
        entry
        for entry in await _stream(workspace.tenant_id)
        if entry.object_type == "session" and entry.action == "create"
    ]
    assert claims.jti in {entry.object_id for entry in sessions}, (
        "decision 2: object_id is the token's jti"
    )


# ---------------------------------------------------------------------------
# Invitations — the new-user and existing-user (auditor-two-orgs) paths
# ---------------------------------------------------------------------------


async def test_invite_accept_login_for_a_new_user(client: httpx.AsyncClient) -> None:
    workspace = await signup_workspace()
    invited = await invite_directly(
        workspace, email="employee@acme.example", full_name="Plain Employee", role_name="Employee"
    )
    assert "/accept-invite?token=" in invited.accept_url

    accept = await client.post(
        ACCEPT_URL,
        json={
            "token": invited.invite_token,
            "full_name": "Plain Employee",
            "password": INVITEE_PASSWORD,
        },
    )
    assert accept.status_code == 200
    assert accept.json() == {"status": "accepted", "tenant_name": "Acme Compliance"}

    # Single use: the membership is already active, so a second accept is 409.
    again = await client.post(ACCEPT_URL, json={"token": invited.invite_token})
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "invite_already_accepted"

    login = await client.post(
        LOGIN_URL, json={"email": "employee@acme.example", "password": INVITEE_PASSWORD}
    )
    assert login.status_code == 200
    assert login.json()["status"] == "authenticated", "a non-admin needs no TOTP in Week 1"
    assert login.json()["principal"]["role_names"] == ["Employee"]

    # A new user setting their name on accept is a state change on the global users
    # row and is audited like every other write in that flow (review finding 4).
    user_updates = [
        entry
        for entry in await _stream(workspace.tenant_id)
        if entry.object_type == "user" and entry.action == "update"
    ]
    assert any(
        entry.after is not None and entry.after.get("full_name") == "Plain Employee"
        for entry in user_updates
    )


async def test_logout_is_recorded_as_delete_on_the_session(client: httpx.AsyncClient) -> None:
    """Decisions 2 and 17: sign-out writes a delete/'session' row keyed on the token's
    jti, matching the create written when the session was issued."""
    workspace = await signup_workspace(email="dana@acme.example")
    headers = {"Authorization": f"Bearer {workspace.session_token}"}
    jti = decode_token(workspace.session_token, expected_typ="session", expected_plane="tenant").jti

    response = await client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 204

    deletes = [
        entry
        for entry in await _stream(workspace.tenant_id)
        if entry.object_type == "session" and entry.action == "delete"
    ]
    assert jti in {entry.object_id for entry in deletes}

    unauth = await client.post("/api/v1/auth/logout")
    assert unauth.status_code == 401


async def test_accept_refuses_garbage_tokens_and_weak_passwords(
    client: httpx.AsyncClient,
) -> None:
    workspace = await signup_workspace()
    invited = await invite_directly(
        workspace, email="second@acme.example", full_name="Second", role_name="Employee"
    )

    garbage = await client.post(ACCEPT_URL, json={"token": "not-a-token"})
    assert garbage.status_code == 401
    assert garbage.json()["error"]["code"] == "invalid_invite"

    # A session token is not an invite token (typ matrix at the route).
    wrong_typ = await client.post(ACCEPT_URL, json={"token": workspace.session_token})
    assert wrong_typ.status_code == 401
    assert wrong_typ.json()["error"]["code"] == "invalid_invite"

    weak = await client.post(
        ACCEPT_URL,
        json={"token": invited.invite_token, "full_name": "Second", "password": "short-one"},
    )
    assert weak.status_code == 422
    assert weak.json()["error"]["code"] == "weak_password"

    # None of the refusals consumed the invite.
    accept = await client.post(
        ACCEPT_URL,
        json={"token": invited.invite_token, "full_name": "Second", "password": INVITEE_PASSWORD},
    )
    assert accept.status_code == 200


async def test_an_existing_user_is_invited_into_a_second_tenant_time_boxed(
    client: httpx.AsyncClient,
) -> None:
    """The auditor-two-orgs path: token-only accept, a second membership, and
    the window on the role assignment — then login offers both workspaces."""
    home = await signup_workspace(company="Acme Compliance", email="auditor@firm.example")
    host = await signup_workspace(company="Bravo Assurance", email="founder@bravo.example")

    today = datetime.now(UTC).date()
    invited = await invite_directly(
        host,
        email=home.email,
        full_name="Guest Auditor",
        role_name="Auditor",
        valid_from=today,
        valid_until=today + timedelta(days=30),
    )
    accept = await client.post(ACCEPT_URL, json={"token": invited.invite_token})
    assert accept.status_code == 200
    assert accept.json()["tenant_name"] == "Bravo Assurance"

    login = await client.post(LOGIN_URL, json={"email": home.email, "password": SIGNUP_PASSWORD})
    assert login.status_code == 200
    body = login.json()
    assert body["status"] == "select_workspace"
    assert {w["tenant_name"] for w in body["workspaces"]} == {
        "Acme Compliance",
        "Bravo Assurance",
    }

    by_name = {w["tenant_name"]: w for w in body["workspaces"]}
    # Selecting the Admin home workspace demands the second factor; the guest
    # membership is not an Admin and proceeds straight to a session.
    into_home = await client.post(
        SELECT_URL,
        json={
            "selection_token": body["selection_token"],
            "membership_id": by_name["Acme Compliance"]["membership_id"],
        },
    )
    assert into_home.json()["status"] == "mfa_required"

    into_host = await client.post(
        SELECT_URL,
        json={
            "selection_token": body["selection_token"],
            "membership_id": by_name["Bravo Assurance"]["membership_id"],
        },
    )
    assert into_host.json()["status"] == "authenticated"
    assert into_host.json()["principal"]["role_names"] == ["Auditor"]


async def test_workspace_switch_issues_a_new_session_audited_in_the_target_stream(
    client: httpx.AsyncClient,
) -> None:
    home = await signup_workspace(company="Acme Compliance", email="dual@firm.example")
    host = await signup_workspace(company="Bravo Assurance", email="founder@bravo.example")
    invited = await invite_directly(
        host, email=home.email, full_name="Dual Member", role_name="Employee"
    )
    await client.post(ACCEPT_URL, json={"token": invited.invite_token})

    headers = {"Authorization": f"Bearer {home.session_token}"}
    workspaces = await client.get(WORKSPACES_URL, headers=headers)
    assert workspaces.status_code == 200
    target = next(w for w in workspaces.json() if uuid.UUID(w["tenant_id"]) == host.tenant_id)

    switch = await client.post(
        SWITCH_URL, json={"membership_id": target["membership_id"]}, headers=headers
    )
    assert switch.status_code == 200
    body = switch.json()
    assert body["status"] == "authenticated"
    assert body["access_token"] != home.session_token, "a switch is a new session"
    assert uuid.UUID(body["principal"]["tenant_id"]) == host.tenant_id

    # Decision 2: the switch is create/'session' in the TARGET tenant's stream.
    claims = decode_token(body["access_token"], expected_typ="session", expected_plane="tenant")
    target_sessions = [
        entry for entry in await _stream(host.tenant_id) if entry.object_type == "session"
    ]
    assert claims.jti in {entry.object_id for entry in target_sessions}


async def test_a_provider_created_tenant_activates_when_its_admin_accepts(
    client: httpx.AsyncClient,
) -> None:
    """Decision 10 end to end: register (provider) → admin-invite → accept →
    active. The invited admin then hits the Admin TOTP wall at first login."""
    operator = await seed_admin()
    tenant = await register_tenant_directly(operator.id, "delta")
    assert await _tenant_status(tenant.id) == "provisioning"

    invite = await client.post(
        f"/api/v1/provider/tenants/{tenant.id}/admin-invite",
        json={"email": "admin@delta.example", "full_name": "Delta Admin"},
        headers=provider_session_headers(operator.id),
    )
    assert invite.status_code == 201
    assert invite.json()["member"]["status"] == "invited"
    assert await _tenant_status(tenant.id) == "provisioning", "recorded is not yet active"

    accept = await client.post(
        ACCEPT_URL,
        json={
            "token": invite.json()["invite_token"],
            "full_name": "Delta Admin",
            "password": INVITEE_PASSWORD,
        },
    )
    assert accept.status_code == 200
    assert await _tenant_status(tenant.id) == "active"

    login = await client.post(
        LOGIN_URL, json={"email": "admin@delta.example", "password": INVITEE_PASSWORD}
    )
    assert login.status_code == 200
    assert login.json()["status"] == "mfa_enrollment_required"


# ---------------------------------------------------------------------------
# The role window at login — the guest-auditor expiry (spec: "The membership is
# disabled or outside its window" → 401)
# ---------------------------------------------------------------------------


async def test_a_sole_out_of_window_membership_refuses_login(
    client: httpx.AsyncClient,
) -> None:
    """A new user whose only role assignment has expired must not obtain a session
    with empty roles: login is 401, indistinguishable from an unknown email."""
    host = await signup_workspace(company="Bravo Assurance", email="founder@bravo.example")
    today = datetime.now(UTC).date()
    invited = await invite_directly(
        host,
        email="expired@guest.example",
        full_name="Expired Guest",
        role_name="Auditor",
        valid_from=today - timedelta(days=30),
        valid_until=today - timedelta(days=1),
    )
    accept = await client.post(
        ACCEPT_URL,
        json={
            "token": invited.invite_token,
            "full_name": "Expired Guest",
            "password": INVITEE_PASSWORD,
        },
    )
    assert accept.status_code == 200

    login = await client.post(
        LOGIN_URL, json={"email": "expired@guest.example", "password": INVITEE_PASSWORD}
    )
    assert login.status_code == 401, "an expired sole membership yields no session"
    unknown = await client.post(
        LOGIN_URL, json={"email": "ghost@nowhere.example", "password": INVITEE_PASSWORD}
    )
    assert login.json()["error"]["code"] == unknown.json()["error"]["code"]
    # Decision 3: the refusal is recorded as no_active_membership, never a session.
    assert "no_active_membership" in _attempt_outcomes(await _stream(None))


async def test_an_in_window_sole_membership_still_logs_in(
    client: httpx.AsyncClient,
) -> None:
    """The other side of the guard: an in-window guest still gets a session."""
    host = await signup_workspace(company="Bravo Assurance", email="founder@bravo.example")
    today = datetime.now(UTC).date()
    invited = await invite_directly(
        host,
        email="current@guest.example",
        full_name="Current Guest",
        role_name="Auditor",
        valid_from=today - timedelta(days=1),
        valid_until=today + timedelta(days=30),
    )
    await client.post(
        ACCEPT_URL,
        json={
            "token": invited.invite_token,
            "full_name": "Current Guest",
            "password": INVITEE_PASSWORD,
        },
    )
    login = await client.post(
        LOGIN_URL, json={"email": "current@guest.example", "password": INVITEE_PASSWORD}
    )
    assert login.status_code == 200
    assert login.json()["status"] == "authenticated"
    assert login.json()["principal"]["role_names"] == ["Auditor"]


async def test_login_lists_only_in_window_workspaces(
    client: httpx.AsyncClient,
) -> None:
    """A member in-window in A but expired-only in B is offered A alone: the
    expired workspace is not part of the resolved memberships."""
    a = await signup_workspace(company="Acme Compliance", email="founder-a@acme.example")
    b = await signup_workspace(company="Bravo Assurance", email="founder-b@bravo.example")
    today = datetime.now(UTC).date()

    in_a = await invite_directly(
        a, email="dual@guest.example", full_name="Dual Guest", role_name="Employee"
    )
    await client.post(
        ACCEPT_URL,
        json={
            "token": in_a.invite_token,
            "full_name": "Dual Guest",
            "password": INVITEE_PASSWORD,
        },
    )
    in_b = await invite_directly(
        b,
        email="dual@guest.example",
        full_name="Dual Guest",
        role_name="Auditor",
        valid_from=today - timedelta(days=30),
        valid_until=today - timedelta(days=1),
    )
    assert (await client.post(ACCEPT_URL, json={"token": in_b.invite_token})).status_code == 200

    login = await client.post(
        LOGIN_URL, json={"email": "dual@guest.example", "password": INVITEE_PASSWORD}
    )
    assert login.status_code == 200
    body = login.json()
    assert body["status"] == "authenticated", "only A is usable, so login binds A directly"
    assert {w["tenant_name"] for w in body["workspaces"]} == {"Acme Compliance"}


# ---------------------------------------------------------------------------
# Token matrix at the routes, and the seam's unique key
# ---------------------------------------------------------------------------


async def test_partial_and_foreign_tokens_open_no_tenant_route(
    client: httpx.AsyncClient,
) -> None:
    workspace = await signup_workspace()
    operator = await seed_admin()

    challenge = (
        await client.post(LOGIN_URL, json={"email": workspace.email, "password": SIGNUP_PASSWORD})
    ).json()["challenge_token"]

    # A challenge is not a session.
    refused = await client.get(WORKSPACES_URL, headers={"Authorization": f"Bearer {challenge}"})
    assert refused.status_code == 401
    assert refused.json()["error"]["code"] == "invalid_token"

    # A provider session is authenticated but categorically not a tenant user.
    crossed = await client.get("/api/v1/members", headers=provider_session_headers(operator.id))
    assert crossed.status_code == 403

    # And a tenant session is categorically not an operator.
    crossed_back = await client.get(
        "/api/v1/provider/tenants", headers=tenant_session_headers(workspace.membership_id)
    )
    assert crossed_back.status_code == 403


async def test_the_federation_seam_unique_key_is_provider_scoped() -> None:
    """Task 5.2: ``(provider, external_subject_id)`` refuses a duplicate, so
    Phase 3 has a real seam rather than a table-shaped hope."""
    workspace = await signup_workspace()
    async with provider_session_scope() as session:
        membership = await session.get(TenantMembership, workspace.membership_id)
        assert membership is not None
        user_id = membership.user_id

    async def link(subject: str) -> None:
        async with provider_session_scope() as session:
            session.add(
                UserIdentity(
                    id=uuid7(),
                    user_id=user_id,
                    provider="entra",
                    provider_type="oidc",
                    external_subject_id=subject,
                )
            )
            await session.flush()

    await link("subject-1")
    with pytest.raises(IntegrityError, match="uq_user_identities__provider_subject"):
        await link("subject-1")
