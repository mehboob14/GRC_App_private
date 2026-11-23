"""Keycloak's Admin REST API, as Verity's service account uses it to set a workspace up (phase C).

Verity touches only what a workspace owns: its organization (named by ``tenant_sso.
organization_alias``) and its identity provider (``tenant_sso.idp_alias``). The service account's
roles in the client's realm are wider than that, so the ownership check lives in the caller, not in
Keycloak. Client secrets pass through to Keycloak and are never stored or logged by Verity.
"""

from __future__ import annotations

import time
from typing import Any, Final

import httpx

from verity.core.config import get_settings
from verity.core.errors import UpstreamUnavailable
from verity.core.logging import get_logger

logger = get_logger(__name__)

_PAGE: Final = 100
_UNAVAILABLE: Final = (
    "Keycloak did not accept the change. Check the details and try again, or ask your Keycloak "
    "administrator."
)


def realm_parts() -> tuple[str, str]:
    """``(base URL, realm)`` from the configured issuer, e.g. ``http://kc:8180``, ``verity``."""
    issuer = get_settings().oidc.issuer_url.rstrip("/")
    base, _, realm = issuer.rpartition("/realms/")
    return base, realm


def broker_redirect_uri(idp_alias: str) -> str:
    """What the customer registers at their identity provider as the redirect (or ACS) URL."""
    base, realm = realm_parts()
    return f"{base}/realms/{realm}/broker/{idp_alias}/endpoint"


def service_provider_entity_id() -> str:
    base, realm = realm_parts()
    return f"{base}/realms/{realm}"


