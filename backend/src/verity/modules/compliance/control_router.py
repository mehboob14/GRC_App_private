"""HTTP for the tenant control library: parse, authorise, call the service, shape.

Reads declare ``frameworks:read``; writes declare ``controls:manage``. Deny by
default (rule 7) — a route with no permission dependency fails CI.

The tenant is resolved from the session's :class:`TenantContext`, never from a
parameter: there is no route by which one tenant addresses another's controls.
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
from verity.modules.compliance.control_service import control_service
from verity.modules.compliance.models import (
    CONTROL_CATEGORIES,
    CONTROL_STATUSES,
    CONTROL_SUB_TYPES,
    CONTROL_TYPES,
)
from verity.modules.compliance.schemas import (
    AdoptLibraryRequest,
    AdoptLibraryResponse,
    ControlCreate,
    ControlDisable,
    ControlOut,
    ControlUpdate,
    ControlVocabularyOut,
)

controls_router = APIRouter(prefix="/controls", tags=["controls"])

require_controls_read = require("frameworks:read")
require_controls_manage = require("controls:manage")


def _actor(principal: Principal) -> Membership:
    assert principal.membership_id is not None  # noqa: S101
    return Membership(principal.membership_id)


@controls_router.get(
    "/vocabulary",
    response_model=ControlVocabularyOut,
    summary="The closed vocabularies a control can take",
)
async def get_vocabulary(
    _principal: Annotated[Principal, Depends(require_controls_read)],
) -> ControlVocabularyOut:
    # Served from the same constants the CHECK constraints are built from, so
    # the UI cannot offer a value the database would reject.
    return ControlVocabularyOut(
        categories=list(CONTROL_CATEGORIES),
        control_types=list(CONTROL_TYPES),
        control_sub_types=list(CONTROL_SUB_TYPES),
        statuses=list(CONTROL_STATUSES),
    )


@controls_router.get(
    "",
    response_model=list[ControlOut],
    summary="The tenant's control library, with each control's mapped criteria",
)
async def list_controls(  # noqa: PLR0913, PLR0917 — one parameter per filter
    _principal: Annotated[Principal, Depends(require_controls_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
    control_status: Annotated[str | None, Query(alias="status")] = None,
    category: str | None = None,
    control_type: str | None = None,
    control_sub_type: str | None = None,
    owner_membership_id: uuid.UUID | None = None,
    include_disabled: bool = False,
    search: str | None = None,
) -> list[ControlOut]:
    views = await control_service.list_controls(
        session,
        tenant_id=context.tenant_id,
        status=control_status,
        category=category,
        control_type=control_type,
        control_sub_type=control_sub_type,
        owner_membership_id=owner_membership_id,
        include_disabled=include_disabled,
        search=search,
    )
    return [ControlOut.model_validate(view) for view in views]


@controls_router.get("/{control_id}", response_model=ControlOut, summary="One control")
async def get_control(
    control_id: uuid.UUID,
    _principal: Annotated[Principal, Depends(require_controls_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> ControlOut:
    view = await control_service.get_control(
        session, tenant_id=context.tenant_id, control_id=control_id
    )
    return ControlOut.model_validate(view)


@controls_router.post(
    "/adopt",
    response_model=AdoptLibraryResponse,
    summary="Instantiate the shipped templates into this tenant's library",
)
async def adopt_library(
    body: AdoptLibraryRequest,
    principal: Annotated[Principal, Depends(require_controls_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> AdoptLibraryResponse:
    result = await control_service.instantiate_library(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        requirement_ids=body.requirement_ids,
    )
    return AdoptLibraryResponse.model_validate(result)


@controls_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ControlOut,
    summary="Author a custom control",
)
async def create_control(
    body: ControlCreate,
    principal: Annotated[Principal, Depends(require_controls_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> ControlOut:
    view = await control_service.create_custom_control(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        code=body.code,
        name=body.name,
        description=body.description,
        category=body.category,
        control_type=body.control_type,
        control_sub_type=body.control_sub_type,
        implementation_guidance=body.implementation_guidance,
        owner_membership_id=body.owner_membership_id,
        requirement_ids=body.requirement_ids,
    )
    return ControlOut.model_validate(view)


@controls_router.patch("/{control_id}", response_model=ControlOut, summary="Edit a control")
async def update_control(
    control_id: uuid.UUID,
    body: ControlUpdate,
    principal: Annotated[Principal, Depends(require_controls_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> ControlOut:
    view = await control_service.update_control(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        control_id=control_id,
        name=body.name,
        description=body.description,
        implementation_guidance=body.implementation_guidance,
        category=body.category,
        control_type=body.control_type,
        control_sub_type=body.control_sub_type,
        status=body.status,
        owner_membership_id=body.owner_membership_id,
        clear_owner=body.clear_owner,
        requirement_ids=body.requirement_ids,
    )
    return ControlOut.model_validate(view)


@controls_router.post(
    "/{control_id}/disable",
    response_model=ControlOut,
    summary="Retire a control with a recorded justification (never deleted)",
)
async def disable_control(
    control_id: uuid.UUID,
    body: ControlDisable,
    principal: Annotated[Principal, Depends(require_controls_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> ControlOut:
    view = await control_service.disable_control(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        control_id=control_id,
        reason=body.reason,
    )
    return ControlOut.model_validate(view)


@controls_router.post(
    "/{control_id}/enable",
    response_model=ControlOut,
    summary="Return a retired control to the working library",
)
async def enable_control(
    control_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_controls_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> ControlOut:
    view = await control_service.enable_control(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        control_id=control_id,
    )
    return ControlOut.model_validate(view)
