"""A workspace's SSO through Keycloak: settings, organization routing, enforcement (phase B).

The OIDC exchange is covered by tests/unit/test_sso.py; here validated identities are handed to the
service the way the callback does.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from tests.support.documents import client
from tests.support.iam import (
    SIGNUP_PASSWORD,
    Workspace,
    invite_directly,
    signup_workspace,
    tenant_session_headers,
)
from verity.core.config import Settings
from verity.core.db import dispose_engine
from verity.core.errors import AuthenticationRequired, NotFound
from verity.main import create_app
from verity.modules.iam import sso
from verity.modules.iam.service import (
    ChallengeIssued,
    SelectionIssued,
    SessionIssued,
    iam_auth_service,
)

pytestmark = [pytest.mark.integration]

MEMBER_PASSWORD = "Harbour-violet-tram-77"  # noqa: S105 — test credential


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
async def acme() -> Workspace:
    return await signup_workspace(company="Acme Ltd", email="admin@acme.example")


def _identity(email: str, *, orgs: list[str], subject: str | None = None) -> sso.SsoIdentity:
    return sso.SsoIdentity(
        issuer="http://localhost:8180/realms/verity",
        subject=subject or f"kc-{email}",
        email=email,
        email_verified=True,
        name=None,
        organizations=orgs,
    )


async def _put_sso(app: FastAPI, ws: Workspace, **body: Any) -> httpx.Response:  # noqa: ANN401
    async with client(app, tenant_session_headers(ws.membership_id)) as admin:
        return await admin.put("/tenant/security/sso", json=body)


async def _verify(app: FastAPI, ws: Workspace, domain: str) -> httpx.Response:
    async with client(app, tenant_session_headers(ws.membership_id)) as admin:
        return await admin.post(f"/tenant/security/sso/domains/{domain}/verify")


async def _get_sso(app: FastAPI, ws: Workspace) -> Any:  # noqa: ANN401
    async with client(app, tenant_session_headers(ws.membership_id)) as admin:
        return (await admin.get("/tenant/security/sso")).json()


async def test_settings_are_validated_and_unique_across_workspaces(
    app: FastAPI, acme: Workspace
) -> None:
    assert (await _get_sso(app, acme))["configured"] is False
    saved = await _put_sso(
        app,
        acme,
        organization_alias="Acme",
        domains=["@Acme.example", "acme.example"],
        enabled=True,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["organization_alias"] == "acme"
    assert saved.json()["domains"] == ["acme.example"]
    early = await _put_sso(
        app, acme, organization_alias="acme", domains=["acme.example"], enabled=True, enforce=True
    )
    assert early.status_code == 422, "enforcing needs a proven SSO sign in first"
    assert (
        await _put_sso(app, acme, organization_alias="acme", domains=["nope"])
    ).status_code == 422

    # Only a proven domain routes sign in (phase C): typed in alone, it does nothing.
    assert await iam_auth_service.sso_organization_for("Someone@ACME.example") is None
    assert (await _verify(app, acme, "acme.example")).status_code == 200
    assert await iam_auth_service.sso_organization_for("Someone@ACME.example") == "acme"
    assert await iam_auth_service.sso_organization_for("someone@other.example") is None

    other = await signup_workspace(company="Other Ltd", email="admin@other.example")
    same_alias = await _put_sso(app, other, organization_alias="acme", domains=[])
    assert same_alias.status_code == 409
    # A domain Acme only typed in blocks nobody; one Acme proved is refused.
    await _put_sso(app, acme, organization_alias="acme", domains=["acme.example", "typed.example"])
    typed = await _put_sso(app, other, organization_alias="other", domains=["typed.example"])
    assert typed.status_code == 200, typed.text
    proven = await _put_sso(app, other, organization_alias="other", domains=["acme.example"])
    assert proven.status_code == 409


async def test_the_organization_picks_the_workspace_and_proves_the_setup(
    app: FastAPI, acme: Workspace
) -> None:
    # The same person is in a second workspace that has no SSO.
    second = await signup_workspace(company="Second Ltd", email="admin@second.example")
    invited = await invite_directly(
        second, email="admin@acme.example", full_name="Acme Admin", role_name="Admin"
    )
    await iam_auth_service.accept_invitation(token=invited.invite_token)
    await _put_sso(app, acme, organization_alias="acme", domains=["acme.example"], enabled=True)

    through_acme = await iam_auth_service.sso_sign_in(
        _identity("admin@acme.example", orgs=["acme"])
    )
    assert isinstance(through_acme, SessionIssued), "the organization names the workspace"
    assert through_acme.principal.tenant_id == acme.tenant_id
    assert (await _get_sso(app, acme))["verified_at"] is not None

    # Without the organization claim, Acme (SSO on) refuses; the workspace without SSO admits.
    without = await iam_auth_service.sso_sign_in(_identity("admin@acme.example", orgs=[]))
    assert isinstance(without, SessionIssued)
    assert without.principal.tenant_id == second.tenant_id


async def test_a_workspace_choice_after_sso_cannot_reach_a_workspace_it_did_not_allow(
    app: FastAPI, acme: Workspace
) -> None:
    second = await signup_workspace(company="Second Ltd", email="admin@second.example")
    third = await signup_workspace(company="Third Ltd", email="admin@third.example")
    for ws in (second, third):
        invited = await invite_directly(
            ws, email="admin@acme.example", full_name="Acme Admin", role_name="Admin"
        )
        await iam_auth_service.accept_invitation(token=invited.invite_token)
    await _put_sso(app, acme, organization_alias="acme", domains=[], enabled=True)

    choice = await iam_auth_service.sso_sign_in(_identity("admin@acme.example", orgs=[]))
    assert isinstance(choice, SelectionIssued)
    offered = {w.tenant_id for w in choice.workspaces}
    assert offered == {second.tenant_id, third.tenant_id}, "Acme needs its organization"
    with pytest.raises(NotFound):
        await iam_auth_service.select_workspace(
            selection_token=choice.selection_token, membership_id=acme.membership_id
        )


async def test_enforcement_closes_password_sign_in_except_break_glass(
    app: FastAPI, acme: Workspace
) -> None:
    invited = await invite_directly(
        acme, email="member@acme.example", full_name="Member", role_name="Security Officer"
    )
    await iam_auth_service.accept_invitation(
        token=invited.invite_token, full_name="Member", password=MEMBER_PASSWORD
    )
    await _put_sso(app, acme, organization_alias="acme", domains=["acme.example"], enabled=True)
    await iam_auth_service.sso_sign_in(_identity("admin@acme.example", orgs=["acme"]))
    enforced = await _put_sso(
        app, acme, organization_alias="acme", domains=["acme.example"], enabled=True, enforce=True
    )
    assert enforced.status_code == 200, enforced.text

    with pytest.raises(AuthenticationRequired) as refused:
        await iam_auth_service.login(email="member@acme.example", password=MEMBER_PASSWORD)
    assert "single sign on" in refused.value.message
    # The Admin with TOTP enrolled keeps a way in, and always takes the TOTP step.
    admin = await iam_auth_service.login(email="admin@acme.example", password=SIGNUP_PASSWORD)
    assert isinstance(admin, ChallengeIssued)
    assert admin.next_step == "mfa_required"
    # SSO still works for the member.
    member = await iam_auth_service.sso_sign_in(_identity("member@acme.example", orgs=["acme"]))
    assert isinstance(member, SessionIssued)

    # Changing the organization clears the proof, and with it enforcement.
    moved = await _put_sso(
        app,
        acme,
        organization_alias="acme-new",
        domains=["acme.example"],
        enabled=True,
        enforce=True,
    )
    assert moved.status_code == 422
