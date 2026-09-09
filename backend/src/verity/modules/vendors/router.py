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
from verity.modules.audit.service import Membership
from verity.modules.vendors.schemas import (
    AdvanceWrite,
    ContactWrite,
    DuplicateCheckOut,
    EngagementWrite,
    SendBackWrite,
    SkipWrite,
    TieringWrite,
    VendorCreate,
    VendorDetailOut,
    VendorFacetsOut,
    VendorOut,
    VendorPageOut,
    VendorWrite,
)
from verity.modules.vendors.service import (
    ContactInput,
    EngagementInput,
    TieringAnswers,
    VendorFilters,
    VendorInput,
    vendor_service,
)

vendors_router = APIRouter(prefix="/vendors", tags=["vendors"])

require_read = require("vendors:read")
require_manage = require("vendors:manage")
require_assess = require("vendors:assess")

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
