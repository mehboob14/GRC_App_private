"""Signing in through Keycloak, Verity side: who the person is and what they get (ADR-0015).

The OIDC exchange itself is covered by tests/unit/test_sso.py; here a validated identity is handed
to the service, the way the callback does after Keycloak.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from tests.support.documents import client
from tests.support.iam import Workspace, signup_workspace, tenant_session_headers
from verity.core.config import Settings
from verity.core.db import dispose_engine, provider_session_scope
from verity.main import create_app
from verity.modules.audit.models import AuditLog
from verity.modules.iam import sso
from verity.modules.iam.service import SelectionIssued, SessionIssued, iam_auth_service

pytestmark = [pytest.mark.integration]

_ID_TOKEN = "id-token-for-sign-out"  # noqa: S105 — a placeholder, not a credential


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
async def workspace() -> Workspace:
    return await signup_workspace(company="Federated Ltd", email="owner@federated.example")


def _identity(subject: str, email: str | None, *, verified: bool = True) -> sso.SsoIdentity:
    return sso.SsoIdentity(
        issuer="http://localhost:8180/realms/verity",
        subject=subject,
        email=email,
        email_verified=verified,
        name="Owner",
        organizations=["federated"],
        acr="1",
        amr=["pwd"],
        id_token=_ID_TOKEN,
    )


async def test_a_verified_email_links_once_then_the_subject_signs_in(
    workspace: Workspace,
) -> None:
    first = await iam_auth_service.sso_sign_in(_identity("kc-1", "OWNER@federated.example"))
    assert isinstance(first, SessionIssued)
    assert first.principal.membership_id == workspace.membership_id
    # Linked by subject now: a changed email at the identity provider still finds the person.
    again = await iam_auth_service.sso_sign_in(_identity("kc-1", "renamed@elsewhere.example"))
    assert isinstance(again, SessionIssued)
    async with provider_session_scope() as session:
        rows = list(
            (
                await session.execute(
                    select(AuditLog).where(AuditLog.object_type.in_(["session", "user_identity"]))
                )
            ).scalars()
        )
    sessions = [r for r in rows if r.object_type == "session" and r.after["method"] == "sso"]
    assert len(sessions) == 2
    assert sessions[0].after["organizations"] == ["federated"]
    assert len([r for r in rows if r.object_type == "user_identity"]) == 1


@pytest.mark.parametrize(
    ("identity", "code"),
    [
        (_identity("kc-2", "nobody@federated.example"), "no_account"),
        (_identity("kc-3", "owner@federated.example", verified=False), "unverified"),
        (_identity("kc-4", None), "no_account"),
    ],
    ids=["unknown email", "unverified email", "no email"],
)
async def test_refusals_are_audited_and_say_what_to_do(
    workspace: Workspace, identity: sso.SsoIdentity, code: str
) -> None:
    with pytest.raises(sso.SsoFailed) as refused:
        await iam_auth_service.sso_sign_in(identity)
    assert refused.value.code == code
    async with provider_session_scope() as session:
        outcomes = [
            r.after["outcome"]
            for r in (
                await session.execute(
                    select(AuditLog).where(AuditLog.object_type == "auth_attempt")
                )
            ).scalars()
        ]
    assert f"sso_{code}" in outcomes


async def test_two_workspaces_give_a_choice_that_skips_totp(
    app: FastAPI, workspace: Workspace
) -> None:
    second = await signup_workspace(company="Second Ltd", email="owner@second.example")
    async with client(app, tenant_session_headers(second.membership_id)) as admin:
        roles = (await admin.get("/roles")).json()
        role = (
            next(r for r in roles if r["name"] == "Viewer")
            if any(r["name"] == "Viewer" for r in roles)
            else roles[0]
        )
        invited = await admin.post(
            "/members/invite",
            json={"email": "owner@federated.example", "full_name": "Owner", "role_id": role["id"]},
        )
    assert invited.status_code == 201, invited.text
    await iam_auth_service.accept_invitation(token=invited.json()["invite_token"])

    outcome = await iam_auth_service.sso_sign_in(_identity("kc-5", "owner@federated.example"))
    assert isinstance(outcome, SelectionIssued)
    chosen = await iam_auth_service.select_workspace(
        selection_token=outcome.selection_token, membership_id=workspace.membership_id
    )
    assert isinstance(chosen, SessionIssued), "the identity provider did MFA; no TOTP step"


async def test_the_routes_are_off_until_configured(app: FastAPI) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test/api/v1"
    ) as anonymous:
        assert (await anonymous.get("/auth/sso/status")).json() == {"enabled": False}
        start = await anonymous.get("/auth/sso/start", params={"email": "a@b.example"})
        assert start.status_code == 401
        callback = await anonymous.get("/auth/sso/callback", params={"state": "nope"})
        assert callback.status_code == 303
        assert callback.headers["location"].endswith("/sso/complete?error=state")


async def test_a_recreated_provider_account_moves_the_link(workspace: Workspace) -> None:
    first = await iam_auth_service.sso_sign_in(_identity("kc-old", "owner@federated.example"))
    assert isinstance(first, SessionIssued)
    again = await iam_auth_service.sso_sign_in(_identity("kc-new", "owner@federated.example"))
    assert isinstance(again, SessionIssued), "same verified email, new subject: the link moves"
    async with provider_session_scope() as session:
        rows = list(
            (
                await session.execute(
                    select(AuditLog).where(AuditLog.object_type == "user_identity")
                )
            ).scalars()
        )
    assert [r.action for r in rows] == ["create", "update"]
    assert rows[1].before == {"subject": "kc-old"}
