"""HTTP for the Asset module.

Reads need ``assets:read``; creating, editing, transitioning and reviewing need
``assets:manage``; a bulk import needs ``assets:import``; decommissioning needs
``assets:decommission`` (deny-by-default, rule 7). Static collection paths are
declared before ``/{asset_id}`` so they are not captured by it.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.deps import (
    Principal,
    TenantContext,
    get_tenant_context,
    get_tenant_session,
    require,
)
from verity.modules.assets.schemas import (
    AssetDetailOut,
    AssetOut,
    AssetPageOut,
    AssetSummaryOut,
    AssetWrite,
    DecommissionRequest,
    FacetsOut,
    ImportRequest,
    ImportResultOut,
    RelationshipOut,
    RelationshipPageOut,
    RelationshipWrite,
    SheetOut,
    TransitionRequest,
)
from verity.modules.assets.service import (
    AssetFilters,
    AssetInput,
    RelationshipInput,
    asset_service,
    read_sheet,
)
from verity.modules.audit.service import Membership

assets_router = APIRouter(prefix="/assets", tags=["assets"])

require_read = require("assets:read")
require_manage = require("assets:manage")
require_import = require("assets:import")
require_decommission = require("assets:decommission")

_Ctx = Annotated[TenantContext, Depends(get_tenant_context)]
_Db = Annotated[AsyncSession, Depends(get_tenant_session)]


def _actor(context: TenantContext) -> Membership:
    assert context.membership_id is not None  # noqa: S101
    return Membership(context.membership_id)


def _to_input(body: AssetWrite) -> AssetInput:
    # An import row carries its starting status on top of the write fields.
    return AssetInput(**body.model_dump(exclude={"status"}))


# -- static collection paths first -------------------------------------------


@assets_router.get("", response_model=AssetPageOut, summary="List assets")
async def list_assets(  # noqa: PLR0913, PLR0917 — one query parameter per filter
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    search: str | None = None,
    asset_type: str | None = None,
    tiers: Annotated[list[str] | None, Query()] = None,
    statuses: Annotated[list[str] | None, Query()] = None,
    environments: Annotated[list[str] | None, Query()] = None,
    classifications: Annotated[list[str] | None, Query()] = None,
    exposure: str | None = None,
    owner: str | None = None,
    needs_attention: bool = False,
    page: int = 1,
    page_size: int = 25,
) -> AssetPageOut:
    filters = AssetFilters(
        search=search,
        asset_type=asset_type,
        tiers=tuple(tiers or ()),
        statuses=tuple(statuses or ()),
        environments=tuple(environments or ()),
        classifications=tuple(classifications or ()),
        exposure=exposure,
        owner=owner,
        needs_attention=needs_attention,
    )
    items, total = await asset_service.list_assets(
        session,
        tenant_id=context.tenant_id,
        filters=filters,
        page=page,
        page_size=page_size,
        caller_membership_id=context.membership_id,
    )
    return AssetPageOut(items=[AssetOut.model_validate(v) for v in items], total=total)


@assets_router.get("/summary", response_model=AssetSummaryOut, summary="Overview dashboard")
async def summary(
    _p: Annotated[Principal, Depends(require_read)], context: _Ctx, session: _Db
) -> AssetSummaryOut:
    return AssetSummaryOut.model_validate(
        await asset_service.summary(session, tenant_id=context.tenant_id)
    )


@assets_router.get("/facets", response_model=FacetsOut, summary="Filter facet counts")
async def facets(
    _p: Annotated[Principal, Depends(require_read)], context: _Ctx, session: _Db
) -> FacetsOut:
    return FacetsOut.model_validate(
        await asset_service.facets(session, tenant_id=context.tenant_id)
    )


@assets_router.post("/import", response_model=ImportResultOut, summary="Bulk import assets")
async def import_assets(
    _p: Annotated[Principal, Depends(require_import)],
    context: _Ctx,
    session: _Db,
    body: ImportRequest,
) -> ImportResultOut:
    created = await asset_service.import_assets(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        rows=[_to_input(row) for row in body.rows],
        statuses=[row.status for row in body.rows],
    )
    return ImportResultOut(created=created)


@assets_router.post("/import/sheet", response_model=SheetOut, summary="Read an Excel import file")
async def read_import_sheet(
    _p: Annotated[Principal, Depends(require_import)],
    file: Annotated[UploadFile, File()],
) -> SheetOut:
    return SheetOut(rows=read_sheet(await file.read()))


@assets_router.post(
    "",
    response_model=AssetDetailOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an asset",
)
async def create_asset(
    _p: Annotated[Principal, Depends(require_manage)], context: _Ctx, session: _Db, body: AssetWrite
) -> AssetDetailOut:
    view = await asset_service.create_asset(
        session, tenant_id=context.tenant_id, actor=_actor(context), data=_to_input(body)
    )
    return AssetDetailOut.model_validate(view)


# -- item paths --------------------------------------------------------------


@assets_router.get("/{asset_id}", response_model=AssetDetailOut, summary="Asset detail")
async def get_asset(
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    asset_id: uuid.UUID,
) -> AssetDetailOut:
    return AssetDetailOut.model_validate(
        await asset_service.get_asset(session, tenant_id=context.tenant_id, asset_id=asset_id)
    )


@assets_router.patch("/{asset_id}", response_model=AssetDetailOut, summary="Edit an asset")
async def update_asset(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    asset_id: uuid.UUID,
    body: AssetWrite,
) -> AssetDetailOut:
    view = await asset_service.update_asset(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        asset_id=asset_id,
        data=_to_input(body),
    )
    return AssetDetailOut.model_validate(view)


@assets_router.post(
    "/{asset_id}/transition", response_model=AssetDetailOut, summary="Move lifecycle"
)
async def transition(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    asset_id: uuid.UUID,
    body: TransitionRequest,
) -> AssetDetailOut:
    view = await asset_service.transition(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        asset_id=asset_id,
        to_status=body.to_status,
        note=body.note,
    )
    return AssetDetailOut.model_validate(view)


@assets_router.post(
    "/{asset_id}/decommission", response_model=AssetDetailOut, summary="Decommission an asset"
)
async def decommission(
    _p: Annotated[Principal, Depends(require_decommission)],
    context: _Ctx,
    session: _Db,
    asset_id: uuid.UUID,
    body: DecommissionRequest,
) -> AssetDetailOut:
    view = await asset_service.decommission(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        asset_id=asset_id,
        disposal_method=body.disposal_method,
        media_sanitised=body.media_sanitised,
        replacement_asset_id=body.replacement_asset_id,
        evidence_ref=body.evidence_ref,
        reason=body.reason,
    )
    return AssetDetailOut.model_validate(view)


@assets_router.get(
    "/{asset_id}/relationships",
    response_model=RelationshipPageOut,
    summary="Dependencies either way",
)
async def list_relationships(
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    asset_id: uuid.UUID,
) -> RelationshipPageOut:
    items = await asset_service.relationships(
        session, tenant_id=context.tenant_id, asset_id=asset_id
    )
    return RelationshipPageOut(items=[RelationshipOut.model_validate(r) for r in items])


@assets_router.post(
    "/{asset_id}/relationships",
    response_model=RelationshipPageOut,
    status_code=status.HTTP_201_CREATED,
    summary="Declare a dependency",
)
async def add_relationship(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    asset_id: uuid.UUID,
    body: RelationshipWrite,
) -> RelationshipPageOut:
    items = await asset_service.add_relationship(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        asset_id=asset_id,
        data=RelationshipInput(**body.model_dump()),
    )
    return RelationshipPageOut(items=[RelationshipOut.model_validate(r) for r in items])


@assets_router.delete(
    "/{asset_id}/relationships/{relationship_id}",
    response_model=RelationshipPageOut,
    summary="Withdraw a dependency",
)
async def remove_relationship(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    asset_id: uuid.UUID,
    relationship_id: uuid.UUID,
) -> RelationshipPageOut:
    items = await asset_service.remove_relationship(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        asset_id=asset_id,
        relationship_id=relationship_id,
    )
    return RelationshipPageOut(items=[RelationshipOut.model_validate(r) for r in items])


@assets_router.post("/{asset_id}/review", response_model=AssetDetailOut, summary="Mark reviewed")
async def review(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    asset_id: uuid.UUID,
) -> AssetDetailOut:
    view = await asset_service.record_review(
        session, tenant_id=context.tenant_id, actor=_actor(context), asset_id=asset_id
    )
    return AssetDetailOut.model_validate(view)
