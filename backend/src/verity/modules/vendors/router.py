"""Vendor register routes.

Four permission keys, deny-by-default (rule 7): ``vendors:read``,
``vendors:manage``, ``vendors:assess`` and ``vendors:approve``. The last two are
``vendors:assess`` guards tiering; ``vendors:approve`` is seeded by this module's
migration and is not yet used by any route — the approval gate is section 4 — so
it is deliberately absent rather than attached to a route that does not enforce
it.

Static collection paths are declared before ``/{vendor_id}`` so they are not
captured by it.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.deps import (
    Principal,
    TenantContext,
    get_tenant_context,
    get_tenant_session,
    require,
)
from verity.core.errors import NotFound
from verity.modules.audit.service import Membership
from verity.modules.vendors.schemas import (
    AcceptFindingWrite,
    AdvanceWrite,
    ApproverOut,
    ApproverPageOut,
    AssessmentOut,
    CloseFindingWrite,
    ConditionCloseWrite,
    ConditionOut,
    ContactWrite,
    ContractOut,
    ContractWrite,
    DecisionWrite,
    DocumentOut,
    DocumentWrite,
    DuplicateCheckOut,
    EngagementWrite,
    FindingOut,
    FindingPageOut,
    IntakeDecisionWrite,
    IntakeOut,
    IntakePageOut,
    IntakeWrite,
    IssuedQuestionnaireOut,
    IssueQuestionnaireWrite,
    OffboardingCompletionWrite,
    OffboardWrite,
    RemediateWrite,
    RosterOut,
    RosterWrite,
    SendBackWrite,
    SkipWrite,
    SocReviewOut,
    SocReviewWrite,
    SubprocessorOut,
    SubprocessorPageOut,
    SubprocessorWrite,
    TieringWrite,
    VendorCreate,
    VendorDetailOut,
    VendorFacetsOut,
    VendorOut,
    VendorPageOut,
    VendorWrite,
)
from verity.modules.vendors.service import (
    ConditionInput,
    ContactInput,
    ContractInput,
    DocumentInput,
    EngagementInput,
    IntakeInput,
    OffboardingCompletion,
    SocReviewInput,
    SubprocessorInput,
    TieringAnswers,
    VendorFilters,
    VendorInput,
    vendor_service,
)

vendors_router = APIRouter(prefix="/vendors", tags=["vendors"])

require_read = require("vendors:read")
require_manage = require("vendors:manage")
require_assess = require("vendors:assess")
require_approve = require("vendors:approve")

_Ctx = Annotated[TenantContext, Depends(get_tenant_context)]
_Db = Annotated[AsyncSession, Depends(get_tenant_session)]


def _actor(context: TenantContext) -> Membership:
    assert context.membership_id is not None  # noqa: S101
    return Membership(context.membership_id)


def _to_input(body: VendorWrite) -> VendorInput:
    return VendorInput(
        name=body.name,
        vendor_type=body.vendor_type,
        industry=body.industry,
        website=body.website,
        business_unit=body.business_unit,
        services_provided=body.services_provided,
        stores_pii=body.stores_pii,
        data_location=body.data_location,
        data_types_in_scope=tuple(body.data_types_in_scope),
        data_classification=body.data_classification,
        tags=tuple(body.tags),
        business_owner_membership_id=body.business_owner_membership_id,
        security_owner_membership_id=body.security_owner_membership_id,
        relationship_owner_membership_id=body.relationship_owner_membership_id,
    )


def _to_engagement(body: EngagementWrite) -> EngagementInput:
    return EngagementInput(**body.model_dump())


# -- static collection paths first --------------------------------------------


@vendors_router.get("", response_model=VendorPageOut, summary="List vendors")
async def list_vendors(  # noqa: PLR0913, PLR0917 — one query parameter per filter
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    search: str | None = None,
    vendor_type: str | None = None,
    statuses: Annotated[list[str] | None, Query()] = None,
    tiers: Annotated[list[str] | None, Query()] = None,
    classifications: Annotated[list[str] | None, Query()] = None,
    business_units: Annotated[list[str] | None, Query()] = None,
    owner: str | None = None,
    stores_pii: bool = False,
    page: int = 1,
    page_size: int = 25,
) -> VendorPageOut:
    filters = VendorFilters(
        search=search,
        vendor_type=vendor_type,
        statuses=tuple(statuses or ()),
        tiers=tuple(tiers or ()),
        classifications=tuple(classifications or ()),
        business_units=tuple(business_units or ()),
        owner=owner,
        stores_pii=stores_pii,
    )
    items, total = await vendor_service.list_vendors(
        session,
        tenant_id=context.tenant_id,
        filters=filters,
        page=page,
        page_size=page_size,
        caller_membership_id=context.membership_id,
    )
    return VendorPageOut(items=[VendorOut.model_validate(v) for v in items], total=total)


@vendors_router.get("/facets", response_model=VendorFacetsOut, summary="Register filter options")
async def facets(
    _p: Annotated[Principal, Depends(require_read)], context: _Ctx, session: _Db
) -> VendorFacetsOut:
    return VendorFacetsOut.model_validate(
        await vendor_service.facets(session, tenant_id=context.tenant_id)
    )


@vendors_router.get(
    "/duplicate-check", response_model=DuplicateCheckOut, summary="Vendors that look like this one"
)
async def duplicate_check(
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    name: str,
    website: str | None = None,
) -> DuplicateCheckOut:
    """Called by the create form as the name is typed, so the warning arrives
    before the record does rather than after it (ER ¶90)."""
    matches = await vendor_service.find_duplicates(
        session, tenant_id=context.tenant_id, name=name, website=website
    )
    return DuplicateCheckOut.model_validate({"matches": matches})


@vendors_router.post(
    "",
    response_model=VendorDetailOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a vendor",
)
async def create_vendor(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    body: VendorCreate,
) -> VendorDetailOut:
    view = await vendor_service.create_vendor(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        data=_to_input(body),
        engagement=_to_engagement(body.engagement) if body.engagement else None,
    )
    return VendorDetailOut.model_validate(view)


# -- item paths ---------------------------------------------------------------


@vendors_router.get("/{vendor_id}", response_model=VendorDetailOut, summary="Vendor detail")
async def get_vendor(
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
) -> VendorDetailOut:
    return VendorDetailOut.model_validate(
        await vendor_service.get_vendor(session, tenant_id=context.tenant_id, vendor_id=vendor_id)
    )


@vendors_router.patch("/{vendor_id}", response_model=VendorDetailOut, summary="Edit a vendor")
async def update_vendor(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    body: VendorWrite,
) -> VendorDetailOut:
    view = await vendor_service.update_vendor(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        data=_to_input(body),
    )
    return VendorDetailOut.model_validate(view)


@vendors_router.post(
    "/{vendor_id}/engagements",
    response_model=VendorDetailOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add an engagement",
)
async def add_engagement(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    body: EngagementWrite,
) -> VendorDetailOut:
    view = await vendor_service.add_engagement(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        data=_to_engagement(body),
    )
    return VendorDetailOut.model_validate(view)


@vendors_router.patch(
    "/{vendor_id}/engagements/{engagement_id}",
    response_model=VendorDetailOut,
    summary="Edit an engagement",
)
async def update_engagement(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    engagement_id: uuid.UUID,
    body: EngagementWrite,
) -> VendorDetailOut:
    view = await vendor_service.update_engagement(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        engagement_id=engagement_id,
        data=_to_engagement(body),
    )
    return VendorDetailOut.model_validate(view)


@vendors_router.post(
    "/{vendor_id}/contacts",
    response_model=VendorDetailOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a contact",
)
async def add_contact(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    body: ContactWrite,
) -> VendorDetailOut:
    view = await vendor_service.add_contact(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        data=ContactInput(**body.model_dump()),
    )
    return VendorDetailOut.model_validate(view)


# -- tiering and the lifecycle ------------------------------------------------


@vendors_router.post(
    "/{vendor_id}/engagements/{engagement_id}/tiering",
    response_model=VendorDetailOut,
    status_code=status.HTTP_201_CREATED,
    summary="Score inherent risk and lay out the lifecycle it implies",
)
async def tier_engagement(
    _p: Annotated[Principal, Depends(require_assess)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    engagement_id: uuid.UUID,
    body: TieringWrite,
) -> VendorDetailOut:
    """Tiering and stage materialisation are one call, not two.

    Spec ¶82 makes the tier decide the work. Letting a client score without laying
    out the cycle would allow exactly the state the spec forbids: a tier that has
    changed nothing.
    """
    view = await vendor_service.tier_engagement(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        engagement_id=engagement_id,
        answers=TieringAnswers(**body.model_dump()),
    )
    return VendorDetailOut.model_validate(view)


@vendors_router.post(
    "/{vendor_id}/stages/{stage_id}/advance",
    response_model=VendorDetailOut,
    summary="Complete this stage and enter the next",
)
async def advance_stage(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    stage_id: uuid.UUID,
    body: AdvanceWrite,
) -> VendorDetailOut:
    view = await vendor_service.advance_stage(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        stage_id=stage_id,
        note=body.note,
    )
    return VendorDetailOut.model_validate(view)


@vendors_router.post(
    "/{vendor_id}/stages/{stage_id}/send-back",
    response_model=VendorDetailOut,
    summary="Return the review to an earlier stage",
)
async def send_back(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    stage_id: uuid.UUID,
    body: SendBackWrite,
) -> VendorDetailOut:
    view = await vendor_service.send_back(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        stage_id=stage_id,
        to_stage=body.to_stage,
        reason=body.reason,
    )
    return VendorDetailOut.model_validate(view)


@vendors_router.post(
    "/{vendor_id}/stages/{stage_id}/skip",
    response_model=VendorDetailOut,
    summary="Skip a stage this tier does not need",
)
async def skip_stage(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    stage_id: uuid.UUID,
    body: SkipWrite,
) -> VendorDetailOut:
    view = await vendor_service.skip_stage(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        stage_id=stage_id,
        reason=body.reason,
    )
    return VendorDetailOut.model_validate(view)


# -- the questionnaire and its findings ---------------------------------------


@vendors_router.get("/findings", response_model=FindingPageOut, summary="Findings across vendors")
async def list_findings(
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID | None = None,
    statuses: Annotated[list[str] | None, Query()] = None,
) -> FindingPageOut:
    items = await vendor_service.list_findings(
        session,
        tenant_id=context.tenant_id,
        vendor_id=vendor_id,
        statuses=tuple(statuses or ()),
    )
    return FindingPageOut(items=[FindingOut.model_validate(f) for f in items], total=len(items))


@vendors_router.post(
    "/{vendor_id}/engagements/{engagement_id}/questionnaire",
    response_model=IssuedQuestionnaireOut,
    status_code=status.HTTP_201_CREATED,
    summary="Send a questionnaire to the vendor",
)
async def issue_questionnaire(
    _p: Annotated[Principal, Depends(require_assess)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    engagement_id: uuid.UUID,
    body: IssueQuestionnaireWrite,
) -> IssuedQuestionnaireOut:
    """Returns the portal link **once**.

    Only the hash is stored, so this response is the only place the token ever
    exists. Re-issuing mints a new link and revokes the old one.
    """
    issued = await vendor_service.issue_questionnaire(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        engagement_id=engagement_id,
        contact_id=body.contact_id,
        due_date=body.due_date,
        bank_code=body.bank_code,
    )
    return IssuedQuestionnaireOut.model_validate(issued)


@vendors_router.get(
    "/{vendor_id}/assessments/{assessment_id}",
    response_model=AssessmentOut,
    summary="A questionnaire and its answers",
)
async def get_assessment(
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    assessment_id: uuid.UUID,
) -> AssessmentOut:
    view = await vendor_service.get_assessment(
        session, tenant_id=context.tenant_id, assessment_id=assessment_id
    )
    if view.vendor_id != vendor_id:
        raise NotFound(
            "This questionnaire no longer exists. It may have been deleted.",
            detail=f"assessment {assessment_id} is not on vendor {vendor_id}",
        )
    return AssessmentOut.model_validate(view)


@vendors_router.post(
    "/{vendor_id}/assessments/{assessment_id}/score",
    response_model=AssessmentOut,
    summary="Score a submitted questionnaire",
)
async def score_assessment(
    _p: Annotated[Principal, Depends(require_assess)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    assessment_id: uuid.UUID,
) -> AssessmentOut:
    """Re-score on demand. The portal scores on submit, so this is for the case
    where an answer was corrected after the fact."""
    view = await vendor_service.score_assessment(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        assessment_id=assessment_id,
        vendor_id=vendor_id,
    )
    return AssessmentOut.model_validate(view)


@vendors_router.post(
    "/{vendor_id}/findings/{finding_id}/remediate",
    response_model=FindingOut,
    summary="Open a remediation task",
)
async def remediate_finding(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    finding_id: uuid.UUID,
    body: RemediateWrite,
) -> FindingOut:
    view = await vendor_service.remediate_finding(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        finding_id=finding_id,
        owner_membership_id=body.owner_membership_id,
    )
    return FindingOut.model_validate(view)


@vendors_router.post(
    "/{vendor_id}/findings/{finding_id}/accept",
    response_model=FindingOut,
    summary="Accept the risk, for a stated time",
)
async def accept_finding(
    _p: Annotated[Principal, Depends(require_approve)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    finding_id: uuid.UUID,
    body: AcceptFindingWrite,
) -> FindingOut:
    """Requires ``vendors:approve``, not ``:manage``. Accepting a risk is a
    decision somebody signs for, and the person who found it is often not the
    person entitled to live with it."""
    view = await vendor_service.accept_finding(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        finding_id=finding_id,
        until=body.until,
        rationale=body.rationale,
    )
    return FindingOut.model_validate(view)


@vendors_router.post(
    "/{vendor_id}/findings/{finding_id}/close",
    response_model=FindingOut,
    summary="Close a finding",
)
async def close_finding(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    finding_id: uuid.UUID,
    body: CloseFindingWrite,
) -> FindingOut:
    view = await vendor_service.close_finding(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        finding_id=finding_id,
        note=body.note,
    )
    return FindingOut.model_validate(view)


# -- intake, the roster and the gate ------------------------------------------


@vendors_router.get("/intake", response_model=IntakePageOut, summary="Intake queue")
async def list_intake(
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    decision: str | None = None,
) -> IntakePageOut:
    items = await vendor_service.list_intake(
        session, tenant_id=context.tenant_id, decision=decision
    )
    return IntakePageOut(items=[IntakeOut.model_validate(i) for i in items], total=len(items))


@vendors_router.post(
    "/intake",
    response_model=IntakeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Request a vendor",
)
async def request_vendor(
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    body: IntakeWrite,
) -> IntakeOut:
    """Guarded by ``vendors:read``, not ``:manage``. Anyone who can see the register
    may ask for a vendor; deciding is what needs the stronger key."""
    view = await vendor_service.request_vendor(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        data=IntakeInput(**body.model_dump()),
    )
    return IntakeOut.model_validate(view)


@vendors_router.post(
    "/intake/{request_id}/decide", response_model=IntakeOut, summary="Accept or decline a request"
)
async def decide_intake(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    request_id: uuid.UUID,
    body: IntakeDecisionWrite,
) -> IntakeOut:
    view = await vendor_service.decide_intake(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        request_id=request_id,
        approve=body.approve,
        reason=body.reason,
    )
    return IntakeOut.model_validate(view)


@vendors_router.get("/roster", response_model=RosterOut, summary="Who plays which role")
async def get_roster(
    _p: Annotated[Principal, Depends(require_read)], context: _Ctx, session: _Db
) -> RosterOut:
    roster = await vendor_service.roster(session, tenant_id=context.tenant_id)
    return RosterOut(roles={role: list(ids) for role, ids in roster.items()})


@vendors_router.post("/roster", response_model=RosterOut, summary="Assign a role")
async def set_roster_role(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    body: RosterWrite,
) -> RosterOut:
    roster = await vendor_service.set_roster_role(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        role=body.role,
        membership_id=body.membership_id,
    )
    return RosterOut(roles={role: list(ids) for role, ids in roster.items()})


@vendors_router.get(
    "/{vendor_id}/engagements/{engagement_id}/approvers",
    response_model=ApproverPageOut,
    summary="Who may decide this gate",
)
async def list_approvers(
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    engagement_id: uuid.UUID,
) -> ApproverPageOut:
    """Served so the picker can grey a disqualified name **and say why**.

    Enforcing segregation of duties only on submit means the user has written a
    rationale and attached a document before learning the rule, and learns it as an
    obstacle rather than a policy.
    """
    items = await vendor_service.approvers(
        session,
        tenant_id=context.tenant_id,
        engagement_id=engagement_id,
        vendor_id=vendor_id,
    )
    return ApproverPageOut(items=[ApproverOut.model_validate(a) for a in items])


@vendors_router.post(
    "/{vendor_id}/engagements/{engagement_id}/decision",
    response_model=VendorDetailOut,
    status_code=status.HTTP_201_CREATED,
    summary="Decide the approval gate",
)
async def decide(
    _p: Annotated[Principal, Depends(require_approve)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    engagement_id: uuid.UUID,
    body: DecisionWrite,
) -> VendorDetailOut:
    """``vendors:approve``, which is a separate key from ``:manage`` for the same
    reason ``vulnerabilities:accept`` is: deciding is not the same authority as
    doing the work."""
    view = await vendor_service.decide(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        engagement_id=engagement_id,
        decision=body.decision,
        rationale=body.rationale,
        conditions=[
            ConditionInput(
                description=c.description,
                owner_membership_id=c.owner_membership_id,
                due_date=c.due_date,
            )
            for c in body.conditions
        ],
    )
    return VendorDetailOut.model_validate(view)


@vendors_router.post(
    "/{vendor_id}/conditions/{condition_id}",
    response_model=ConditionOut,
    summary="Close or waive a condition",
)
async def close_condition(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    condition_id: uuid.UUID,
    body: ConditionCloseWrite,
) -> ConditionOut:
    view = await vendor_service.close_condition(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        condition_id=condition_id,
        status=body.status,
        waived_reason=body.waived_reason,
    )
    return ConditionOut.model_validate(view)


# -- the paperwork -------------------------------------------------------------


@vendors_router.post(
    "/{vendor_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Record a vendor document",
)
async def add_document(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    body: DocumentWrite,
) -> DocumentOut:
    view = await vendor_service.add_document(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        data=DocumentInput(**body.model_dump()),
    )
    return DocumentOut.model_validate(view)


@vendors_router.post(
    "/{vendor_id}/soc-reviews",
    response_model=SocReviewOut,
    status_code=status.HTTP_201_CREATED,
    summary="Review a SOC report",
)
async def review_soc_report(
    _p: Annotated[Principal, Depends(require_assess)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    body: SocReviewWrite,
) -> SocReviewOut:
    """**The CC9.2 artefact** (ER 110). Structured rather than a file plus a note,
    because "which of our critical vendors hold an unqualified SOC 2 Type II
    covering the audit period" has to be a query and not a reading exercise."""
    payload = body.model_dump()
    payload["tsc_included"] = tuple(payload["tsc_included"])
    view = await vendor_service.review_soc_report(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        data=SocReviewInput(**payload),
    )
    return SocReviewOut.model_validate(view)


