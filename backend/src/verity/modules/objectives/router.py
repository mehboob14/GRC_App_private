"""HTTP for assessment objectives. Reading needs ``frameworks:read``; recording a decision or
tagging evidence needs ``controls:manage``."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.deps import (
    Principal,
    TenantContext,
    get_tenant_context,
    get_tenant_session,
    require,
)
from verity.modules.audit.service import Membership
from verity.modules.objectives.schemas import (
    ComparisonOut,
    ControlObjectivesOut,
    FrameworkObjectivesOut,
    NextItemOut,
    NotApplicableIn,
    ObjectiveOut,
    OverviewOut,
    TagIn,
)
from verity.modules.objectives.service import objectives_service

objectives_router = APIRouter(prefix="/objectives", tags=["objectives"])

require_read = require("frameworks:read")
require_manage = require("controls:manage")

_Ctx = Annotated[TenantContext, Depends(get_tenant_context)]
_Db = Annotated[AsyncSession, Depends(get_tenant_session)]
_Code = Annotated[str, Path(max_length=20, pattern=r"^[A-Z]{2,4}-\d{2}\.[A-Z]$")]
_Artifact = Annotated[str, Path(max_length=120, pattern=r"^[a-z0-9-]+$")]


@objectives_router.get("", response_model=OverviewOut, summary="Objectives across the workspace")
async def overview(
    _principal: Annotated[Principal, Depends(require_read)], context: _Ctx, session: _Db
) -> OverviewOut:
    view = await objectives_service.overview(session, tenant_id=context.tenant_id)
    return OverviewOut(
        frameworks=[FrameworkObjectivesOut.model_validate(f) for f in view.frameworks],
        controls_with_objectives=view.controls_with_objectives,
        controls_total=view.controls_total,
        next=[
            NextItemOut(
                control_id=c.control_id,
                control_code=c.code,
                control_name=c.name,
                objective=ObjectiveOut.model_validate(o),
            )
            for c, o in view.next
        ],
        review_status=view.review_status,
    )


@objectives_router.get(
    "/comparison", response_model=ComparisonOut, summary="Readiness today beside objectives"
)
async def comparison(
    _principal: Annotated[Principal, Depends(require_read)], context: _Ctx, session: _Db
) -> ComparisonOut:
    view = await objectives_service.comparison(session, tenant_id=context.tenant_id)
    return ComparisonOut.model_validate(view)


@objectives_router.get("/controls/{control_id}", response_model=ControlObjectivesOut | None)
async def for_control(
    control_id: uuid.UUID,
    _principal: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
) -> ControlObjectivesOut | None:
    """A control's objectives with outcomes and next steps; null when it has none yet."""
    view = await objectives_service.for_control(
        session, tenant_id=context.tenant_id, control_id=control_id
    )
    return ControlObjectivesOut.model_validate(view) if view else None


@objectives_router.post("/{code}/not-applicable", status_code=status.HTTP_204_NO_CONTENT)
async def mark_not_applicable(
    code: _Code,
    body: NotApplicableIn,
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> None:
    assert principal.membership_id is not None  # noqa: S101
    await objectives_service.mark_not_applicable(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        membership_id=principal.membership_id,
        objective_code=code,
        reason=body.reason,
    )


@objectives_router.post("/{code}/applies-again", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw(
    code: _Code,
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> None:
    assert principal.membership_id is not None  # noqa: S101
    await objectives_service.withdraw(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        membership_id=principal.membership_id,
        objective_code=code,
    )


@objectives_router.put("/artifacts/{artifact_key}/evidence", status_code=status.HTTP_204_NO_CONTENT)
async def tag_evidence(
    artifact_key: _Artifact,
    body: TagIn,
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> None:
    """Mark an evidence row as this record, or unmark it."""
    assert principal.membership_id is not None  # noqa: S101
    await objectives_service.tag_evidence(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        membership_id=principal.membership_id,
        evidence_id=body.evidence_id,
        artifact_key=artifact_key,
        on=body.on,
    )
