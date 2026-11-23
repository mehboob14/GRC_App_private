"""Setting a workspace's single sign on up from Verity (add-keycloak-sso phase C, ADR-0015).

Three steps, each audited in the workspace's stream:

1. **Prove the domains.** The workspace publishes ``verity-domain-verification=<token>`` in a
   TXT record at ``_verity.<domain>``; Verity reads it over DNS over HTTPS. Only proven domains
   route sign in, and a domain proven by one workspace cannot be proven by another. Reserved test
   domains (``.example``, ``.test``, ``.localhost``) pass without DNS outside a deployed
   environment.
2. **Connect the identity provider.** Verity creates or updates, in Keycloak: the organization, the
   identity provider (from ``idp_templates``), the link between them, and the routing of each proven
   domain to it. The client secret goes to Keycloak only.
3. **Prove a sign in** (phase B's ``verified_at``) before SSO can be required.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Final

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.config import get_settings
from verity.core.db import provider_session_scope
from verity.core.errors import Conflict, InvalidInput, NotFound, UpstreamUnavailable
from verity.modules.audit.service import AuditService, Membership, audit_service
from verity.modules.iam import idp_templates
from verity.modules.iam.keycloak_admin import (
    KeycloakAdmin,
    broker_redirect_uri,
    service_provider_entity_id,
)
from verity.modules.iam.models import TenantSso
from verity.modules.iam.repository import SsoRepository

TXT_PREFIX: Final = "_verity"
TXT_VALUE_PREFIX: Final = "verity-domain-verification="
_TEST_TLDS: Final = (".example", ".test", ".localhost", ".invalid")
_SNAPSHOT: Final = (
    "organization_alias",
    "domains",
    "verified_domains",
    "enabled",
    "enforce",
    "provider",
    "idp_alias",
    "verified_at",
)


@dataclass(frozen=True, slots=True)
class ProviderOption:
    key: str
    label: str


@dataclass(frozen=True, slots=True)
class GroupRoleView:
    id: uuid.UUID
    group_name: str
    role_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class SsoSetupView:
    configured: bool
    organization_alias: str
    domains: list[str]
    verified_domains: list[str]
    txt_name_prefix: str
    txt_value: str | None
    enabled: bool
    enforce: bool
    jit_enabled: bool
    default_role_id: uuid.UUID | None
    verified_at: object
    provider: str | None
    idp_alias: str | None
    redirect_uri: str | None
    entity_id: str
    providers: list[ProviderOption] = field(default_factory=list)
    synced_at: object = None
    group_roles: list[GroupRoleView] = field(default_factory=list)


def _view(
    row: TenantSso | None, default_alias: str, group_roles: list[GroupRoleView] | None = None
) -> SsoSetupView:
    providers = [ProviderOption(k, idp_templates.LABELS[k]) for k in idp_templates.PROVIDERS]
    if row is None:
        return SsoSetupView(
            configured=False,
            organization_alias=default_alias,
            domains=[],
            verified_domains=[],
            txt_name_prefix=TXT_PREFIX,
            txt_value=None,
            enabled=False,
            enforce=False,
            jit_enabled=False,
            default_role_id=None,
            verified_at=None,
            provider=None,
            idp_alias=None,
            redirect_uri=None,
            entity_id=service_provider_entity_id(),
            providers=providers,
        )
    return SsoSetupView(
        configured=True,
        organization_alias=row.organization_alias,
        domains=list(row.domains),
        verified_domains=list(row.verified_domains),
        txt_name_prefix=TXT_PREFIX,
        txt_value=f"{TXT_VALUE_PREFIX}{row.domain_token}",
        enabled=row.enabled,
        enforce=row.enforce,
        jit_enabled=row.jit_enabled,
        default_role_id=row.default_role_id,
        verified_at=row.verified_at,
        provider=row.provider,
        idp_alias=row.idp_alias,
        redirect_uri=broker_redirect_uri(row.idp_alias or f"{row.organization_alias}-idp"),
        entity_id=service_provider_entity_id(),
        providers=providers,
        synced_at=row.synced_at,
        group_roles=group_roles or [],
    )


async def txt_records(name: str) -> list[str]:
    """TXT strings at ``name``, over DNS over HTTPS (JSON). Empty when there are none."""
    settings = get_settings().oidc
    try:
        async with httpx.AsyncClient(timeout=settings.timeout_seconds) as client:
            response = await client.get(
                settings.dns_resolver_url,
                params={"name": name, "type": "TXT"},
                headers={"Accept": "application/dns-json"},
            )
        response.raise_for_status()
        answers = response.json().get("Answer") or []
    except (httpx.HTTPError, ValueError) as exc:
        raise UpstreamUnavailable(
            "We could not look the domain up. Try again in a minute.",
            detail=f"DNS over HTTPS failed: {type(exc).__name__}",
        ) from exc
    # A long TXT value comes back as several quoted strings; joined, they are one record.
    return [
        str(a.get("data", "")).replace('" "', "").strip('"')
        for a in answers
        if a.get("type") == 16  # noqa: PLR2004 — the TXT record type
    ]


class SsoSetupService:
    def __init__(
        self, admin: KeycloakAdmin | None = None, audit: AuditService | None = None
    ) -> None:
        self._admin = admin
        self._audit = audit or audit_service
        self._sso = SsoRepository()

    def _keycloak(self) -> KeycloakAdmin:
        return self._admin or KeycloakAdmin()

    async def _tenant(self, session: AsyncSession, tenant_id: uuid.UUID) -> tuple[str, str]:
        """The workspace's display name, and the organization alias its slug suggests."""
        from verity.modules.tenancy.service import tenancy_service  # noqa: PLC0415

        tenant = await tenancy_service.get_tenant(session, tenant_id)
        slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in tenant.slug.lower())
        return tenant.trading_name or tenant.legal_name, slug.strip("-_")[:63] or "workspace"

    async def view(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> SsoSetupView:
        _, default_alias = await self._tenant(session, tenant_id)
        maps = [
            GroupRoleView(m.id, m.group_name, m.role_id)
            for m in await self._sso.group_roles(session, tenant_id)
        ]
        return _view(await self._sso.get(session, tenant_id), default_alias, maps)

    async def _row(self, session: AsyncSession, tenant_id: uuid.UUID) -> TenantSso:
        row = await self._sso.get(session, tenant_id)
        if row is None:
            raise NotFound(
                "Save the organization and its domains first.", detail="no tenant_sso row"
            )
        return row

    async def _record(
        self,
        session: AsyncSession,
        row: TenantSso,
        before: dict[str, object],
        actor_membership_id: uuid.UUID,
        **extra: object,
    ) -> None:
        after = AuditService.snapshot(row, fields=_SNAPSHOT)
        await self._audit.record(
            session,
            action="update",
            object_type="tenant_sso",
            object_id=row.id,
            actor=Membership(actor_membership_id),
            tenant_id=row.tenant_id,
            before=before,
            after={**after, **extra},
        )

    # -- step 1: prove a domain -------------------------------------------------------------

    async def verify_domain(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor_membership_id: uuid.UUID,
        domain: str,
    ) -> SsoSetupView:
        row = await self._row(session, tenant_id)
        tenant_name, _ = await self._tenant(session, tenant_id)
        domain = domain.strip().lower()
        if domain not in row.domains:
            raise NotFound("Add the domain first, then prove it.", detail=f"domain {domain}")
        async with provider_session_scope() as plane:
            others = await self._sso.verified_elsewhere(plane, tenant_id=tenant_id, domain=domain)
        if others:
            raise Conflict(
                "Another workspace has already proven it owns this domain.", detail=domain
            )
        expected = f"{TXT_VALUE_PREFIX}{row.domain_token}"
        test_domain = domain.endswith(_TEST_TLDS) and not get_settings().is_deployed
        if not test_domain and expected not in await txt_records(f"{TXT_PREFIX}.{domain}"):
            raise InvalidInput(
                f"We did not find the TXT record at {TXT_PREFIX}.{domain} yet. DNS changes can "
                "take a few minutes; try again shortly.",
                detail=f"no matching TXT at {TXT_PREFIX}.{domain}",
            )
        if domain in row.verified_domains:
            return _view(row, row.organization_alias)
        before = AuditService.snapshot(row, fields=_SNAPSHOT)
        row.verified_domains = sorted({*row.verified_domains, domain})
        await self._sso.add(session, row)
        await self._record(session, row, before, actor_membership_id, proved=domain)
        if row.idp_alias:
            await self.sync_routing(row, tenant_name)
        return _view(row, row.organization_alias)

    # -- step 2: connect the identity provider ---------------------------------------------

    async def connect(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor_membership_id: uuid.UUID,
        provider: str,
        given: idp_templates.ProviderInput,
    ) -> SsoSetupView:
        """Set the workspace's identity provider up in Keycloak. A new or changed provider has not
        been tried yet, so the proof of a working sign in is cleared, and enforcement with it."""
        row = await self._row(session, tenant_id)
        tenant_name, _ = await self._tenant(session, tenant_id)
        if not row.verified_domains:
            raise InvalidInput(
                "Prove at least one email domain first: sign in is routed by domain.",
                detail="connect before a verified domain",
            )
        allow_http = not get_settings().is_deployed
        source = idp_templates.import_source(provider, given, allow_http=allow_http)
        alias = f"{row.organization_alias}-{provider}"
        keycloak = self._keycloak()
        imported = await keycloak.import_config(*source) if source else {}
        representation = idp_templates.representation(
            provider=provider,
            alias=alias,
            imported=imported,
            given=given,
            hosted_domain=row.verified_domains[0],
            display_name=f"{tenant_name} ({idp_templates.LABELS[provider]})",
        )
        await keycloak.upsert_identity_provider(representation)
        if row.idp_alias and row.idp_alias != alias:
            await keycloak.set_identity_provider_enabled(row.idp_alias, False)
        before = AuditService.snapshot(row, fields=_SNAPSHOT)
        row.provider = provider
        row.idp_alias = alias
        row.verified_at = None
        row.enforce = False
        await self._sso.add(session, row)
        await self.sync_routing(row, tenant_name)
        # The secret is deliberately not in the audit row.
        await self._record(session, row, before, actor_membership_id, connected=provider)
        return _view(row, row.organization_alias)

    async def sync_routing(self, row: TenantSso, tenant_name: str) -> None:
        """Make Keycloak match the workspace: its organization, the identity provider linked to it,
        every proven domain sent to that provider, and the provider on only while SSO is on."""
        keycloak = self._keycloak()
        org = await keycloak.ensure_organization(row.organization_alias, tenant_name)
        if row.idp_alias:
            await keycloak.link_identity_provider(org["id"], row.idp_alias)
            await keycloak.set_identity_provider_enabled(row.idp_alias, row.enabled)
        await keycloak.route_domains(org["id"], list(row.verified_domains), row.idp_alias)


sso_setup_service: Final = SsoSetupService()
