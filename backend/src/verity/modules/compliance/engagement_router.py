"""HTTP for engagement setup, scope, the coverage view, and the dashboard."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.deps import (
    Principal,
    TenantContext,
    get_tenant_context,
    get_tenant_session,
    require,
)
from verity.modules.audit.service import Membership
from verity.modules.compliance.engagement_service import engagement_service
from verity.modules.compliance.schemas import (
    CoverageOut,
    DashboardOut,
    EngagementOut,
    EngagementPut,
    ScopeCriterionOut,
)

engagement_router = APIRouter(prefix="/engagement", tags=["engagement"])

require_engagement_read = require("frameworks:read")
require_engagement_manage = require("controls:manage")


@engagement_router.get(
    "",
    response_model=EngagementOut | None,
    summary="The tenant's engagement, or null before one is set up",
)
async def get_engagement(
    _principal: Annotated[Principal, Depends(require_engagement_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> EngagementOut | None:
    engagement = await engagement_service.get(session, tenant_id=context.tenant_id)
    return EngagementOut.model_validate(engagement) if engagement else None


@engagement_router.put("", response_model=EngagementOut, summary="Create or update the engagement")
async def put_engagement(
    body: EngagementPut,
    principal: Annotated[Principal, Depends(require_engagement_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> EngagementOut:
    assert principal.membership_id is not None  # noqa: S101
    engagement = await engagement_service.upsert(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        name=body.name,
        framework_version_id=body.framework_version_id,
        audit_type=body.audit_type,
        categories_in_scope=body.categories_in_scope,
        window_start=body.window_start,
        window_end=body.window_end,
        status=body.status,
    )
    return EngagementOut.model_validate(engagement)


@engagement_router.get(
    "/scope",
    response_model=list[ScopeCriterionOut],
    summary="The criteria the engagement's scope actually covers",
)
async def get_scope(
    _principal: Annotated[Principal, Depends(require_engagement_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> list[ScopeCriterionOut]:
    criteria = await engagement_service.criteria_in_scope(session, tenant_id=context.tenant_id)
    return [ScopeCriterionOut.model_validate(c) for c in criteria]


@engagement_router.get(
    "/coverage",
    response_model=CoverageOut,
    summary="Criteria in scope with no control, and controls with no evidence",
)
async def get_coverage(
    _principal: Annotated[Principal, Depends(require_engagement_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> CoverageOut:
    report = await engagement_service.coverage(session, tenant_id=context.tenant_id)
    return CoverageOut.model_validate(report)


@engagement_router.get(
    "/dashboard",
    response_model=DashboardOut,
    summary="Compliance dashboard: coverage, control health, timeline, activity",
)
async def get_dashboard(
    _principal: Annotated[Principal, Depends(require_engagement_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
    window_from: Annotated[date | None, Query(alias="from")] = None,
    window_to: Annotated[date | None, Query(alias="to")] = None,
) -> DashboardOut:
    report = await engagement_service.dashboard(
        session,
        tenant_id=context.tenant_id,
        window_from=window_from,
        window_to=window_to,
    )
    return DashboardOut.model_validate(report)
