"""HTTP for engagement setup, scope, the coverage view, and the dashboard."""

from __future__ import annotations

import uuid
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
from verity.modules.compliance.engagement_service import DETAIL_FIELDS, engagement_service
from verity.modules.compliance.models import DEFAULT_FRAMEWORK
from verity.modules.compliance.schemas import (
    CoverageOut,
    DashboardOut,
    EngagementOut,
    EngagementPut,
    ScopeCriterionOut,
    ScopeDecisionIn,
    ScopeDecisionOut,
    ScopeItemIn,
    ScopeItemOut,
    ScopeRetireIn,
    ScopeRetireOut,
)
from verity.modules.compliance.scope_service import scope_service

engagement_router = APIRouter(prefix="/engagement", tags=["engagement"])

require_engagement_read = require("frameworks:read")
require_engagement_manage = require("controls:manage")

# The framework a read is about, by code. Omitted means SOC 2, so every client written
# before a second framework existed keeps getting the answer it always did.
FrameworkParam = Annotated[str, Query(alias="framework", max_length=40)]


@engagement_router.get(
    "",
    response_model=EngagementOut | None,
    summary="The tenant's engagement, or null before one is set up",
)
async def get_engagement(
    _principal: Annotated[Principal, Depends(require_engagement_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
    framework: FrameworkParam = DEFAULT_FRAMEWORK,
) -> EngagementOut | None:
    engagement = await engagement_service.get(
        session, tenant_id=context.tenant_id, framework_code=framework
    )
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
        scope_statement=body.scope_statement,
        certification_body=body.certification_body,
        audit_on=body.audit_on,
        sent=body.model_fields_set,
        details={
            name: getattr(body, name) for name in DETAIL_FIELDS if name in body.model_fields_set
        },
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
    framework: FrameworkParam = DEFAULT_FRAMEWORK,
) -> list[ScopeCriterionOut]:
    criteria = await engagement_service.criteria_in_scope(
        session, tenant_id=context.tenant_id, framework_code=framework
    )
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
    framework: FrameworkParam = DEFAULT_FRAMEWORK,
) -> CoverageOut:
    report = await engagement_service.coverage(
        session, tenant_id=context.tenant_id, framework_code=framework
    )
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
    framework: FrameworkParam = DEFAULT_FRAMEWORK,
) -> DashboardOut:
    report = await engagement_service.dashboard(
        session,
        tenant_id=context.tenant_id,
        window_from=window_from,
        window_to=window_to,
        framework_code=framework,
    )
    return DashboardOut.model_validate(report)


# -- scope items: shared by every framework, in or out decided per framework (SC-0) --------


@engagement_router.get(
    "/scope-items",
    response_model=list[ScopeItemOut],
    summary="The workspace's scope items, with this framework's in or out decision",
)
async def list_scope_items(
    _principal: Annotated[Principal, Depends(require_engagement_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
    framework: FrameworkParam = DEFAULT_FRAMEWORK,
) -> list[ScopeItemOut]:
    views = await scope_service.list_items(
        session, tenant_id=context.tenant_id, framework_code=framework
    )
    return [ScopeItemOut.model_validate(v) for v in views]


@engagement_router.post(
    "/scope-items",
    response_model=ScopeItemOut,
    status_code=201,
    summary="Add an item every framework's scope can then include or leave out",
)
async def add_scope_item(
    body: ScopeItemIn,
    principal: Annotated[Principal, Depends(require_engagement_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> ScopeItemOut:
    assert principal.membership_id is not None  # noqa: S101
    item = await scope_service.add_item(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        kind=body.kind,
        name=body.name,
    )
    return ScopeItemOut(
        id=item.id,
        kind=item.kind,
        name=item.name,
        origin=item.origin,
        in_scope=None,
        reason=None,
        decided_at=None,
        others=[],
    )


@engagement_router.put(
    "/scope-items/{item_id}/decision",
    response_model=ScopeDecisionOut,
    summary="Decide whether an item is in this framework's scope, and why",
)
async def decide_scope_item(  # noqa: PLR0913, PLR0917 — path, query, body, principal, context, session
    item_id: uuid.UUID,
    body: ScopeDecisionIn,
    principal: Annotated[Principal, Depends(require_engagement_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
    framework: FrameworkParam = DEFAULT_FRAMEWORK,
) -> ScopeDecisionOut:
    assert principal.membership_id is not None  # noqa: S101
    result = await scope_service.decide(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        membership_id=principal.membership_id,
        item_id=item_id,
        framework_code=framework,
        in_scope=body.in_scope,
        reason=body.reason,
    )
    return ScopeDecisionOut.model_validate(result)


@engagement_router.post(
    "/scope-items/{item_id}/retire",
    response_model=ScopeRetireOut,
    summary="Remove an item from every framework's list, with a reason",
)
async def retire_scope_item(
    item_id: uuid.UUID,
    body: ScopeRetireIn,
    principal: Annotated[Principal, Depends(require_engagement_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> ScopeRetireOut:
    assert principal.membership_id is not None  # noqa: S101
    notices = await scope_service.retire(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        item_id=item_id,
        reason=body.reason,
    )
    return ScopeRetireOut(notices=notices)


@engagement_router.get(
    "/in-scope-for",
    response_model=dict[uuid.UUID, list[str]],
    summary="Which frameworks each asset, vendor or group is in scope for",
)
async def in_scope_for(
    _principal: Annotated[Principal, Depends(require_engagement_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
    ref_type: Annotated[str, Query(pattern="^(asset|vendor|group)$")],
) -> dict[uuid.UUID, list[str]]:
    """Derived from scope items decided in on each current engagement (SC-4)."""
    return await scope_service.in_scope_for(session, tenant_id=context.tenant_id, ref_type=ref_type)


@engagement_router.post(
    "/scope-statement/approve",
    response_model=EngagementOut,
    summary="Approve the scope statement as written",
)
async def approve_scope_statement(
    principal: Annotated[Principal, Depends(require_engagement_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
    framework: FrameworkParam = DEFAULT_FRAMEWORK,
) -> EngagementOut:
    """EN-11: the scope statement counts once a named member approves it."""
    assert principal.membership_id is not None  # noqa: S101 — tenant route
    engagement = await engagement_service.approve_scope_statement(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        membership_id=principal.membership_id,
        framework_code=framework,
    )
    return EngagementOut.model_validate(engagement)