@vendors_router.post(
    "/{vendor_id}/contracts",
    response_model=ContractOut,
    status_code=status.HTTP_201_CREATED,
    summary="Record a contract",
)
async def add_contract(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    body: ContractWrite,
) -> ContractOut:
    view = await vendor_service.add_contract(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        data=ContractInput(**body.model_dump()),
    )
    return ContractOut.model_validate(view)


@vendors_router.post(
    "/{vendor_id}/subprocessors",
    response_model=SubprocessorPageOut,
    status_code=status.HTTP_201_CREATED,
    summary="Declare a fourth party",
)
async def add_subprocessor(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    body: SubprocessorWrite,
) -> SubprocessorPageOut:
    items = await vendor_service.add_subprocessor(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        data=SubprocessorInput(**body.model_dump()),
    )
    return SubprocessorPageOut(items=[SubprocessorOut.model_validate(s) for s in items])


# -- reassessment and the exit -------------------------------------------------


@vendors_router.post(
    "/{vendor_id}/engagements/{engagement_id}/reassess",
    response_model=VendorDetailOut,
    status_code=status.HTTP_201_CREATED,
    summary="Open the next review cycle",
)
async def open_reassessment(
    _p: Annotated[Principal, Depends(require_assess)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    engagement_id: uuid.UUID,
) -> VendorDetailOut:
    view = await vendor_service.open_reassessment(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        engagement_id=engagement_id,
    )
    return VendorDetailOut.model_validate(view)


@vendors_router.post(
    "/{vendor_id}/offboarding",
    response_model=VendorDetailOut,
    status_code=status.HTTP_201_CREATED,
    summary="Start the exit",
)
async def offboard(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    body: OffboardWrite,
) -> VendorDetailOut:
    view = await vendor_service.offboard(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        engagement_id=body.engagement_id,
        reason=body.reason,
    )
    return VendorDetailOut.model_validate(view)


@vendors_router.post(
    "/{vendor_id}/offboarding/{offboarding_id}",
    response_model=VendorDetailOut,
    summary="Record and complete exit steps",
)
async def complete_offboarding(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    vendor_id: uuid.UUID,
    offboarding_id: uuid.UUID,
    body: OffboardingCompletionWrite,
) -> VendorDetailOut:
    view = await vendor_service.complete_offboarding(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        vendor_id=vendor_id,
        offboarding_id=offboarding_id,
        data=OffboardingCompletion(**body.model_dump()),
    )
    return VendorDetailOut.model_validate(view)
