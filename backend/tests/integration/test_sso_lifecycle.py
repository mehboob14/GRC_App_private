"""Phase D: just in time provisioning, the directory sync with its group to role map, and
back-channel logout. Keycloak is the in-process fake from tests/unit/test_sso_setup.py."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from pydantic import SecretStr
from sqlalchemy import select

from tests.support.documents import client
from tests.support.iam import Workspace, signup_workspace, tenant_session_headers
from tests.unit.test_sso_setup import _FakeKeycloak
from verity.core.config import Settings, get_settings
from verity.core.db import dispose_engine, provider_session_scope, session_scope
from verity.main import create_app
from verity.modules.audit.models import AuditLog
from verity.modules.iam import keycloak_admin, sso, sso_setup, sso_sync
from verity.modules.iam.models import RoleAssignment, TenantMembership, User
from verity.modules.iam.service import SessionIssued, iam_auth_service, iam_service

pytestmark = [pytest.mark.integration]

DEFAULT_ROLE = "Engineering Lead"
MAPPED_ROLE = "Security Officer"


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
def keycloak(monkeypatch: pytest.MonkeyPatch) -> _FakeKeycloak:
    fake = _FakeKeycloak()
    fake.orgs["acme"] = {"alias": "acme", "id": "org-acme", "domains": []}
    configured = get_settings().model_copy(
        update={
            "oidc": get_settings().oidc.model_copy(
                update={
                    "issuer_url": "http://kc.test/realms/verity",
                    "admin_client_secret": SecretStr("admin-secret"),
                }
            )
        }
    )
    monkeypatch.setattr(keycloak_admin, "get_settings", lambda: configured)
    admin = keycloak_admin.KeycloakAdmin(transport=httpx.MockTransport(fake))
    monkeypatch.setattr(sso_setup.sso_setup_service, "_admin", admin)
    monkeypatch.setattr(sso_sync.sso_sync_service, "_admin", admin)
    return fake


async def _roles(ws: Workspace) -> dict[str, uuid.UUID]:
    async with session_scope(ws.tenant_id) as session:
        return {r.name: r.id for r in await iam_service.list_roles(session, tenant_id=ws.tenant_id)}


async def _call(app: FastAPI, ws: Workspace, method: str, path: str, **kw: Any) -> httpx.Response:  # noqa: ANN401
    async with client(app, tenant_session_headers(ws.membership_id)) as admin:
        return await admin.request(method, f"/tenant/security/sso{path}", **kw)


@pytest.fixture
async def acme(app: FastAPI) -> Workspace:
    ws = await signup_workspace(company="Acme Ltd", email="admin@acme.example")
    roles = await _roles(ws)
    body = {"organization_alias": "acme", "domains": ["acme.example"], "enabled": True}
    assert (await _call(app, ws, "PUT", "", json=body)).status_code == 200
    assert (await _call(app, ws, "POST", "/domains/acme.example/verify")).status_code == 200
    no_role = await _call(app, ws, "PUT", "", json={**body, "jit_enabled": True})
    assert no_role.status_code == 422, "provisioning needs the role new people get"
    as_admin = {**body, "jit_enabled": True, "default_role_id": str(roles["Admin"])}
    assert (await _call(app, ws, "PUT", "", json=as_admin)).status_code == 422
    on = {**body, "jit_enabled": True, "default_role_id": str(roles[DEFAULT_ROLE])}
    assert (await _call(app, ws, "PUT", "", json=on)).status_code == 200
    return ws


def _arriving(email: str, subject: str, **kw: Any) -> sso.SsoIdentity:  # noqa: ANN401
    fields: dict[str, Any] = {
        "issuer": "http://kc.test/realms/verity",
        "subject": subject,
        "email": email,
        "email_verified": True,
        "name": "Pat Person",
        "organizations": ["acme"],
        "idp": None,
    }
    return sso.SsoIdentity(**{**fields, **kw})


async def _role_names(ws: Workspace, membership_id: uuid.UUID) -> dict[str, str | None]:
    roles = {v: k for k, v in (await _roles(ws)).items()}
    async with session_scope(ws.tenant_id) as session:
        rows = (
            await session.execute(
                select(RoleAssignment).where(RoleAssignment.assignee_id == membership_id)
            )
        ).scalars()
        return {roles[r.role_id]: r.source for r in rows}


async def _membership(ws: Workspace, email: str) -> TenantMembership:
    async with session_scope(ws.tenant_id) as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        return (
            await session.execute(
                select(TenantMembership).where(TenantMembership.user_id == user.id)
            )
        ).scalar_one()


async def test_a_first_sign_in_through_the_organization_creates_the_member(
    acme: Workspace,
) -> None:
    signed = await iam_auth_service.sso_sign_in(_arriving("pat@acme.example", "kc-pat"))
    assert isinstance(signed, SessionIssued)
    assert signed.principal.tenant_id == acme.tenant_id
    assert await _role_names(acme, signed.principal.membership_id) == {DEFAULT_ROLE: None}

    # Only through the workspace's organization, for a verified email in a proven domain.
    for identity, code in [
        (_arriving("sam@acme.example", "kc-sam", email_verified=False), "unverified"),
        (_arriving("sam@elsewhere.example", "kc-sam"), "no_account"),
        (_arriving("sam@acme.example", "kc-sam", organizations=[]), "no_account"),
    ]:
        with pytest.raises(sso.SsoFailed) as refused:
            await iam_auth_service.sso_sign_in(identity)
        assert refused.value.code == code

    async with provider_session_scope() as session:
        written = {
            r.object_type
            for r in (
                await session.execute(select(AuditLog).where(AuditLog.actor_type == "system"))
            ).scalars()
        }
    assert {"user", "user_identity", "tenant_membership", "role_assignment"} <= written


async def test_the_sync_follows_the_organization_and_its_groups(
    app: FastAPI, acme: Workspace, keycloak: _FakeKeycloak
) -> None:
    roles = await _roles(acme)
    mapped = await _call(
        app,
        acme,
        "POST",
        "/groups",
        json={"group_name": "engineering", "role_id": str(roles[MAPPED_ROLE])},
    )
    assert mapped.status_code == 200, mapped.text
    assert [g["group_name"] for g in mapped.json()["group_roles"]] == ["engineering"]

    # The admin is linked to Keycloak too, so the sync governs them.
    admin = await iam_auth_service.sso_sign_in(_arriving("admin@acme.example", "kc-admin"))
    assert isinstance(admin, SessionIssued)

    pat = {
        "id": "kc-pat",
        "email": "pat@acme.example",
        "emailVerified": True,
        "enabled": True,
        "firstName": "Pat",
        "lastName": "Person",
    }
    keycloak.members["org-acme"] = [pat, {**pat, "id": "kc-admin", "email": "admin@acme.example"}]
    keycloak.groups["kc-pat"] = [{"name": "engineering", "path": "/engineering"}]

    first = await _call(app, acme, "POST", "/sync")
    assert first.status_code == 200, first.text
    assert first.json() | {"skipped": None} == {
        "skipped": None,
        "created": 1,
        "disabled": 0,
        "granted": 1,
        "revoked": 0,
        "kept": 0,
    }
    pat_m = await _membership(acme, "pat@acme.example")
    assert await _role_names(acme, pat_m.id) == {DEFAULT_ROLE: None, MAPPED_ROLE: "sso_group"}
    again = (await _call(app, acme, "POST", "/sync")).json()
    assert again["created"] == again["granted"] == 0, "a second run changes nothing"

    # Leaving the group takes back only what the group gave.
    keycloak.groups["kc-pat"] = []
    assert (await _call(app, acme, "POST", "/sync")).json()["revoked"] == 1
    assert await _role_names(acme, pat_m.id) == {DEFAULT_ROLE: None}

    # An empty organization is a broken read, not everyone leaving: nothing changes.
    keycloak.members["org-acme"] = []
    assert (await _call(app, acme, "POST", "/sync")).json()["skipped"] == "empty"

    # Leaving the organization disables the membership; the last Admin is kept.
    keycloak.members["org-acme"] = [{**pat, "id": "kc-other", "email": "x@elsewhere.example"}]
    gone = (await _call(app, acme, "POST", "/sync")).json()
    assert (gone["disabled"], gone["kept"]) == (1, 1)
    assert (await _membership(acme, "pat@acme.example")).status == "disabled"
    assert (await _membership(acme, "admin@acme.example")).status == "active"
    async with provider_session_scope() as session:
        reasons = [
            (r.after or {}).get("reason")
            for r in (
                await session.execute(
                    select(AuditLog).where(
                        AuditLog.object_type == "tenant_membership", AuditLog.object_id == pat_m.id
                    )
                )
            ).scalars()
        ]
    assert "left the organization in Keycloak" in reasons
    assert (await _call(app, acme, "GET", "")).json()["synced_at"] is not None


async def test_back_channel_logout_ends_the_persons_sessions(app: FastAPI, acme: Workspace) -> None:
    signed = await iam_auth_service.sso_sign_in(_arriving("pat@acme.example", "kc-pat"))
    assert isinstance(signed, SessionIssued)
    headers = {"Authorization": f"Bearer {signed.token}"}
    async with client(app, headers) as pat:
        assert (await pat.get("/auth/me")).status_code == 200
        await iam_auth_service.sso_backchannel_logout("kc-pat")
        assert (await pat.get("/auth/me")).status_code == 401
        bad = await pat.post(
            "/auth/sso/backchannel-logout",
            content="logout_token=not-a-token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert bad.status_code == 400
