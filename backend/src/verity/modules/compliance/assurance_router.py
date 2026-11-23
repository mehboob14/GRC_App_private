"""HTTP for assurance records and the SOC 2 description inputs (guided onboarding phase 7).

Reading needs ``frameworks:read``; recording needs ``controls:manage``, the key that runs the
programme.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, Any

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
from verity.modules.compliance.assurance_service import (
    MANAGEMENT_REVIEW_INPUTS,
    assurance_service,
)
from verity.modules.compliance.description_service import description_service
from verity.modules.compliance.models import DEFAULT_FRAMEWORK
from verity.modules.compliance.programme_service import programme_service

assurance_router = APIRouter(prefix="/engagement", tags=["engagement"])

require_read = require("frameworks:read")
require_manage = require("controls:manage")

_Ctx = Annotated[TenantContext, Depends(get_tenant_context)]
_Db = Annotated[AsyncSession, Depends(get_tenant_session)]
_Framework = Annotated[str, Query(alias="framework", max_length=40)]


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FindingOut(_Out):
    id: uuid.UUID
    grade: str
    summary: str
    due_on: date | None
    owner_membership_id: uuid.UUID | None
    response: str | None
    task_id: uuid.UUID | None
    closed_on: date | None
    closure_evidence_id: uuid.UUID | None
    verified_on: date | None
    overdue: bool


class RecordOut(_Out):
    id: uuid.UUID
    kind: str
    label: str
    starts_on: date | None
    ends_on: date | None
    performed_by_membership_id: uuid.UUID | None
    performed_by_name: str | None
    performed_by_firm: str | None
    independence_confirmed_by_membership_id: uuid.UUID | None
    scope_note: str | None
    document_id: uuid.UUID | None
    inputs: dict[str, Any]
    status: str
    findings: list[FindingOut]
    notice: str | None = None


class AssuranceOut(_Out):
    records: list[RecordOut]
    review_inputs: list[str]


class RecordIn(_In):
    kind: str = Field(max_length=40)
    label: str | None = Field(default=None, max_length=200)
    starts_on: date | None = None
    ends_on: date | None = None
    performed_by_membership_id: uuid.UUID | None = None
    performed_by_name: str | None = Field(default=None, max_length=200)
    performed_by_firm: str | None = Field(default=None, max_length=200)
    independence_confirmed_by_membership_id: uuid.UUID | None = None
    scope_note: str | None = Field(default=None, max_length=4000)
    document_id: uuid.UUID | None = None
    inputs: dict[str, bool] = Field(default_factory=dict)
    status: str = Field(default="planned", max_length=20)


class FindingIn(_In):
    grade: str = Field(max_length=20)
    summary: str = Field(min_length=1, max_length=2000)
    due_on: date | None = None
    owner_membership_id: uuid.UUID | None = None


class FindingUpdate(_In):
    response: str | None = Field(default=None, max_length=4000)
    closed_on: date | None = None
    closure_evidence_id: uuid.UUID | None = None
    verified_on: date | None = None


class AreaOut(_Out):
    key: str
    title: str
    filled: list[str]
    to_write: str


@assurance_router.get("/assurance", response_model=AssuranceOut)
async def list_records(
    _principal: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    framework: _Framework = DEFAULT_FRAMEWORK,
) -> AssuranceOut:
    rows = await assurance_service.records(
        session, tenant_id=context.tenant_id, framework_code=framework
    )
    return AssuranceOut(
        records=[RecordOut.model_validate(r) for r in rows],
        review_inputs=list(MANAGEMENT_REVIEW_INPUTS),
    )


async def _save(  # noqa: PLR0913, PLR0917 — the route context and the record
    principal: Principal,
    context: TenantContext,
    session: AsyncSession,
    framework: str,
    record_id: uuid.UUID | None,
    body: RecordIn,
) -> RecordOut:
    assert principal.membership_id is not None  # noqa: S101
    view = await assurance_service.save_record(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        framework_code=framework,
        record_id=record_id,
        values=body.model_dump(),
    )
    return RecordOut.model_validate(view)


@assurance_router.post("/assurance", response_model=RecordOut, status_code=status.HTTP_201_CREATED)
async def create_record(
    body: RecordIn,
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    framework: _Framework = DEFAULT_FRAMEWORK,
) -> RecordOut:
    return await _save(principal, context, session, framework, None, body)


@assurance_router.put("/assurance/{record_id}", response_model=RecordOut)
async def update_record(  # noqa: PLR0913, PLR0917 — path id, body, principal, context, session
    record_id: uuid.UUID,
    body: RecordIn,
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    framework: _Framework = DEFAULT_FRAMEWORK,
) -> RecordOut:
    return await _save(principal, context, session, framework, record_id, body)


@assurance_router.post(
    "/assurance/{record_id}/findings",
    response_model=FindingOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_finding(
    record_id: uuid.UUID,
    body: FindingIn,
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> FindingOut:
    """Record a finding; its corrective action task is raised with it."""
    assert principal.membership_id is not None  # noqa: S101
    view = await assurance_service.add_finding(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        record_id=record_id,
        grade=body.grade,
        summary=body.summary,
        due_on=body.due_on,
        owner_membership_id=body.owner_membership_id,
    )
    return FindingOut.model_validate(view)


@assurance_router.put("/assurance/findings/{finding_id}", response_model=FindingOut)
async def update_finding(
    finding_id: uuid.UUID,
    body: FindingUpdate,
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> FindingOut:
    assert principal.membership_id is not None  # noqa: S101
    view = await assurance_service.update_finding(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        membership_id=principal.membership_id,
        finding_id=finding_id,
        response=body.response,
        closed_on=body.closed_on,
        closure_evidence_id=body.closure_evidence_id,
        verified_on=body.verified_on,
    )
    return FindingOut.model_validate(view)


@assurance_router.get("/description-inputs", response_model=list[AreaOut])
async def description_inputs(
    _principal: Annotated[Principal, Depends(require_read)], context: _Ctx, session: _Db
) -> list[AreaOut]:
    """What your records already say for each area of the SOC 2 system description (EN-6)."""
    rows = await description_service.inputs(session, tenant_id=context.tenant_id)
    return [AreaOut.model_validate(r) for r in rows]


class PeriodicRowOut(_Out):
    control_id: uuid.UUID
    code: str
    name: str
    cadence: str
    needed: int
    found: int


class PeriodicOut(_Out):
    start: date | None
    end: date | None
    label: str | None
    rows: list[PeriodicRowOut]


@assurance_router.get("/periodic", response_model=PeriodicOut)
async def periodic(
    _principal: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    framework: _Framework = DEFAULT_FRAMEWORK,
) -> PeriodicOut:
    """Annual, quarterly and monthly controls planned against the audit period (EN-8)."""
    view = await programme_service.periodic(
        session, tenant_id=context.tenant_id, framework_code=framework
    )
    return PeriodicOut.model_validate(view)
