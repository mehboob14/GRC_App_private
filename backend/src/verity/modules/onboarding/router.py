"""HTTP for Get Started.

The status read needs only ``tenant:read``, which every built in role holds, so the landing
page loads for everyone. What each step shows then follows the caller's own permissions
inside the service. Skipping and reopening a step need ``controls:manage``, the key that
runs the programme today.
"""

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
from verity.modules.onboarding import assist
from verity.modules.onboarding.ownership_service import ownership_service
from verity.modules.onboarding.plan_service import plan_service
from verity.modules.onboarding.proposals_service import proposals_service
from verity.modules.onboarding.schemas import (
    AppliedOut,
    ApplyOwnersIn,
    AssignSectionIn,
    AssistIn,
    BaselineAnswerIn,
    BaselineOut,
    ConnectionSuggestionOut,
    DecidedOut,
    DecideIn,
    DraftOut,
    MyPartOut,
    OwnerFunctionIn,
    OwnershipOut,
    PlanOut,
    PrefillOut,
    ProposalsOut,
    RaisedOut,
    RequiredOut,
    SetupIn,
    SetupOut,
    SkipIn,
    SnapshotOut,
    StatusOut,
)
from verity.modules.onboarding.service import onboarding_service

onboarding_router = APIRouter(prefix="/onboarding", tags=["onboarding"])

require_status_read = require("tenant:read")
require_step_manage = require("controls:manage")
require_programme_read = require("frameworks:read")

_Ctx = Annotated[TenantContext, Depends(get_tenant_context)]
_Db = Annotated[AsyncSession, Depends(get_tenant_session)]
_StepKey = Annotated[str, Path(max_length=80, pattern=r"^[a-z_]+(:[A-Za-z0-9_]+)?$")]


@onboarding_router.get("/guidance-notes/{code}", response_model=list[str])
async def get_guidance_notes(
    code: Annotated[str, Path(max_length=10, pattern=r"^[A-Z]{2,4}-\d{2}$")],
    _principal: Annotated[Principal, Depends(require_programme_read)],
    context: _Ctx,
    session: _Db,
) -> list[str]:
    """Notes for this control from the company profile (CL-7 guidance switches)."""
    from verity.modules.onboarding.rules import notes_for  # noqa: PLC0415
    from verity.modules.tenancy.service import tenancy_service  # noqa: PLC0415

    profile = await tenancy_service.get_own_company_profile(session, context.tenant_id)
    return notes_for(code, dict(profile.answers or {}))


@onboarding_router.get("/scope-notes", response_model=list[str])
async def get_scope_notes(
    _principal: Annotated[Principal, Depends(require_programme_read)], context: _Ctx, session: _Db
) -> list[str]:
    """Control codes no requirement in the current scope needs (CL-7)."""
    return await onboarding_service.scope_notes(session, tenant_id=context.tenant_id)


@onboarding_router.get("/profile-prefill", response_model=list[PrefillOut])
async def get_profile_prefill(
    _principal: Annotated[Principal, Depends(require_status_read)], context: _Ctx, session: _Db
) -> list[PrefillOut]:
    """Answers the workspace already implies, for a person to confirm (PR-7)."""
    rows = await onboarding_service.profile_prefill(session, tenant_id=context.tenant_id)
    return [PrefillOut.model_validate(r) for r in rows]


@onboarding_router.get("/my-part", response_model=MyPartOut, summary="Open items assigned to you")
async def get_my_part(
    principal: Annotated[Principal, Depends(require_status_read)], context: _Ctx, session: _Db
) -> MyPartOut:
    assert principal.membership_id is not None  # noqa: S101
    view = await onboarding_service.my_part(
        session, tenant_id=context.tenant_id, membership_id=principal.membership_id
    )
    return MyPartOut.model_validate(view)


@onboarding_router.get(
    "/status",
    response_model=StatusOut,
    summary="Get Started, computed from the workspace's records",
)
async def get_status(
    principal: Annotated[Principal, Depends(require_status_read)], context: _Ctx, session: _Db
) -> StatusOut:
    view = await onboarding_service.status(
        session, tenant_id=context.tenant_id, principal=principal
    )
    return StatusOut.model_validate(view)


@onboarding_router.post(
    "/steps/{step_key}/skip",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Skip a step, with the reason shown to everyone",
)
async def skip_step(
    step_key: _StepKey,
    body: SkipIn,
    principal: Annotated[Principal, Depends(require_step_manage)],
    context: _Ctx,
    session: _Db,
) -> None:
    assert principal.membership_id is not None  # noqa: S101 — tenant route
    await onboarding_service.skip(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        membership_id=principal.membership_id,
        step_key=step_key,
        reason=body.reason,
    )