class KeycloakAdmin:
    """One client per unit of work. ``transport`` lets tests answer for Keycloak."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport
        self._token: tuple[str, float] | None = None

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=self._transport, timeout=get_settings().oidc.timeout_seconds
        )

    async def _access_token(self) -> str:
        if self._token and self._token[1] > time.monotonic():
            return self._token[0]
        settings = get_settings().oidc
        if settings.admin_client_secret is None:
            raise UpstreamUnavailable(
                "Single sign on setup is not configured on this server.",
                detail="OIDC_ADMIN_CLIENT_SECRET is not set",
            )
        issuer = settings.issuer_url.rstrip("/")
        async with self._client() as client:
            try:
                response = await client.post(
                    f"{issuer}/protocol/openid-connect/token",
                    data={"grant_type": "client_credentials"},
                    auth=(
                        settings.admin_client_id,
                        settings.admin_client_secret.get_secret_value(),
                    ),
                )
            except httpx.HTTPError as exc:
                raise UpstreamUnavailable(
                    _UNAVAILABLE, detail=f"admin token: {type(exc).__name__}"
                ) from exc
        if response.status_code != 200:  # noqa: PLR2004
            raise UpstreamUnavailable(
                _UNAVAILABLE, detail=f"admin token answered {response.status_code}"
            )
        body = response.json()
        self._token = (str(body["access_token"]), time.monotonic() + int(body["expires_in"]) - 30)
        return self._token[0]

    async def _call(
        self,
        method: str,
        path: str,
        *,
        body: Any = None,  # noqa: ANN401 — Keycloak takes JSON of any shape
        missing_ok: bool = False,
    ) -> Any:  # noqa: ANN401 — Keycloak's JSON
        base, realm = realm_parts()
        token = await self._access_token()
        async with self._client() as client:
            try:
                response = await client.request(
                    method,
                    f"{base}/admin/realms/{realm}{path}",
                    json=body,
                    headers={"Authorization": f"Bearer {token}"},
                )
            except httpx.HTTPError as exc:
                raise UpstreamUnavailable(
                    _UNAVAILABLE, detail=f"{method} {path}: {type(exc).__name__}"
                ) from exc
        if response.status_code == 404 and missing_ok:  # noqa: PLR2004
            return None
        if response.status_code >= 400:  # noqa: PLR2004
            # Keycloak's own words go to the log only: they can name internals.
            logger.info(
                "keycloak.admin_refused",
                method=method,
                path=path,
                status=response.status_code,
                answer=response.text[:300],
            )
            raise UpstreamUnavailable(
                _UNAVAILABLE, detail=f"{method} {path} answered {response.status_code}"
            )
        return response.json() if response.content else None

    # -- organizations ----------------------------------------------------------------------

    async def organization(self, alias: str) -> dict[str, Any] | None:
        found = await self._call("GET", f"/organizations?search={alias}&max=100")
        return next((o for o in found or [] if o.get("alias") == alias), None)

    async def ensure_organization(self, alias: str, name: str) -> dict[str, Any]:
        org = await self.organization(alias)
        if org is None:
            await self._call(
                "POST",
                "/organizations",
                body={"name": name, "alias": alias, "enabled": True, "domains": []},
            )
            org = await self.organization(alias)
        if org is None:
            raise UpstreamUnavailable(_UNAVAILABLE, detail=f"organization {alias} not created")
        return org

    async def route_domains(self, org_id: str, domains: list[str], idp_alias: str | None) -> None:
        """Set the organization's domains (all proven by DNS) and send each to the identity
        provider, so an email from one of them goes straight to it."""
        org = await self._call("GET", f"/organizations/{org_id}")
        org["domains"] = [
            {
                "name": d,
                "verified": True,
                **({"identityProviderAlias": idp_alias, "autoRedirect": True} if idp_alias else {}),
            }
            for d in domains
        ]
        await self._call("PUT", f"/organizations/{org_id}", body=org)

    async def link_identity_provider(self, org_id: str, alias: str) -> None:
        linked = {
            idp["alias"]
            for idp in await self._call("GET", f"/organizations/{org_id}/identity-providers") or []
        }
        if alias not in linked:
            await self._call("POST", f"/organizations/{org_id}/identity-providers", body=alias)
        await self._call(
            "PUT",
            f"/organizations/{org_id}/identity-providers/{alias}",
            body={"autoMembership": True, "membershipType": "MANAGED"},
        )

    async def members(self, org_id: str) -> list[dict[str, Any]]:
        """Every member of the organization, page by page (id, email, emailVerified, enabled)."""
        out: list[dict[str, Any]] = []
        while True:
            page = await self._call(
                "GET",
                f"/organizations/{org_id}/members?first={len(out)}&max={_PAGE}"
                "&briefRepresentation=false",
            )
            out.extend(page or [])
            if len(page or []) < _PAGE:
                return out

    async def member_groups(self, org_id: str, member_id: str) -> list[str]:
        """The organization's groups this member is in, each by name and by path."""
        groups = await self._call(
            "GET", f"/organizations/{org_id}/members/{member_id}/groups?max=1000"
        )
        return [v for g in groups or [] for v in (g.get("name"), g.get("path")) if v]

    # -- identity providers ----------------------------------------------------------------

    async def import_config(self, provider_id: str, from_url: str) -> dict[str, str]:
        """Keycloak reads the provider's discovery document (OIDC) or metadata (SAML) itself."""
        imported = await self._call(
            "POST",
            "/identity-provider/import-config",
            body={"providerId": provider_id, "fromUrl": from_url},
        )
        return {str(k): str(v) for k, v in (imported or {}).items()}

    async def upsert_identity_provider(self, representation: dict[str, Any]) -> None:
        alias = representation["alias"]
        existing = await self._call("GET", f"/identity-provider/instances/{alias}", missing_ok=True)
        if existing is None:
            await self._call("POST", "/identity-provider/instances", body=representation)
        else:
            await self._call(
                "PUT",
                f"/identity-provider/instances/{alias}",
                body={**existing, **representation, "internalId": existing.get("internalId")},
            )

    async def set_identity_provider_enabled(self, alias: str, enabled: bool) -> None:
        existing = await self._call("GET", f"/identity-provider/instances/{alias}", missing_ok=True)
        if existing is not None and existing.get("enabled") != enabled:
            await self._call(
                "PUT",
                f"/identity-provider/instances/{alias}",
                body={**existing, "enabled": enabled},
            )
