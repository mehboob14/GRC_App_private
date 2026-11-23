"""Phase C, no network: provider templates, and the Admin API client against a fake Keycloak."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from verity.core.config import get_settings
from verity.core.errors import InvalidInput, UpstreamUnavailable
from verity.modules.iam import idp_templates, keycloak_admin
from verity.modules.iam.idp_templates import ProviderInput

ISSUER = "http://kc.test/realms/verity"


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings().model_copy(
        update={
            "oidc": get_settings().oidc.model_copy(
                update={"issuer_url": ISSUER, "admin_client_secret": SecretStr("admin-secret")}
            )
        }
    )
    monkeypatch.setattr(keycloak_admin, "get_settings", lambda: settings)


def test_where_each_provider_is_imported_from() -> None:
    tenant = "0b1c2d3e-4f50-6172-8394-a5b6c7d8e9f0"
    assert idp_templates.import_source(
        "entra", ProviderInput(tenant_id=tenant), allow_http=False
    ) == (
        "oidc",
        f"https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration",
    )
    assert idp_templates.import_source(
        "okta", ProviderInput(okta_domain="https://Acme.okta.com/"), allow_http=False
    ) == ("oidc", "https://acme.okta.com/.well-known/openid-configuration")
    assert idp_templates.import_source("google", ProviderInput(), allow_http=False) is None
    with pytest.raises(InvalidInput):
        idp_templates.import_source(
            "entra", ProviderInput(tenant_id="not a tenant"), allow_http=False
        )
    with pytest.raises(InvalidInput):
        idp_templates.import_source(
            "oidc", ProviderInput(discovery_url="http://idp.internal/x"), allow_http=False
        )
    assert idp_templates.import_source(
        "saml", ProviderInput(metadata_url="http://localhost/m"), allow_http=True
    ) == ("saml", "http://localhost/m")


def test_the_representation_adds_credentials_pkce_and_trust() -> None:
    rep = idp_templates.representation(
        provider="okta",
        alias="acme-okta",
        imported={"authorizationUrl": "https://acme.okta.com/oauth2/v1/authorize"},
        given=ProviderInput(client_id="cid", client_secret="sec"),  # noqa: S106 — fake
        hosted_domain="acme.com",
        display_name="Acme (Okta)",
    )
    assert rep["providerId"] == "oidc"
    assert rep["trustEmail"] is True
    assert rep["config"]["pkceMethod"] == "S256"
    assert rep["config"]["authorizationUrl"].startswith("https://acme.okta.com")
    google = idp_templates.representation(
        provider="google",
        alias="acme-google",
        imported={},
        given=ProviderInput(client_id="cid", client_secret="sec"),  # noqa: S106 — fake
        hosted_domain="acme.com",
        display_name="Acme (Google Workspace)",
    )
    assert google["config"]["hostedDomain"] == "acme.com", "only the company's own Google accounts"
    with pytest.raises(InvalidInput):
        idp_templates.representation(
            provider="oidc",
            alias="a-oidc",
            imported={},
            given=ProviderInput(client_id="cid"),
            hosted_domain=None,
            display_name="A",
        )


class _FakeKeycloak:
    """Answers the Admin API the way Keycloak does, keeping what was written."""

    def __init__(self) -> None:
        self.idps: dict[str, dict[str, Any]] = {}
        self.orgs: dict[str, dict[str, Any]] = {}
        self.links: dict[str, set[str]] = {}
        self.members: dict[str, list[dict[str, Any]]] = {}
        self.groups: dict[str, list[dict[str, Any]]] = {}
        self.calls: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:  # noqa: PLR0911, PLR0912 — one answer per route
        path = request.url.path
        self.calls.append(f"{request.method} {path}")
        if path.endswith("/protocol/openid-connect/token"):
            assert request.headers["authorization"].startswith("Basic ")
            return httpx.Response(200, json={"access_token": "t", "expires_in": 300})
        body = json.loads(request.content) if request.content else None
        assert request.headers["authorization"] == "Bearer t"
        admin = "/admin/realms/verity"
        if path == f"{admin}/identity-provider/import-config":
            return httpx.Response(200, json={"issuer": body["fromUrl"]})
        if path.startswith(f"{admin}/identity-provider/instances"):
            alias = path.rsplit("/", 1)[1]
            if request.method == "GET":
                found = self.idps.get(alias)
                return httpx.Response(200, json=found) if found else httpx.Response(404)
            if request.method == "POST":
                self.idps[body["alias"]] = {**body, "internalId": "x"}
                return httpx.Response(201)
            self.idps[alias] = body
            return httpx.Response(204)
        if path == f"{admin}/organizations" and request.method == "GET":
            return httpx.Response(200, json=list(self.orgs.values()))
        if path == f"{admin}/organizations" and request.method == "POST":
            self.orgs[body["alias"]] = {**body, "id": f"org-{body['alias']}"}
            return httpx.Response(201)
        if "/members" in path:
            org = path.split("/organizations/")[1].split("/")[0]
            if path.endswith("/groups"):
                return httpx.Response(200, json=self.groups.get(path.split("/")[-2], []))
            first, size = int(request.url.params["first"]), int(request.url.params["max"])
            return httpx.Response(200, json=self.members.get(org, [])[first : first + size])
        if "/identity-providers" in path:
            org = path.split("/organizations/")[1].split("/")[0]
            if request.method == "GET":
                return httpx.Response(200, json=[{"alias": a} for a in self.links.get(org, set())])
            if request.method == "POST":
                self.links.setdefault(org, set()).add(body)
            return httpx.Response(204)
        if path.startswith(f"{admin}/organizations/"):
            org_id = path.rsplit("/", 1)[1]
            org = next(o for o in self.orgs.values() if o["id"] == org_id)
            if request.method == "PUT":
                org.update(body)
                return httpx.Response(204)
            return httpx.Response(200, json=org)
        return httpx.Response(500)


async def test_the_admin_client_creates_then_updates_and_routes_domains() -> None:
    fake = _FakeKeycloak()
    admin = keycloak_admin.KeycloakAdmin(transport=httpx.MockTransport(fake))
    imported = await admin.import_config(
        "oidc", "https://acme.okta.com/.well-known/openid-configuration"
    )
    assert imported["issuer"].startswith("https://acme.okta.com")
    await admin.upsert_identity_provider({"alias": "acme-okta", "enabled": True, "config": {}})
    await admin.upsert_identity_provider(
        {"alias": "acme-okta", "enabled": True, "config": {"x": "1"}}
    )
    assert fake.idps["acme-okta"]["config"] == {"x": "1"}
    assert fake.idps["acme-okta"]["internalId"] == "x", "an update keeps Keycloak's own id"
    org = await admin.ensure_organization("acme", "Acme")
    await admin.link_identity_provider(org["id"], "acme-okta")
    await admin.route_domains(org["id"], ["acme.com"], "acme-okta")
    assert fake.orgs["acme"]["domains"] == [
        {
            "name": "acme.com",
            "verified": True,
            "identityProviderAlias": "acme-okta",
            "autoRedirect": True,
        }
    ]
    await admin.set_identity_provider_enabled("acme-okta", False)
    assert fake.idps["acme-okta"]["enabled"] is False
    assert sum(1 for c in fake.calls if c.endswith("/token")) == 1, "the token is reused"
    assert keycloak_admin.broker_redirect_uri("acme-okta") == (
        "http://kc.test/realms/verity/broker/acme-okta/endpoint"
    )


async def test_keycloak_refusals_are_typed_and_say_nothing_internal() -> None:
    admin = keycloak_admin.KeycloakAdmin(
        transport=httpx.MockTransport(
            lambda r: (
                httpx.Response(200, json={"access_token": "t", "expires_in": 300})
                if r.url.path.endswith("/token")
                else httpx.Response(
                    409, text="Identity Provider acme-okta already exists in table X"
                )
            )
        )
    )
    with pytest.raises(UpstreamUnavailable) as refused:
        await admin.upsert_identity_provider({"alias": "acme-okta"})
    assert "table" not in refused.value.message
