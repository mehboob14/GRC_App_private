"""HTTP for the programme around an audit (guided onboarding phase 3).

Milestones, cycles, changes in the period, vendors that count and scope suggestions live under
``/engagement``; the commitments register under ``/commitments``; turning a framework off under
``/tenant-frameworks``. Reads need ``frameworks:read``; writes need ``controls:manage``, the key
that runs the programme (deny by default, rule 7).
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.deps import (
    Principal,
    TenantContext,
    get_tenant_context,
    get_tenant_session,
    require,
)
from verity.modules.audit.service import Membership
from verity.modules.compliance.models import DEFAULT_FRAMEWORK
from verity.modules.compliance.programme_service import programme_service
from verity.modules.tenancy.schemas import UtcDateTime

programme_router = APIRouter(tags=["engagement"])

require_read = require("frameworks:read")
require_manage = require("controls:manage")

_Ctx = Annotated[TenantContext, Depends(get_tenant_context)]
_Db = Annotated[AsyncSession, Depends(get_tenant_session)]
_Framework = Annotated[str, Query(alias="framework", max_length=40)]


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MilestoneOut(_Out):
    kind: str
    label: str
    planned_on: date | None
    actual_on: date | None
    from_engagement: bool


class MilestoneIn(_In):
    kind: str = Field(max_length=40)
    planned_on: date | None = None
    actual_on: date | None = None


class MilestonesIn(_In):
    milestones: list[MilestoneIn] = Field(max_length=20)


class CycleOut(_Out):
    id: uuid.UUID
    name: str
    audit_type: str
    status: str
    is_current: bool
    window_start: date | None
    window_end: date | None
    as_of_date: date | None
    audit_on: date | None
    certification_body: str | None
    created_at: UtcDateTime


class NextCycleIn(_In):
    name: str = Field(min_length=1, max_length=200)
    audit_type: str = Field(pattern="^(type_1|initial_certification|surveillance|recertification)$")


class ChangeOut(_Out):
    occurred_at: UtcDateTime
    object_type: str
    action: str
    summary: str


class CommitmentOut(_Out):
    id: uuid.UUID
    statement: str
    source_kind: str
    source_ref: str | None
    points_at: list[str]


class CommitmentIn(_In):
    statement: str = Field(min_length=1, max_length=1000)
    source_kind: str = Field(pattern="^(contract|service_levels|privacy_notice|website|other)$")
    source_ref: str | None = Field(default=None, max_length=300)
    points_at: list[str] = Field(default_factory=list, max_length=20)


class ReasonIn(_In):
    reason: str = Field(min_length=1, max_length=1000)


class EngagementVendorOut(_Out):
    vendor_id: uuid.UUID
    name: str
    tier: str | None
    role: str
    method: str | None
    note: str | None


class EngagementVendorIn(_In):
    role: str = Field(pattern="^(subservice|supplier)$")
    method: str | None = Field(default=None, pattern="^(carve_out|included)$")
    note: str | None = Field(default=None, max_length=500)


class SuggestionOut(_Out):
    ref_type: str
    ref_id: uuid.UUID
    name: str
    kind: str


class SuggestionRef(_In):
    ref_type: str = Field(pattern="^(asset|vendor)$")
    ref_id: uuid.UUID


class AcceptSuggestionsIn(_In):
    refs: list[SuggestionRef] = Field(max_length=500)


class AcceptedOut(_Out):
    added: int


class DeactivatedOut(_Out):
    controls_only_here: list[str]


def _actor(principal: Principal) -> Membership:
    assert principal.membership_id is not None  # noqa: S101 — tenant route
    return Membership(principal.membership_id)


# -- milestones and cycles ---------------------------------------------------------------


@programme_router.get("/engagement/milestones", response_model=list[MilestoneOut])
async def list_milestones(
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    framework: _Framework = DEFAULT_FRAMEWORK,
) -> list[MilestoneOut]:
    views = await programme_service.milestones(
        session, tenant_id=context.tenant_id, framework_code=framework
    )
    return [MilestoneOut.model_validate(v) for v in views]


@programme_router.put("/engagement/milestones", response_model=list[MilestoneOut])
async def save_milestones(
    body: MilestonesIn,
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    framework: _Framework = DEFAULT_FRAMEWORK,
) -> list[MilestoneOut]:
    before = {
        m.kind: m.actual_on
        for m in await programme_service.milestones(
            session, tenant_id=context.tenant_id, framework_code=framework
        )
    }
    views = await programme_service.save_milestones(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        framework_code=framework,
        changes=[(m.kind, m.planned_on, m.actual_on) for m in body.milestones],
    )
    # Guided onboarding PL-9: a milestone reached freezes the figures, beside the baseline.
    from verity.modules.onboarding.plan_service import plan_service  # noqa: PLC0415

    for v in views:
        if v.actual_on is not None and before.get(v.kind) is None:
            await plan_service.snapshot(
                session,
                tenant_id=context.tenant_id,
                actor=_actor(principal),
                label=f"{framework}: {v.label}",
            )
    return [MilestoneOut.model_validate(v) for v in views]


@programme_router.get("/engagement/cycles", response_model=list[CycleOut])
async def list_cycles(
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    framework: _Framework = DEFAULT_FRAMEWORK,
) -> list[CycleOut]:
    views = await programme_service.cycles(
        session, tenant_id=context.tenant_id, framework_code=framework
    )
    return [CycleOut.model_validate(v) for v in views]


@programme_router.post(
    "/engagement/next-cycle", response_model=CycleOut, status_code=status.HTTP_201_CREATED
)
async def start_next_cycle(
    body: NextCycleIn,
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    framework: _Framework = DEFAULT_FRAMEWORK,
) -> CycleOut:
    engagement = await programme_service.next_cycle(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        framework_code=framework,
        name=body.name,
        audit_type=body.audit_type,
    )
    return CycleOut.model_validate(engagement)


@programme_router.get("/engagement/changes", response_model=list[ChangeOut])
async def list_changes(
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    framework: _Framework = DEFAULT_FRAMEWORK,
) -> list[ChangeOut]:
    views = await programme_service.changes_in_period(
        session, tenant_id=context.tenant_id, framework_code=framework
    )
    return [ChangeOut.model_validate(v) for v in views]


# -- vendors that count and scope suggestions ----------------------------------------------


@programme_router.get("/engagement/vendors", response_model=list[EngagementVendorOut])
async def list_engagement_vendors(
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    framework: _Framework = DEFAULT_FRAMEWORK,
) -> list[EngagementVendorOut]:
    views = await programme_service.engagement_vendors(
        session, tenant_id=context.tenant_id, framework_code=framework
    )
    return [EngagementVendorOut.model_validate(v) for v in views]


@programme_router.put("/engagement/vendors/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def set_engagement_vendor(  # noqa: PLR0913, PLR0917
    vendor_id: uuid.UUID,
    body: EngagementVendorIn,
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    framework: _Framework = DEFAULT_FRAMEWORK,
) -> None:
    await programme_service.set_engagement_vendor(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        framework_code=framework,
        vendor_id=vendor_id,
        role=body.role,
        method=body.method,
        note=body.note,
    )


@programme_router.post(
    "/engagement/vendors/{vendor_id}/remove", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_engagement_vendor(  # noqa: PLR0913, PLR0917
    vendor_id: uuid.UUID,
    body: ReasonIn,
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    framework: _Framework = DEFAULT_FRAMEWORK,
) -> None:
    await programme_service.remove_engagement_vendor(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        framework_code=framework,
        vendor_id=vendor_id,
        reason=body.reason,
    )


@programme_router.get("/engagement/scope-suggestions", response_model=list[SuggestionOut])
async def list_scope_suggestions(
    _p: Annotated[Principal, Depends(require_read)], context: _Ctx, session: _Db
) -> list[SuggestionOut]:
    views = await programme_service.scope_suggestions(session, tenant_id=context.tenant_id)
    return [SuggestionOut.model_validate(v) for v in views]


@programme_router.post("/engagement/scope-suggestions/accept", response_model=AcceptedOut)
async def accept_scope_suggestions(
    body: AcceptSuggestionsIn,
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> AcceptedOut:
    added = await programme_service.accept_suggestions(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        refs=[(r.ref_type, r.ref_id) for r in body.refs],
    )
    return AcceptedOut(added=added)


# -- commitments ------------------------------------------------------------------------


@programme_router.get("/commitments", response_model=list[CommitmentOut])
async def list_commitments(
    _p: Annotated[Principal, Depends(require_read)], context: _Ctx, session: _Db
) -> list[CommitmentOut]:
    rows = await programme_service.commitments(session, tenant_id=context.tenant_id)
    return [CommitmentOut.model_validate(r) for r in rows]


@programme_router.post(
    "/commitments", response_model=CommitmentOut, status_code=status.HTTP_201_CREATED
)
async def add_commitment(
    body: CommitmentIn,
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> CommitmentOut:
    row = await programme_service.save_commitment(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        commitment_id=None,
        statement=body.statement,
        source_kind=body.source_kind,
        source_ref=body.source_ref,
        points_at=body.points_at,
    )
    return CommitmentOut.model_validate(row)


@programme_router.put("/commitments/{commitment_id}", response_model=CommitmentOut)
async def update_commitment(
    commitment_id: uuid.UUID,
    body: CommitmentIn,
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> CommitmentOut:
    row = await programme_service.save_commitment(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        commitment_id=commitment_id,
        statement=body.statement,
        source_kind=body.source_kind,
        source_ref=body.source_ref,
        points_at=body.points_at,
    )
    return CommitmentOut.model_validate(row)


@programme_router.post(
    "/commitments/{commitment_id}/retire", status_code=status.HTTP_204_NO_CONTENT
)
async def retire_commitment(
    commitment_id: uuid.UUID,
    body: ReasonIn,
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> None:
    await programme_service.retire_commitment(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        commitment_id=commitment_id,
        reason=body.reason,
    )


# -- turning a framework off ------------------------------------------------------------------


@programme_router.post(
    "/tenant-frameworks/{framework_id}/deactivate", response_model=DeactivatedOut
)
async def deactivate_framework(
    framework_id: uuid.UUID,
    body: ReasonIn,
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> DeactivatedOut:
    assert principal.membership_id is not None  # noqa: S101
    codes = await programme_service.deactivate_framework(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        membership_id=principal.membership_id,
        framework_id=framework_id,
        reason=body.reason,
    )
    return DeactivatedOut(controls_only_here=codes)