@onboarding_router.post(
    "/steps/{step_key}/reopen",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reopen a skipped step",
)
async def reopen_step(
    step_key: _StepKey,
    principal: Annotated[Principal, Depends(require_step_manage)],
    context: _Ctx,
    session: _Db,
) -> None:
    assert principal.membership_id is not None  # noqa: S101 — tenant route
    await onboarding_service.reopen(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        membership_id=principal.membership_id,
        step_key=step_key,
    )


# -- owner functions (OW-1, OW-2) ---------------------------------------------------------

_FunctionKey = Annotated[str, Path(max_length=40, pattern=r"^[a-z_]+$")]


@onboarding_router.get("/owner-functions", response_model=OwnershipOut)
async def get_owner_functions(
    _principal: Annotated[Principal, Depends(require_programme_read)], context: _Ctx, session: _Db
) -> OwnershipOut:
    view = await ownership_service.view(session, tenant_id=context.tenant_id)
    return OwnershipOut.model_validate(view)


@onboarding_router.put("/owner-functions/{function_key}", status_code=status.HTTP_204_NO_CONTENT)
async def put_owner_function(
    function_key: _FunctionKey,
    body: OwnerFunctionIn,
    principal: Annotated[Principal, Depends(require_step_manage)],
    context: _Ctx,
    session: _Db,
) -> None:
    assert principal.membership_id is not None  # noqa: S101
    await ownership_service.assign(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        function_key=function_key,
        membership_id=body.membership_id,
    )


@onboarding_router.post("/owner-functions/apply", response_model=AppliedOut)
async def apply_owner_functions(
    body: ApplyOwnersIn,
    principal: Annotated[Principal, Depends(require_step_manage)],
    context: _Ctx,
    session: _Db,
) -> AppliedOut:
    assert principal.membership_id is not None  # noqa: S101
    changed = await ownership_service.apply(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        keep_existing=body.keep_existing,
    )
    return AppliedOut(changed=changed)


@onboarding_router.get("/required-documents", response_model=RequiredOut)
async def get_required_documents(
    _principal: Annotated[Principal, Depends(require("documents:read"))],
    context: _Ctx,
    session: _Db,
) -> RequiredOut:
    """The documents and records the workspace's frameworks expect, with their state (RD-1)."""
    view = await onboarding_service.required_documents(session, tenant_id=context.tenant_id)
    return RequiredOut.model_validate(view)


# -- suggestions from the profile (PL-1 to PL-5) -------------------------------------------


@onboarding_router.get("/proposals", response_model=ProposalsOut)
async def get_proposals(
    _principal: Annotated[Principal, Depends(require_programme_read)], context: _Ctx, session: _Db
) -> ProposalsOut:
    """Suggestions computed from the profile, with what people decided about them."""
    view = await proposals_service.view(session, tenant_id=context.tenant_id)
    return ProposalsOut.model_validate(view)


@onboarding_router.post("/proposals/decide", response_model=DecidedOut)
async def decide_proposals(
    body: DecideIn,
    principal: Annotated[Principal, Depends(require_step_manage)],
    context: _Ctx,
    session: _Db,
) -> DecidedOut:
    """Accept or reject suggestions. Each accepted one is applied through the service that
    owns the record and audited there; the decision is audited here."""
    assert principal.membership_id is not None  # noqa: S101
    decided = await proposals_service.decide(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        membership_id=principal.membership_id,
        keys=body.keys,
        accept=body.accept,
        reason=body.reason,
        bulk=body.bulk,
    )
    return DecidedOut(decided=decided)


# -- baseline, snapshots and the work plan (PL-6 to PL-12) ---------------------------------


@onboarding_router.get("/baseline", response_model=BaselineOut)
async def get_baseline(
    _principal: Annotated[Principal, Depends(require_programme_read)], context: _Ctx, session: _Db
) -> BaselineOut:
    return BaselineOut.model_validate(
        await plan_service.baseline(session, tenant_id=context.tenant_id)
    )


@onboarding_router.put("/baseline/controls/{control_id}", status_code=status.HTTP_204_NO_CONTENT)
async def answer_baseline(
    control_id: uuid.UUID,
    body: BaselineAnswerIn,
    principal: Annotated[Principal, Depends(require_step_manage)],
    context: _Ctx,
    session: _Db,
) -> None:
    assert principal.membership_id is not None  # noqa: S101
    await plan_service.answer(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        membership_id=principal.membership_id,
        control_id=control_id,
        answer=body.answer,
        note=body.note,
    )


