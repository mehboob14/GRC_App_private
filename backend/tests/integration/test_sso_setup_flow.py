"""Phase C: prove domains, connect an identity provider through Keycloak's Admin API, and hold that
provider to its own workspace. Keycloak is the in-process fake from tests/unit/test_sso_setup.py."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from pydantic import SecretStr
from sqlalchemy import select

from tests.support.documents import client
from tests.support.iam import Workspace, invite_directly, signup_workspace, tenant_session_headers
from tests.unit.test_sso_setup import _FakeKeycloak
from verity.core.config import Settings, get_settings
from verity.core.db import dispose_engine, provider_session_scope
from verity.main import create_app
from verity.modules.audit.models import AuditLog
from verity.modules.iam import keycloak_admin, sso, sso_setup
from verity.modules.iam.service import SessionIssued, iam_auth_service

pytestmark = [pytest.mark.integration]


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
    monkeypatch.setattr(
        sso_setup.sso_setup_service,
        "_admin",
        keycloak_admin.KeycloakAdmin(transport=httpx.MockTransport(fake)),
    )
    return fake


@pytest.fixture
async def acme() -> Workspace:
    return await signup_workspace(company="Acme Ltd", email="admin@acme.example")


async def _call(app: FastAPI, ws: Workspace, method: str, path: str, **kw: Any) -> httpx.Response:  # noqa: ANN401
    async with client(app, tenant_session_headers(ws.membership_id)) as admin:
        return await admin.request(method, f"/tenant/security/sso{path}", **kw)


async def test_prove_connect_and_follow_the_switches(
    app: FastAPI, acme: Workspace, keycloak: _FakeKeycloak, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = await _call(
        app,
        acme,
        "PUT",
        "",
        json={
            "organization_alias": "acme",
            "domains": ["acme.example", "acme.com"],
            "enabled": True,
        },
    )
    assert saved.status_code == 200, saved.text
    view = saved.json()
    assert view["txt_value"].startswith("verity-domain-verification=")

    early = await _call(app, acme, "PUT", "/provider", json={"provider": "okta"})
    assert early.status_code == 422, "a provider needs a proven domain to route to"

    # A real domain is proven by its TXT record; a reserved test domain passes outside production.
    seen: list[str] = []

    async def no_record(name: str) -> list[str]:
        seen.append(name)
        return []

    monkeypatch.setattr(sso_setup, "txt_records", no_record)
    missing = await _call(app, acme, "POST", "/domains/acme.com/verify")
    assert missing.status_code == 422
    assert seen == ["_verity.acme.com"]

    async def published(name: str) -> list[str]:
        return ["some-other-record", view["txt_value"]]

    monkeypatch.setattr(sso_setup, "txt_records", published)
    assert (await _call(app, acme, "POST", "/domains/acme.com/verify")).status_code == 200
    proved = await _call(app, acme, "POST", "/domains/acme.example/verify")
    assert proved.json()["verified_domains"] == ["acme.com", "acme.example"]

    connected = await _call(
        app,
        acme,
        "PUT",
        "/provider",
        json={
            "provider": "okta",
            "okta_domain": "acme.okta.com",
            "client_id": "cid",
            "client_secret": "very-secret-value",
        },
    )
    assert connected.status_code == 200, connected.text
    body = connected.json()
    assert (body["provider"], body["idp_alias"]) == ("okta", "acme-okta")
    assert body["redirect_uri"] == "http://kc.test/realms/verity/broker/acme-okta/endpoint"
    idp = keycloak.idps["acme-okta"]
    assert idp["config"]["clientSecret"] == "very-secret-value"
    assert idp["config"]["issuer"] == "https://acme.okta.com/.well-known/openid-configuration"
    org = keycloak.orgs["acme"]
    assert {d["name"] for d in org["domains"]} == {"acme.com", "acme.example"}
    assert all(d["identityProviderAlias"] == "acme-okta" for d in org["domains"])
    assert keycloak.links[org["id"]] == {"acme-okta"}

    # Switching SSO off turns the provider off in Keycloak too; a dropped domain stops routing.
    off = await _call(
        app,
        acme,
        "PUT",
        "",
        json={"organization_alias": "acme", "domains": ["acme.com"], "enabled": False},
    )
    assert off.status_code == 200, off.text
    assert keycloak.idps["acme-okta"]["enabled"] is False
    assert [d["name"] for d in keycloak.orgs["acme"]["domains"]] == ["acme.com"]
    assert off.json()["verified_domains"] == ["acme.com"]

    async with provider_session_scope() as session:
        rows = list(
            (
                await session.execute(select(AuditLog).where(AuditLog.object_type == "tenant_sso"))
            ).scalars()
        )
    assert rows, "every change is audited"
    assert "very-secret-value" not in repr([(r.before, r.after) for r in rows])


async def test_a_workspace_provider_is_held_to_its_workspace_and_domains(
    app: FastAPI, acme: Workspace, keycloak: _FakeKeycloak
) -> None:
    await _call(
        app,
        acme,
        "PUT",
        "",
        json={"organization_alias": "acme", "domains": ["acme.example"], "enabled": True},
    )
    await _call(app, acme, "POST", "/domains/acme.example/verify")
    await _call(
        app,
        acme,
        "PUT",
        "/provider",
        json={
            "provider": "oidc",
            "discovery_url": "http://idp.acme.example/.well-known/openid-configuration",
            "client_id": "cid",
            "client_secret": "s",
        },
    )
    # The Acme admin is also a member of another workspace.
    other = await signup_workspace(company="Other Ltd", email="admin@other.example")
    invited = await invite_directly(
        other, email="admin@acme.example", full_name="Acme Admin", role_name="Admin"
    )
    await iam_auth_service.accept_invitation(token=invited.invite_token)

    def through_acme(email: str, subject: str) -> sso.SsoIdentity:
        return sso.SsoIdentity(
            issuer="http://kc.test/realms/verity",
            subject=subject,
            email=email,
            email_verified=True,
            name=None,
            organizations=["acme"],
            idp="acme-oidc",
        )

    signed = await iam_auth_service.sso_sign_in(through_acme("admin@acme.example", "s-1"))
    assert isinstance(signed, SessionIssued), "only Acme is reachable, so no choice is offered"
    assert signed.principal.tenant_id == acme.tenant_id

    # Acme's provider cannot vouch for an address outside Acme's proven domains.
    with pytest.raises(sso.SsoFailed) as refused:
        await iam_auth_service.sso_sign_in(through_acme("admin@other.example", "s-2"))
    assert refused.value.code == "wrong_domain"
