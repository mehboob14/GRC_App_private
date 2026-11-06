"""HTTP for the frameworks a workspace runs: the catalogue with what is added, the overlap
preview, adding a framework, and the Statement of Applicability.

Reads need ``frameworks:read``; adding a framework and deciding applicability need
``controls:manage``, the permission engagement setup already uses (deny by default, rule 7).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.deps import (
    Principal,
    TenantContext,
    get_tenant_context,
    get_tenant_session,
    require,
)
from verity.modules.audit.service import Membership
from verity.modules.compliance.framework_service import framework_service
from verity.modules.compliance.schemas import (
    ApplicabilityPut,
    ApplicabilityRowOut,
    FrameworkAdd,
    FrameworkAddedOut,
    OverlapOut,
    StatementOut,
    TenantFrameworkOut,
)

tenant_frameworks_router = APIRouter(prefix="/tenant-frameworks", tags=["compliance"])
framework_scope_router = APIRouter(prefix="/frameworks", tags=["compliance"])

require_read = require("frameworks:read")
require_manage = require("controls:manage")

_Ctx = Annotated[TenantContext, Depends(get_tenant_context)]
_Db = Annotated[AsyncSession, Depends(get_tenant_session)]

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _actor(principal: Principal) -> Membership:
    assert principal.membership_id is not None  # noqa: S101
    return Membership(principal.membership_id)


@tenant_frameworks_router.get(
    "",
    response_model=list[TenantFrameworkOut],
    summary="The framework catalogue with which frameworks this workspace has added",
)
async def list_tenant_frameworks(
    _principal: Annotated[Principal, Depends(require_read)], context: _Ctx, session: _Db
) -> list[TenantFrameworkOut]:
    views = await framework_service.list_for_tenant(session, tenant_id=context.tenant_id)
    return [TenantFrameworkOut.model_validate(v) for v in views]


@tenant_frameworks_router.post(
    "",
    response_model=FrameworkAddedOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a framework: adopt the controls it needs and link the ones already running",
)
async def add_framework(
    body: FrameworkAdd,
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> FrameworkAddedOut:
    added = await framework_service.add(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        framework_id=body.framework_id,
    )
    return FrameworkAddedOut(
        framework=TenantFrameworkOut.model_validate(added.framework),
        controls_adopted=added.controls_adopted,
        links_created=added.links_created,
    )


@framework_scope_router.get(
    "/{framework_id}/overlap",
    response_model=OverlapOut,
    summary="What adding this framework would mean for this workspace",
)
async def get_overlap(
    framework_id: uuid.UUID,
    _principal: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
) -> OverlapOut:
    view = await framework_service.overlap(
        session, tenant_id=context.tenant_id, framework_id=framework_id
    )
    return OverlapOut.model_validate(view)


@framework_scope_router.get(
    "/{framework_id}/applicability",
    response_model=StatementOut,
    summary="The Statement of Applicability: every requirement with this workspace's decision",
)
async def get_statement(
    framework_id: uuid.UUID,
    _principal: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
) -> StatementOut:
    view = await framework_service.statement(
        session, tenant_id=context.tenant_id, framework_id=framework_id
    )
    return StatementOut.model_validate(view)


@framework_scope_router.put(
    "/{framework_id}/applicability/{requirement_id}",
    response_model=ApplicabilityRowOut,
    summary="Decide whether a requirement applies, and why",
)
async def put_applicability(  # noqa: PLR0913, PLR0917 — path ids, body, principal, context, session
    framework_id: uuid.UUID,
    requirement_id: uuid.UUID,
    body: ApplicabilityPut,
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> ApplicabilityRowOut:
    row = await framework_service.set_applicability(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        framework_id=framework_id,
        requirement_id=requirement_id,
        applicable=body.applicable,
        justification=body.justification,
        provided_by=body.provided_by,
        owner_membership_id=body.owner_membership_id,
        reviewed=body.reviewed,
    )
    return ApplicabilityRowOut.model_validate(row)


@framework_scope_router.get(
    "/{framework_id}/soa.xlsx",
    summary="The Statement of Applicability as a workbook",
    response_class=Response,
)
async def download_statement(
    framework_id: uuid.UUID,
    _principal: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
) -> Response:
    data, filename = await framework_service.statement_workbook(
        session, tenant_id=context.tenant_id, framework_id=framework_id
    )
    return Response(
        content=data,
        media_type=XLSX,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