@onboarding_router.post("/baseline/complete", response_model=BaselineOut)
async def complete_baseline(
    principal: Annotated[Principal, Depends(require_step_manage)], context: _Ctx, session: _Db
) -> BaselineOut:
    assert principal.membership_id is not None  # noqa: S101
    view = await plan_service.complete(
        session, tenant_id=context.tenant_id, actor=Membership(principal.membership_id)
    )
    return BaselineOut.model_validate(view)


@onboarding_router.get("/snapshots", response_model=list[SnapshotOut])
async def list_snapshots(
    _principal: Annotated[Principal, Depends(require_programme_read)], context: _Ctx, session: _Db
) -> list[SnapshotOut]:
    rows = await plan_service.snapshots(session, tenant_id=context.tenant_id)
    return [SnapshotOut.model_validate(r) for r in rows]


@onboarding_router.get("/plan", response_model=PlanOut)
async def get_plan(
    _principal: Annotated[Principal, Depends(require_programme_read)], context: _Ctx, session: _Db
) -> PlanOut:
    return PlanOut.model_validate(await plan_service.plan(session, tenant_id=context.tenant_id))


@onboarding_router.post("/plan/approve", response_model=RaisedOut)
async def approve_plan(
    principal: Annotated[Principal, Depends(require_step_manage)], context: _Ctx, session: _Db
) -> RaisedOut:
    """Raise the plan's tasks. Approving again raises only what is new."""
    assert principal.membership_id is not None  # noqa: S101
    raised = await plan_service.approve_plan(
        session, tenant_id=context.tenant_id, actor=Membership(principal.membership_id)
    )
    return RaisedOut(raised=raised)


@onboarding_router.get("/connections", response_model=list[ConnectionSuggestionOut])
async def get_connection_suggestions(
    _principal: Annotated[Principal, Depends(require("connectors:read"))],
    context: _Ctx,
    session: _Db,
) -> list[ConnectionSuggestionOut]:
    """Systems the profile names, matched to the integration catalogue (PL-10)."""
    rows = await plan_service.connections(session, tenant_id=context.tenant_id)
    return [ConnectionSuggestionOut.model_validate(r) for r in rows]


# -- the setup flow's place (part 3 section 3) ---------------------------------------------


@onboarding_router.get("/setup", response_model=SetupOut)
async def get_setup(
    _principal: Annotated[Principal, Depends(require_status_read)], context: _Ctx, session: _Db
) -> SetupOut:
    return SetupOut.model_validate(await plan_service.setup(session, tenant_id=context.tenant_id))


@onboarding_router.put("/setup", response_model=SetupOut)
async def save_setup(
    body: SetupIn,
    principal: Annotated[Principal, Depends(require_step_manage)],
    context: _Ctx,
    session: _Db,
) -> SetupOut:
    assert principal.membership_id is not None  # noqa: S101
    view = await plan_service.save_setup(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        start_point=body.start_point,
        setup_step=body.setup_step,
        complete=body.complete,
    )
    return SetupOut.model_validate(view)


# -- AI drafts (AI-1 to AI-4, AI-6) ----------------------------------------------------------


@onboarding_router.post("/assist", response_model=DraftOut)
async def draft_text(
    body: AssistIn,
    principal: Annotated[Principal, Depends(require_step_manage)],
    context: _Ctx,
    session: _Db,
) -> DraftOut:
    """A draft for a person to edit. Nothing is saved but the draft's origin in the audit log."""
    assert principal.membership_id is not None  # noqa: S101
    result = await assist.draft(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        kind=body.kind,
        subject=body.subject,
    )
    return DraftOut.model_validate(result)


@onboarding_router.post("/profile-sections/{section}/assign", response_model=RaisedOut)
async def assign_profile_section(
    section: Annotated[str, Path(max_length=40, pattern=r"^[a-z_]+$")],
    body: AssignSectionIn,
    principal: Annotated[Principal, Depends(require("tenant:manage"))],
    context: _Ctx,
    session: _Db,
) -> RaisedOut:
    """Ask a member to answer one section of the profile, as a task."""
    assert principal.membership_id is not None  # noqa: S101
    made = await plan_service.assign_section(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        section=section,
        membership_id=body.membership_id,
    )
    return RaisedOut(raised=1 if made else 0)
