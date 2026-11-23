"""Finish the local Keycloak for Verity's SSO work, through the Admin REST API. Idempotent.

Run after `bash infra/keycloak/run-local.sh` is up:

    python infra/keycloak/setup_local.py

What it does in realm `verity` (the parts the realm import format cannot express in this build):

1. Gives the `verity-admin` service account the realm-management roles phases C and D need.
2. Creates organization `northwind` (Verity's Northwind demo workspace) with domain `northwind.example`.
3. Links the `northwind-corp` identity provider to it with auto membership, and routes the domain to it,
   so an email ending in northwind.example goes straight to Northwind's own sign in.

Standard library only. Local development only: the admin credentials default to the throwaway ones in
run-local.sh.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

BASE = os.environ.get("KC_URL", "http://localhost:8180")
REALM = "verity"
ADMIN_USER = os.environ.get("KC_BOOTSTRAP_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("KC_BOOTSTRAP_ADMIN_PASSWORD", "admin")
SERVICE_ROLES = (
    "view-users",
    "query-users",
    "query-groups",
    "view-realm",
    "manage-realm",
    "manage-users",
    "manage-identity-providers",
)


def _call(method: str, path: str, token: str | None, body: Any = None) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 — fixed local URL
        raw = resp.read()
        return json.loads(raw) if raw else None


def _token() -> str:
    form = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": ADMIN_USER,
            "password": ADMIN_PASSWORD,
        }
    ).encode()
    req = urllib.request.Request(
        f"{BASE}/realms/master/protocol/openid-connect/token", data=form, method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 — fixed local URL
        return str(json.loads(resp.read())["access_token"])


def service_account_roles(token: str) -> None:
    client = _call("GET", f"/admin/realms/{REALM}/clients?clientId=verity-admin", token)[0]
    # This Keycloak build names the service account user on the client itself.
    user = {"id": client["serviceAccountUserId"]}
    # This build also refuses Admin API tokens without the kc-admin-api scope (its audience and
    # scope check); a default scope puts it in every token the service account gets.
    admin_scope = next(
        (
            c
            for c in _call("GET", f"/admin/realms/{REALM}/client-scopes", token)
            if c["name"] == "kc-admin-api"
        ),
        None,
    )
    if admin_scope is not None:
        _call(
            "PUT",
            f"/admin/realms/{REALM}/clients/{client['id']}/default-client-scopes/{admin_scope['id']}",
            token,
        )
    rm =_call("GET", f"/admin/realms/{REALM}/clients?clientId=realm-management", token)[0]
    roles = [
        _call("GET", f"/admin/realms/{REALM}/clients/{rm['id']}/roles/{name}", token)
        for name in SERVICE_ROLES
    ]
    _call(
        "POST",
        f"/admin/realms/{REALM}/users/{user['id']}/role-mappings/clients/{rm['id']}",
        token,
        roles,
    )
    print("verity-admin service account:", ", ".join(SERVICE_ROLES))


def organization(token: str) -> None:
    def find() -> list[dict[str, Any]]:
        listed = _call("GET", f"/admin/realms/{REALM}/organizations?max=1000", token)
        return [o for o in listed if o.get("alias") == "northwind"]

    orgs = find()
    if not orgs:
        _call(
            "POST",
            f"/admin/realms/{REALM}/organizations",
            token,
            {
                "name": "Northwind Software",
                "alias": "northwind",
                "enabled": True,
                "description": "Verity's Northwind demo workspace",
                "domains": [{"name": "northwind.example", "verified": True}],
            },
        )
        orgs = find()
    org = orgs[0]
    linked = {
        idp["alias"]
        for idp in _call(
            "GET", f"/admin/realms/{REALM}/organizations/{org['id']}/identity-providers", token
        )
    }
    if "northwind-corp" not in linked:
        _call(
            "POST",
            f"/admin/realms/{REALM}/organizations/{org['id']}/identity-providers",
            token,
            "northwind-corp",
        )
    _call(
        "PUT",
        f"/admin/realms/{REALM}/organizations/{org['id']}/identity-providers/northwind-corp",
        token,
        {"autoMembership": True, "membershipType": "MANAGED"},
    )
    full = _call("GET", f"/admin/realms/{REALM}/organizations/{org['id']}", token)
    full["domains"] = [
        {
            "name": "northwind.example",
            "verified": True,
            "identityProviderAlias": "northwind-corp",
            "autoRedirect": True,
        }
    ]
    _call("PUT", f"/admin/realms/{REALM}/organizations/{org['id']}", token, full)
    print("organization northwind:", org["id"], "domain northwind.example routes to northwind-corp")


def web_client(token: str) -> None:
    """Re-apply the verity-web redirect and sign out URLs from the realm file (an import only
    happens on the first start)."""
    realm_file = Path(__file__).with_name("realms") / "verity-realm.json"
    wanted = next(
        c for c in json.loads(realm_file.read_text("utf-8"))["clients"] if c["clientId"] == "verity-web"
    )
    live = _call("GET", f"/admin/realms/{REALM}/clients?clientId=verity-web", token)[0]
    live["redirectUris"] = wanted["redirectUris"]
    live["attributes"] = {**live.get("attributes", {}), **wanted["attributes"]}
    _call("PUT", f"/admin/realms/{REALM}/clients/{live['id']}", token, live)
    # The identity_provider claim tells Verity which identity provider signed a person in, so a
    # workspace's own provider can be held to that workspace (phase C).
    mappers = _call(
        "GET", f"/admin/realms/{REALM}/clients/{live['id']}/protocol-mappers/models", token
    )
    for mapper in wanted.get("protocolMappers", []):
        if not any(m["name"] == mapper["name"] for m in mappers):
            _call(
                "POST",
                f"/admin/realms/{REALM}/clients/{live['id']}/protocol-mappers/models",
                token,
                mapper,
            )
    print("verity-web redirect, sign out URLs and identity provider claim applied")


def customer_realm(token: str) -> None:
    """The stand-in customer IdP accepts any broker alias in realm verity, so a provider Verity
    sets up (phase C) can use it without editing this realm again."""
    realm_file = Path(__file__).with_name("realms") / "northwind-corp-realm.json"
    wanted = next(
        c
        for c in json.loads(realm_file.read_text("utf-8"))["clients"]
        if c["clientId"] == "keycloak-broker"
    )
    live = _call("GET", "/admin/realms/northwind-corp/clients?clientId=keycloak-broker", token)[0]
    live["redirectUris"] = wanted["redirectUris"]
    _call("PUT", f"/admin/realms/northwind-corp/clients/{live['id']}", token, live)
    print("northwind-corp accepts any verity broker alias")


def main() -> None:
    token = _token()
    try:
        web_client(token)
        customer_realm(token)
        service_account_roles(token)
        organization(token)
    except urllib.error.HTTPError as exc:
        print("Keycloak refused:", exc.code, exc.read().decode(errors="replace")[:500])
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
