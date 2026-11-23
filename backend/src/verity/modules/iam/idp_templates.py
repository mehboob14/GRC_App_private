"""What Verity asks for, per identity provider, and the Keycloak provider it builds from it.

Pure: no network. Keycloak fetches the discovery document or SAML metadata itself
(``KeycloakAdmin.import_config``); this module says where it lives and adds what the import does not
cover (client credentials, PKCE, signature checks, email trust).
"""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass
from typing import Any, Final

from verity.core.errors import InvalidInput

PROVIDERS: Final[tuple[str, ...]] = ("entra", "okta", "google", "oidc", "saml")
LABELS: Final[dict[str, str]] = {
    "entra": "Microsoft Entra ID",
    "okta": "Okta",
    "google": "Google Workspace",
    "oidc": "Other OpenID Connect provider",
    "saml": "SAML provider",
}
_TENANT_ID: Final = re.compile(
    r"^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[a-z0-9.-]+\.[a-z]{2,})$"
)
_HOST: Final = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")


@dataclass(frozen=True, slots=True)
class ProviderInput:
    tenant_id: str | None = None
    """Entra ID: the directory (tenant) id or its primary domain."""
    okta_domain: str | None = None
    discovery_url: str | None = None
    metadata_url: str | None = None
    client_id: str | None = None
    client_secret: str | None = None


def _require(value: str | None, what: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise InvalidInput(f"Enter the {what}.", detail=f"missing {what}")
    return cleaned


def _url(value: str | None, what: str, *, allow_http: bool) -> str:
    url = _require(value, what)
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ({"https", "http"} if allow_http else {"https"}) or not parts.hostname:
        raise InvalidInput(
            f"The {what} must be a full https address.", detail=f"{what} {url!r} rejected"
        )
    return url


def import_source(
    provider: str, given: ProviderInput, *, allow_http: bool
) -> tuple[str, str] | None:
    """``(Keycloak provider id, URL Keycloak imports from)``, or None for Google."""
    if provider == "entra":
        tenant = _require(given.tenant_id, "directory (tenant) ID").lower()
        if not _TENANT_ID.fullmatch(tenant):
            raise InvalidInput(
                "Use the directory (tenant) ID from Entra ID, or its primary domain.",
                detail=f"entra tenant {tenant!r}",
            )
        return "oidc", (
            f"https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration"
        )
    if provider == "okta":
        domain = _require(given.okta_domain, "Okta domain").lower()
        domain = domain.removeprefix("https://").removesuffix("/")
        if not _HOST.fullmatch(domain):
            raise InvalidInput("Use your Okta domain, like acme.okta.com.", detail=domain)
        return "oidc", f"https://{domain}/.well-known/openid-configuration"
    if provider == "oidc":
        return "oidc", _url(given.discovery_url, "discovery URL", allow_http=allow_http)
    if provider == "saml":
        return "saml", _url(given.metadata_url, "metadata URL", allow_http=allow_http)
    if provider == "google":
        return None
    raise InvalidInput("Choose one of the listed identity providers.", detail=provider)


def representation(  # noqa: PLR0913 — one identity provider's facts
    *,
    provider: str,
    alias: str,
    imported: dict[str, str],
    given: ProviderInput,
    hosted_domain: str | None,
    display_name: str,
) -> dict[str, Any]:
    """The Keycloak identity provider. Email is trusted because Verity confines a workspace's
    identity provider to that workspace's DNS proven domains (ADR-0015, phase C)."""
    common: dict[str, Any] = {
        "alias": alias,
        "displayName": display_name,
        "enabled": True,
        "trustEmail": True,
        "hideOnLogin": True,
        "firstBrokerLoginFlowAlias": "first broker login",
    }
    if provider == "saml":
        return {
            **common,
            "providerId": "saml",
            "config": {
                **imported,
                "nameIDPolicyFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
                "principalType": "SUBJECT",
                "syncMode": "FORCE",
                "validateSignature": imported.get("validateSignature", "true"),
                "wantAssertionsSigned": "true",
            },
        }
    client_id = _require(given.client_id, "client ID")
    client_secret = _require(given.client_secret, "client secret")
    if provider == "google":
        return {
            **common,
            "providerId": "google",
            "config": {
                "clientId": client_id,
                "clientSecret": client_secret,
                "hostedDomain": hosted_domain or "",
                "defaultScope": "openid email profile",
                "syncMode": "FORCE",
            },
        }
    return {
        **common,
        "providerId": "oidc",
        "config": {
            **imported,
            "clientId": client_id,
            "clientSecret": client_secret,
            "clientAuthMethod": "client_secret_post",
            "defaultScope": "openid email profile",
            "validateSignature": "true",
            "useJwksUrl": "true",
            "pkceEnabled": "true",
            "pkceMethod": "S256",
            "syncMode": "FORCE",
        },
    }
