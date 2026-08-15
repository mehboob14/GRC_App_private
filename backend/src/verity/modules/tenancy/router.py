"""The tenants register (provider plane) and the tenant's own two reads.

Routers are HTTP only: parse, authorise, call the service, shape the response.
Every route declares its permission. Provider routes address a tenant **as a
resource** — ``/provider/tenants/{tenant_id}`` is the register's key, not the
acting tenant, and no provider route ever binds ``app.tenant_id``
(add-provider-plane/design.md, "Tenant identifiers in provider-plane paths").

The two tenant-plane routes resolve the tenant from the session's
:class:`TenantContext`, never from a parameter: there is no route, parameter, or
filter by which a tenant addresses another tenant.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Final

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.deps import (
    PlatformAdminPrincipal,
    Principal,
    TenantContext,
    get_provider_session,
    get_tenant_context,
    get_tenant_session,
    require,
    require_provider,
)
from verity.modules.tenancy.models import (
    PROVISIONING_STATUS_PENDING,
    Tenant,
    TenantProvisioningStep,
    TenantSmtp,
)
from verity.modules.tenancy.schemas import (
    BrandingPut,
    BrandingResponse,
    CompanyProfileResponse,
    CompanyProfileUpdate,
    ProvisioningResponse,
    ProvisioningStepResponse,
    SmtpConfigResponse,
    SmtpConfigUpdate,
    SmtpTestRequest,
    SmtpTestResponse,
    TenantPage,
    TenantProfileResponse,
    TenantRegistration,
    TenantResponse,
    TenantStatusFilter,
    TenantUpdate,
)
from verity.modules.tenancy.service import tenancy_service

DEFAULT_PAGE_SIZE: Final = 50
MAX_PAGE_SIZE: Final = 200

provider_tenants_router = APIRouter(prefix="/provider/tenants", tags=["provider tenants"])
tenant_router = APIRouter(prefix="/tenant", tags=["tenant"])

# Named rather than inlined so tests can target the exact dependency objects.
require_tenants_create = require_provider("tenants:create")
require_tenants_read = require_provider("tenants:read")
require_tenants_update = require_provider("tenants:update")
require_tenants_brand = require_provider("tenants:brand")
require_tenants_provision = require_provider("tenants:provision")

require_tenant_read = require("tenant:read")
"""The tenant-plane permission dependency. ``core.deps.require`` is a Week 1
placeholder until IAM lands; tests override this exact object, and nothing here
changes when the real implementation arrives (the audit module set the pattern)."""

require_tenant_manage = require("tenant:manage")
"""Editing the company profile is an Admin action (holds every key at check time)."""


def _provisioning_response(
    tenant: Tenant, steps: list[TenantProvisioningStep]
) -> ProvisioningResponse:
    return ProvisioningResponse(
        tenant_id=tenant.id,
        tenant_status=tenant.status,
        steps=[ProvisioningStepResponse.model_validate(step) for step in steps],
        remaining=[step.step for step in steps if step.status == PROVISIONING_STATUS_PENDING],
    )


# ---------------------------------------------------------------------------
# Provider plane
# ---------------------------------------------------------------------------


@provider_tenants_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=TenantResponse,
    summary="Register a tenant with its company profile and provisioning steps",
)
async def register_tenant(
    body: TenantRegistration,
    admin: Annotated[PlatformAdminPrincipal, Depends(require_tenants_create)],
    session: Annotated[AsyncSession, Depends(get_provider_session)],
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            description="A repeat with the same key and body returns the original tenant.",
        ),
    ] = None,
) -> TenantResponse:
    tenant = await tenancy_service.register_tenant(
        session,
        actor_admin_id=admin.id,
        profile=body,
        idempotency_key=idempotency_key,
    )
    return TenantResponse.model_validate(tenant)


@provider_tenants_router.get(
    "",
    response_model=TenantPage,
    summary="The tenants register, newest first",
)
async def list_tenants(
    _admin: Annotated[PlatformAdminPrincipal, Depends(require_tenants_read)],
    session: Annotated[AsyncSession, Depends(get_provider_session)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    cursor: Annotated[str | None, Query()] = None,
    tenant_status: Annotated[
        TenantStatusFilter | None, Query(alias="status", description="Filter by lifecycle state.")
    ] = None,
) -> TenantPage:
    tenants, next_cursor = await tenancy_service.list_tenants(
        session, limit=limit, cursor=cursor, status=tenant_status
    )
    return TenantPage(
        items=[TenantResponse.model_validate(tenant) for tenant in tenants],
        next_cursor=next_cursor,
    )


@provider_tenants_router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="One tenant from the register",
)
async def get_tenant(
    tenant_id: uuid.UUID,
    _admin: Annotated[PlatformAdminPrincipal, Depends(require_tenants_read)],
    session: Annotated[AsyncSession, Depends(get_provider_session)],
) -> TenantResponse:
    tenant = await tenancy_service.get_tenant(session, tenant_id)
    return TenantResponse.model_validate(tenant)


@provider_tenants_router.patch(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Update the company profile. Lifecycle is not a field write.",
)
async def update_tenant(
    tenant_id: uuid.UUID,
    body: TenantUpdate,
    admin: Annotated[PlatformAdminPrincipal, Depends(require_tenants_update)],
    session: Annotated[AsyncSession, Depends(get_provider_session)],
) -> TenantResponse:
    tenant = await tenancy_service.update_tenant(
        session, actor_admin_id=admin.id, tenant_id=tenant_id, changes=body
    )
    return TenantResponse.model_validate(tenant)


@provider_tenants_router.get(
    "/{tenant_id}/branding",
    response_model=BrandingResponse,
    summary="A tenant's branding. The SMTP credential is never in the response.",
)
async def get_branding(
    tenant_id: uuid.UUID,
    _admin: Annotated[PlatformAdminPrincipal, Depends(require_tenants_read)],
    session: Annotated[AsyncSession, Depends(get_provider_session)],
) -> BrandingResponse:
    branding = await tenancy_service.get_branding(session, tenant_id)
    return BrandingResponse.model_validate(branding)


@provider_tenants_router.put(
    "/{tenant_id}/branding",
    response_model=BrandingResponse,
    summary="Replace a tenant's branding; SMTP credentials are encrypted before storage",
)
async def put_branding(
    tenant_id: uuid.UUID,
    body: BrandingPut,
    admin: Annotated[PlatformAdminPrincipal, Depends(require_tenants_brand)],
    session: Annotated[AsyncSession, Depends(get_provider_session)],
) -> BrandingResponse:
    branding = await tenancy_service.put_branding(
        session, actor_admin_id=admin.id, tenant_id=tenant_id, body=body
    )
    return BrandingResponse.model_validate(branding)


@provider_tenants_router.post(
    "/{tenant_id}/provision",
    response_model=ProvisioningResponse,
    summary="Run provisioning: complete what can complete, idempotently",
)
async def run_provisioning(
    tenant_id: uuid.UUID,
    admin: Annotated[PlatformAdminPrincipal, Depends(require_tenants_provision)],
    session: Annotated[AsyncSession, Depends(get_provider_session)],
) -> ProvisioningResponse:
    tenant, steps = await tenancy_service.run_provisioning(
        session, actor_admin_id=admin.id, tenant_id=tenant_id
    )
    return _provisioning_response(tenant, steps)


@provider_tenants_router.get(
    "/{tenant_id}/provisioning",
    response_model=ProvisioningResponse,
    summary="Inspect a tenant's provisioning steps",
)
async def get_provisioning(
    tenant_id: uuid.UUID,
    _admin: Annotated[PlatformAdminPrincipal, Depends(require_tenants_read)],
    session: Annotated[AsyncSession, Depends(get_provider_session)],
) -> ProvisioningResponse:
    tenant, steps = await tenancy_service.get_provisioning(session, tenant_id)
    return _provisioning_response(tenant, steps)


# ---------------------------------------------------------------------------
# Tenant plane — two reads, resolved from the session, no identifiers accepted
# ---------------------------------------------------------------------------


@tenant_router.get(
    "",
    response_model=TenantProfileResponse,
    summary="The calling tenant's own registration profile",
    dependencies=[Depends(require_tenant_read)],
)
async def read_own_tenant(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> TenantProfileResponse:
    # Lifecycle, plan, and slug are written from the provider plane only: these
    # routes are GET by construction, and the RLS policy is SELECT-only besides.
    tenant = await tenancy_service.get_own_tenant(session, context.tenant_id)
    return TenantProfileResponse.model_validate(tenant)


@tenant_router.get(
    "/branding",
    response_model=BrandingResponse,
    summary="The calling tenant's own branding, without the SMTP credential",
    dependencies=[Depends(require_tenant_read)],
)
async def read_own_branding(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> BrandingResponse:
    branding = await tenancy_service.get_own_branding(session, context.tenant_id)
    return BrandingResponse.model_validate(branding)


@tenant_router.get(
    "/profile",
    response_model=CompanyProfileResponse,
    summary="The calling tenant's own company profile (seeded from registration)",
    dependencies=[Depends(require_tenant_read)],
)
async def read_own_company_profile(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> CompanyProfileResponse:
    profile = await tenancy_service.get_own_company_profile(session, context.tenant_id)
    return CompanyProfileResponse.model_validate(profile)


@tenant_router.patch(
    "/profile",
    response_model=CompanyProfileResponse,
    summary="Update the calling tenant's company profile (Admin)",
)
async def update_own_company_profile(
    body: CompanyProfileUpdate,
    principal: Annotated[Principal, Depends(require_tenant_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> CompanyProfileResponse:
    assert principal.membership_id is not None  # noqa: S101 — tenant plane always has one
    profile = await tenancy_service.update_own_company_profile(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        changes=body,
    )
    return CompanyProfileResponse.model_validate(profile)


def _smtp_response(smtp: TenantSmtp | None) -> SmtpConfigResponse:
    if smtp is None:
        return SmtpConfigResponse(
            host=None,
            port=587,
            username=None,
            from_name=None,
            from_address=None,
            use_tls=True,
            enabled=False,
            has_password=False,
        )
    return SmtpConfigResponse(
        host=smtp.host,
        port=smtp.port,
        username=smtp.username,
        from_name=smtp.from_name,
        from_address=smtp.from_address,
        use_tls=smtp.use_tls,
        enabled=smtp.enabled,
        has_password=smtp.password_encrypted is not None,
    )


@tenant_router.get(
    "/smtp",
    response_model=SmtpConfigResponse,
    summary="The calling tenant's SMTP config (never the password)",
    dependencies=[Depends(require_tenant_read)],
)
async def read_own_smtp(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> SmtpConfigResponse:
    return _smtp_response(await tenancy_service.get_own_smtp(session, context.tenant_id))


@tenant_router.put(
    "/smtp",
    response_model=SmtpConfigResponse,
    summary="Configure the calling tenant's own SMTP server (Admin)",
)
async def update_own_smtp(
    body: SmtpConfigUpdate,
    principal: Annotated[Principal, Depends(require_tenant_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> SmtpConfigResponse:
    assert principal.membership_id is not None  # noqa: S101 — tenant plane always has one
    smtp = await tenancy_service.update_own_smtp(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        changes=body,
    )
    return _smtp_response(smtp)


@tenant_router.post(
    "/smtp/test",
    response_model=SmtpTestResponse,
    summary="Send a test email through the tenant's SMTP (Admin)",
    dependencies=[Depends(require_tenant_manage)],
)
async def test_own_smtp(
    body: SmtpTestRequest,
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> SmtpTestResponse:
    ok, detail = await tenancy_service.send_test_smtp(
        session, tenant_id=context.tenant_id, to_email=body.to_email
    )
    return SmtpTestResponse(ok=ok, detail=detail)
