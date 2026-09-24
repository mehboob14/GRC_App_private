"""HTTP for linked records on assets, vulnerabilities, controls and documents.

Each record type gets the same three routes under its own path, guarded by its
own module's keys (rule 7): read needs the module's read key, drawing or
removing a link needs its manage key. The service adds what a flat key cannot
say: manage on the module that owns the pair, and read on the other end.
Raising a risk from a finding needs ``risks:manage``.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.deps import (
    Principal,
    TenantContext,
    get_tenant_context,
    get_tenant_session,
    require,
)
from verity.modules.audit.service import Membership
from verity.modules.linkage.schemas import (
    LinkedRecordsOut,
    LinkWrite,
    RaisedRiskOut,
    RaiseRiskWrite,
)
from verity.modules.linkage.service import (
    MANAGE_PERMISSION,
    READ_PERMISSION,
    linkage_service,
)

linkage_router = APIRouter(tags=["linkage"])

_Ctx = Annotated[TenantContext, Depends(get_tenant_context)]
_Db = Annotated[AsyncSession, Depends(get_tenant_session)]

_ANCHORS: tuple[tuple[str, str], ...] = (
    ("asset", "/assets"),
    ("vulnerability", "/vulnerabilities"),
    ("control", "/controls"),
    ("document", "/documents"),
)


def _actor(context: TenantContext) -> Membership:
    assert context.membership_id is not None  # noqa: S101
    return Membership(context.membership_id)


def _mount(anchor_type: str, base: str) -> None:
    # Each anchor's keys are known only here, so its dependencies are defaults
    # rather than Annotated metadata: with postponed annotations a closure
    # variable inside a string annotation cannot be resolved by FastAPI.
    read = Depends(require(READ_PERMISSION[anchor_type]))
    manage = Depends(require(MANAGE_PERMISSION[anchor_type]))

    @linkage_router.get(
        f"{base}/{{anchor_id}}/links",
        response_model=LinkedRecordsOut,
        name=f"{anchor_type}_linked_records",
        summary="Records linked to this one",
    )
    async def read_links(
        anchor_id: uuid.UUID,
        context: _Ctx,
        session: _Db,
        principal: Principal = read,
    ) -> LinkedRecordsOut:
        view = await linkage_service.records(
            session,
            tenant_id=context.tenant_id,
            anchor_type=anchor_type,
            anchor_id=anchor_id,
            permissions=principal.permissions,
        )
        return LinkedRecordsOut.model_validate(view)

    @linkage_router.post(
        f"{base}/{{anchor_id}}/links",
        response_model=LinkedRecordsOut,
        status_code=status.HTTP_201_CREATED,
        name=f"{anchor_type}_link_record",
        summary="Link another record to this one",
    )
    async def add_link(
        anchor_id: uuid.UUID,
        body: LinkWrite,
        context: _Ctx,
        session: _Db,
        principal: Principal = manage,
    ) -> LinkedRecordsOut:
        view = await linkage_service.link(
            session,
            tenant_id=context.tenant_id,
            actor=_actor(context),
            anchor_type=anchor_type,
            anchor_id=anchor_id,
            target_type=body.target_type,
            target_id=body.target_id,
            permissions=principal.permissions,
        )
        return LinkedRecordsOut.model_validate(view)

    @linkage_router.delete(
        f"{base}/{{anchor_id}}/links/{{link_id}}",
        response_model=LinkedRecordsOut,
        name=f"{anchor_type}_unlink_record",
        summary="Remove a link from this record",
    )
    async def remove_link(
        anchor_id: uuid.UUID,
        link_id: uuid.UUID,
        context: _Ctx,
        session: _Db,
        principal: Principal = manage,
    ) -> LinkedRecordsOut:
        view = await linkage_service.unlink(
            session,
            tenant_id=context.tenant_id,
            actor=_actor(context),
            anchor_type=anchor_type,
            anchor_id=anchor_id,
            link_id=link_id,
            permissions=principal.permissions,
        )
        return LinkedRecordsOut.model_validate(view)


for _anchor_type, _base in _ANCHORS:
    _mount(_anchor_type, _base)


@linkage_router.post(
    "/vulnerabilities/{instance_id}/raise-risk",
    response_model=RaisedRiskOut,
    status_code=status.HTTP_201_CREATED,
    summary="Raise a risk from this finding",
)
async def raise_risk(
    instance_id: uuid.UUID,
    body: RaiseRiskWrite,
    principal: Annotated[Principal, Depends(require("risks:manage"))],
    context: _Ctx,
    session: _Db,
) -> RaisedRiskOut:
    view = await linkage_service.raise_risk(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        instance_id=instance_id,
        title=body.title,
        register_id=body.register_id,
        permissions=principal.permissions,
    )
    return RaisedRiskOut.model_validate(view)
