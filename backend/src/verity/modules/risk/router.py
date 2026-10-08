"""HTTP for the risk register.

Reads need ``risks:read``; creating, editing, linking, treating, reviewing,
importing and requesting acceptance need ``risks:manage``; deciding and revoking
an acceptance need ``risks:approve``; registers, matrices and taxonomies need
``risks:configure`` (rule 7). Static paths are declared before ``/{risk_id}``.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.deps import (
    Principal,
    TenantContext,
    get_tenant_context,
    get_tenant_session,
    require,
)
from verity.core.errors import InvalidInput
from verity.modules.audit.service import Membership
from verity.modules.customfields.service import FieldInput
from verity.modules.risk import assist, transfer
from verity.modules.risk.schemas import (
    AcceptanceWrite,
    ActionWrite,
    AdoptOut,
    AdoptWrite,
    ApproverOut,
    AssistOut,
    AssistWrite,
    CategoriesWrite,
    CategoryNodeIn,
    ControlsWrite,
    CustomFieldArchiveWrite,
    CustomFieldOut,
    CustomFieldPageOut,
    CustomFieldWrite,
    DecisionWrite,
    FacetsOut,
    ImportPreviewOut,
    ImportResultOut,
    ImportWrite,
    LinkWrite,
    OptionsOut,
    PromoteWrite,
    RegisterOut,
    RegisterWrite,
    ReviewWrite,
    RevokeWrite,
    RiskDetailOut,
    RiskOut,
    RiskPageOut,
    RiskRefOut,
    RiskWrite,
    StatusWrite,
    SummaryOut,
    TemplateOut,
)
from verity.modules.risk.service import (
    CategoryNode,
    RegisterInput,
    RiskFilters,
    RiskInput,
    risk_service,
)

risks_router = APIRouter(prefix="/risks", tags=["risks"])

require_read = require("risks:read")
require_manage = require("risks:manage")
require_approve = require("risks:approve")
require_configure = require("risks:configure")

_Ctx = Annotated[TenantContext, Depends(get_tenant_context)]
_Db = Annotated[AsyncSession, Depends(get_tenant_session)]
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _actor(context: TenantContext) -> Membership:
    assert context.membership_id is not None  # noqa: S101
    return Membership(context.membership_id)


def _register_input(body: RegisterWrite) -> RegisterInput:
    data = body.model_dump()
    for key in ("likelihood_scale", "impact_scale", "severity_bands"):
        if data[key] is not None:
            data[key] = list(data[key])
    return RegisterInput(**data)


def _nodes(items: list[CategoryNodeIn]) -> list[CategoryNode]:
    return [CategoryNode(name=n.name, id=n.id, children=_nodes(n.children)) for n in items]


def _filters(  # noqa: PLR0913, PLR0917 — one per query parameter
    register_id: uuid.UUID,
    search: str | None,
    statuses: list[str] | None,
    bands: list[str] | None,
    category_ids: list[uuid.UUID] | None,
    treatments: list[str] | None,
    owner: str | None,
    department_ids: list[uuid.UUID] | None,
    attention: list[str] | None,
    cell: str | None,
    custom: list[str] | None = None,
) -> RiskFilters:
    return RiskFilters(
        register_id=register_id,
        search=search,
        statuses=tuple(statuses or ()),
        bands=tuple(bands or ()),
        category_ids=tuple(category_ids or ()),
        treatments=tuple(treatments or ()),
        owner=owner,
        department_ids=tuple(department_ids or ()),
        attention=tuple(attention or ()),
        cell=cell,
        custom=tuple(
            (key, value) for key, _, value in (c.partition(":") for c in custom or ()) if key
        ),
    )


# -- registers ------------------------------------------------------------------


@risks_router.get("/registers", response_model=list[RegisterOut], summary="List registers")
async def list_registers(
    _p: Annotated[Principal, Depends(require_read)], context: _Ctx, session: _Db
) -> list[RegisterOut]:
    views = await risk_service.list_registers(session, tenant_id=context.tenant_id)
    return [RegisterOut.model_validate(v) for v in views]


@risks_router.post(
    "/registers",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterOut,
    summary="Create a register",
)
async def create_register(
    body: RegisterWrite,
    _p: Annotated[Principal, Depends(require_configure)],
    context: _Ctx,
    session: _Db,
) -> RegisterOut:
    view = await risk_service.create_register(
        session, tenant_id=context.tenant_id, actor=_actor(context), data=_register_input(body)
    )
    return RegisterOut.model_validate(view)


@risks_router.get("/registers/{register_id}", response_model=RegisterOut, summary="One register")
async def get_register(
    register_id: uuid.UUID,
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
) -> RegisterOut:
    view = await risk_service.get_register(
        session, tenant_id=context.tenant_id, register_id=register_id
    )
    return RegisterOut.model_validate(view)


@risks_router.patch(
    "/registers/{register_id}", response_model=RegisterOut, summary="Configure a register"
)
async def update_register(
    register_id: uuid.UUID,
    body: RegisterWrite,
    _p: Annotated[Principal, Depends(require_configure)],
    context: _Ctx,
    session: _Db,
) -> RegisterOut:
    view = await risk_service.update_register(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        register_id=register_id,
        data=_register_input(body),
    )
    return RegisterOut.model_validate(view)


@risks_router.put(
    "/registers/{register_id}/categories",
    response_model=RegisterOut,
    summary="Save the category taxonomy",
)
async def save_categories(
    register_id: uuid.UUID,
    body: CategoriesWrite,
    _p: Annotated[Principal, Depends(require_configure)],
    context: _Ctx,
    session: _Db,
) -> RegisterOut:
    view = await risk_service.save_categories(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        register_id=register_id,
        tree=_nodes(body.categories),
    )
    return RegisterOut.model_validate(view)


# -- overview -------------------------------------------------------------------------


@risks_router.get("/summary", response_model=SummaryOut, summary="Overview for one register")
async def summary(
    register_id: uuid.UUID,
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
) -> SummaryOut:
    data = await risk_service.summary(session, tenant_id=context.tenant_id, register_id=register_id)
    return SummaryOut.model_validate(data)


@risks_router.get("/facets", response_model=FacetsOut, summary="Filter counts")
async def facets(
    register_id: uuid.UUID,
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
) -> FacetsOut:
    data = await risk_service.facets(session, tenant_id=context.tenant_id, register_id=register_id)
    return FacetsOut.model_validate(data)


@risks_router.get("/export", summary="Export the register as CSV or Excel")
async def export(  # noqa: PLR0913, PLR0917 — the list filters plus the format
    register_id: uuid.UUID,
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    file_format: Annotated[str, Query(alias="format", pattern="^(csv|xlsx)$")] = "xlsx",
    search: str | None = None,
    statuses: Annotated[list[str] | None, Query()] = None,
    bands: Annotated[list[str] | None, Query()] = None,
    category_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    treatments: Annotated[list[str] | None, Query()] = None,
    owner: str | None = None,
    department_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    attention: Annotated[list[str] | None, Query()] = None,
    cell: str | None = None,
    custom: Annotated[list[str] | None, Query()] = None,
) -> Response:
    filters = _filters(
        register_id, search, statuses, bands, category_ids, treatments, owner, department_ids,
        attention, cell, custom,
    )  # fmt: skip
    data, filename, content_type = await transfer.export_register(
        session, tenant_id=context.tenant_id, filters=filters, file_format=file_format
    )
    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# -- import -----------------------------------------------------------------------------


@risks_router.get("/import/template", summary="Download the Excel import template")
async def import_template(
    register_id: uuid.UUID,
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> Response:
    data, filename = await transfer.template_for(
        session, tenant_id=context.tenant_id, register_id=register_id
    )
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@risks_router.post(
    "/import/preview", response_model=ImportPreviewOut, summary="Validate an import file"
)
async def import_preview(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    file: Annotated[UploadFile, File()],
    register_id: Annotated[uuid.UUID, Form()],
) -> ImportPreviewOut:
    data = await file.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise InvalidInput(
            "This file is larger than 10 MB. Split it and import each part.",
            detail="import file too large",
        )
    rows = await transfer.preview(
        session,
        tenant_id=context.tenant_id,
        register_id=register_id,
        file_name=file.filename or "risks.csv",
        data=data,
    )
    valid = sum(1 for r in rows if not r.errors)
    return ImportPreviewOut.model_validate(
        {"rows": rows, "valid": valid, "invalid": len(rows) - valid}
    )


@risks_router.post(
    "/import",
    status_code=status.HTTP_201_CREATED,
    response_model=ImportResultOut,
    summary="Import validated rows",
)
async def import_rows(
    body: ImportWrite,
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> ImportResultOut:
    rows = [transfer.ImportRow(**row.model_dump()) for row in body.rows]
    result = await transfer.commit(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        register_id=body.register_id,
        rows=rows,
    )
    return ImportResultOut.model_validate(result)


# -- assist, library, pickers, promotion ------------------------------------------------


@risks_router.post("/assist", response_model=AssistOut, summary="Draft risk fields from a title")
async def assist_draft(
    body: AssistWrite,
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> AssistOut:
    result = await assist.draft(
        session,
        tenant_id=context.tenant_id,
        register_id=body.register_id,
        title=body.title,
        description=body.description,
    )
    return AssistOut.model_validate(result)


@risks_router.get("/library", response_model=list[TemplateOut], summary="Starter risk library")
async def library(
    register_id: uuid.UUID,
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
) -> list[TemplateOut]:
    views = await risk_service.list_library(
        session, tenant_id=context.tenant_id, register_id=register_id
    )
    return [TemplateOut.model_validate(v) for v in views]


@risks_router.post("/library/adopt", response_model=AdoptOut, summary="Add library risks")
async def adopt(
    body: AdoptWrite,
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> AdoptOut:
    result = await risk_service.adopt_templates(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        register_id=body.register_id,
        codes=body.codes,
    )
    return AdoptOut.model_validate(result)


@risks_router.get("/refs", response_model=list[RiskRefOut], summary="Pick a risk")
async def refs(
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    search: str | None = None,
) -> list[RiskRefOut]:
    views = await risk_service.refs(session, tenant_id=context.tenant_id, search=search)
    return [RiskRefOut.model_validate(v) for v in views]


@risks_router.get("/options", response_model=OptionsOut, summary="Owners and business units")
async def options(
    _p: Annotated[Principal, Depends(require_read)], context: _Ctx, session: _Db
) -> OptionsOut:
    data = await risk_service.form_options(session, tenant_id=context.tenant_id)
    return OptionsOut.model_validate(data)


@risks_router.get(
    "/approvers", response_model=list[ApproverOut], summary="Who can approve an acceptance"
)
async def approvers(
    _p: Annotated[Principal, Depends(require_manage)], context: _Ctx, session: _Db
) -> list[ApproverOut]:
    views = await risk_service.approvers(
        session, tenant_id=context.tenant_id, me=context.membership_id
    )
    return [ApproverOut.model_validate(v) for v in views]


@risks_router.post(
    "/from-vendor-finding",
    status_code=status.HTTP_201_CREATED,
    response_model=RiskDetailOut,
    summary="Promote a vendor finding into the register",
)
async def promote(
    body: PromoteWrite,
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> RiskDetailOut:
    view = await risk_service.promote_vendor_finding(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        finding_id=body.finding_id,
        register_id=body.register_id,
    )
    return RiskDetailOut.model_validate(view)


# -- the collection -----------------------------------------------------------------------


@risks_router.get(
    "/custom-fields", response_model=CustomFieldPageOut, summary="Fields this tenant adds"
)
async def list_custom_fields(
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    include_archived: bool = False,
) -> CustomFieldPageOut:
    items = await risk_service.custom_fields(
        session, tenant_id=context.tenant_id, include_archived=include_archived
    )
    return CustomFieldPageOut(items=[CustomFieldOut.model_validate(i) for i in items])


@risks_router.post(
    "/custom-fields",
    response_model=CustomFieldOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a field",
)
async def create_custom_field(
    _p: Annotated[Principal, Depends(require_configure)],
    context: _Ctx,
    session: _Db,
    body: CustomFieldWrite,
) -> CustomFieldOut:
    view = await risk_service.save_custom_field(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        field_id=None,
        data=FieldInput(**{**body.model_dump(), "options": tuple(body.options)}),
    )
    return CustomFieldOut.model_validate(view)


@risks_router.patch(
    "/custom-fields/{field_id}", response_model=CustomFieldOut, summary="Edit a field"
)
async def update_custom_field(
    _p: Annotated[Principal, Depends(require_configure)],
    context: _Ctx,
    session: _Db,
    field_id: uuid.UUID,
    body: CustomFieldWrite,
) -> CustomFieldOut:
    view = await risk_service.save_custom_field(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        field_id=field_id,
        data=FieldInput(**{**body.model_dump(), "options": tuple(body.options)}),
    )
    return CustomFieldOut.model_validate(view)


@risks_router.post(
    "/custom-fields/{field_id}/archive",
    response_model=CustomFieldOut,
    summary="Stop collecting a field",
)
async def archive_custom_field(
    _p: Annotated[Principal, Depends(require_configure)],
    context: _Ctx,
    session: _Db,
    field_id: uuid.UUID,
    body: CustomFieldArchiveWrite,
) -> CustomFieldOut:
    view = await risk_service.set_custom_field_archived(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        field_id=field_id,
        archived=body.archived,
    )
    return CustomFieldOut.model_validate(view)


@risks_router.get("", response_model=RiskPageOut, summary="List risks in a register")
async def list_risks(  # noqa: PLR0913, PLR0917 — one query parameter per filter
    register_id: uuid.UUID,
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    search: str | None = None,
    statuses: Annotated[list[str] | None, Query()] = None,
    bands: Annotated[list[str] | None, Query()] = None,
    category_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    treatments: Annotated[list[str] | None, Query()] = None,
    owner: str | None = None,
    department_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    attention: Annotated[list[str] | None, Query()] = None,
    cell: str | None = None,
    custom: Annotated[list[str] | None, Query()] = None,
    sort: str | None = None,
    direction: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 25,
) -> RiskPageOut:
    filters = _filters(
        register_id, search, statuses, bands, category_ids, treatments, owner, department_ids,
        attention, cell, custom,
    )  # fmt: skip
    items, total = await risk_service.list_risks(
        session,
        tenant_id=context.tenant_id,
        filters=filters,
        me=context.membership_id,
        sort=sort,
        direction=direction,
        page=page,
        page_size=page_size,
    )
    return RiskPageOut(items=[RiskOut.model_validate(v) for v in items], total=total)


@risks_router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=RiskDetailOut, summary="Add a risk"
)
async def create_risk(
    body: RiskWrite,
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> RiskDetailOut:
    risk = await risk_service.create_risk(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        data=RiskInput(**body.model_dump()),
    )
    view = await risk_service.get_risk(session, tenant_id=context.tenant_id, risk_id=risk.id)
    return RiskDetailOut.model_validate(view)


# -- one risk -------------------------------------------------------------------------------


@risks_router.get("/{risk_id}", response_model=RiskDetailOut, summary="One risk")
async def get_risk(
    risk_id: uuid.UUID,
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
) -> RiskDetailOut:
    view = await risk_service.get_risk(session, tenant_id=context.tenant_id, risk_id=risk_id)
    return RiskDetailOut.model_validate(view)


@risks_router.patch("/{risk_id}", response_model=RiskDetailOut, summary="Edit a risk")
async def update_risk(
    risk_id: uuid.UUID,
    body: RiskWrite,
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> RiskDetailOut:
    view = await risk_service.update_risk(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        risk_id=risk_id,
        data=RiskInput(**body.model_dump()),
    )
    return RiskDetailOut.model_validate(view)


@risks_router.post("/{risk_id}/status", response_model=RiskDetailOut, summary="Change status")
async def change_status(
    risk_id: uuid.UUID,
    body: StatusWrite,
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> RiskDetailOut:
    view = await risk_service.transition(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        risk_id=risk_id,
        status=body.status,
        note=body.note,
    )
    return RiskDetailOut.model_validate(view)


@risks_router.post("/{risk_id}/review", response_model=RiskDetailOut, summary="Mark reviewed")
async def review(
    risk_id: uuid.UUID,
    body: ReviewWrite,
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> RiskDetailOut:
    view = await risk_service.mark_reviewed(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        risk_id=risk_id,
        note=body.note,
        next_review_on=body.next_review_on,
    )
    return RiskDetailOut.model_validate(view)


@risks_router.post("/{risk_id}/controls", response_model=RiskDetailOut, summary="Link controls")
async def link_controls(
    risk_id: uuid.UUID,
    body: ControlsWrite,
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> RiskDetailOut:
    view = await risk_service.link_controls(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        risk_id=risk_id,
        control_ids=body.control_ids,
    )
    return RiskDetailOut.model_validate(view)


@risks_router.delete(
    "/{risk_id}/controls/{control_id}", response_model=RiskDetailOut, summary="Unlink a control"
)
async def unlink_control(
    risk_id: uuid.UUID,
    control_id: uuid.UUID,
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> RiskDetailOut:
    view = await risk_service.unlink_control(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        risk_id=risk_id,
        control_id=control_id,
    )
    return RiskDetailOut.model_validate(view)


@risks_router.post("/{risk_id}/links", response_model=RiskDetailOut, summary="Link a record")
async def link_record(
    risk_id: uuid.UUID,
    body: LinkWrite,
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> RiskDetailOut:
    view = await risk_service.link_record(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        risk_id=risk_id,
        target_type=body.target_type,
        target_id=body.target_id,
    )
    return RiskDetailOut.model_validate(view)


@risks_router.delete(
    "/{risk_id}/links/{link_id}", response_model=RiskDetailOut, summary="Remove a link"
)
async def unlink_record(
    risk_id: uuid.UUID,
    link_id: uuid.UUID,
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> RiskDetailOut:
    view = await risk_service.unlink_record(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        risk_id=risk_id,
        link_id=link_id,
    )
    return RiskDetailOut.model_validate(view)


@risks_router.post(
    "/{risk_id}/actions", response_model=RiskDetailOut, summary="Add a treatment action"
)
async def add_action(
    risk_id: uuid.UUID,
    body: ActionWrite,
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> RiskDetailOut:
    view = await risk_service.add_action(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        risk_id=risk_id,
        title=body.title,
        description=body.description,
        priority=body.priority,
        owner_membership_id=body.owner_membership_id,
        due_on=body.due_on,
    )
    return RiskDetailOut.model_validate(view)


@risks_router.post(
    "/{risk_id}/acceptances", response_model=RiskDetailOut, summary="Request acceptance"
)
async def request_acceptance(
    risk_id: uuid.UUID,
    body: AcceptanceWrite,
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> RiskDetailOut:
    view = await risk_service.request_acceptance(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        risk_id=risk_id,
        approver_membership_id=body.approver_membership_id,
        rationale=body.rationale,
        expires_on=body.expires_on,
    )
    return RiskDetailOut.model_validate(view)


@risks_router.post(
    "/{risk_id}/acceptances/{acceptance_id}/decision",
    response_model=RiskDetailOut,
    summary="Approve or reject an acceptance",
)
async def decide_acceptance(
    risk_id: uuid.UUID,
    acceptance_id: uuid.UUID,
    body: DecisionWrite,
    _p: Annotated[Principal, Depends(require_approve)],
    context: _Ctx,
    session: _Db,
) -> RiskDetailOut:
    view = await risk_service.decide_acceptance(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        risk_id=risk_id,
        acceptance_id=acceptance_id,
        approve=body.approve,
        note=body.note,
    )
    return RiskDetailOut.model_validate(view)


@risks_router.post(
    "/{risk_id}/acceptances/{acceptance_id}/withdraw",
    response_model=RiskDetailOut,
    summary="Withdraw a pending acceptance request",
)
async def withdraw_acceptance(
    risk_id: uuid.UUID,
    acceptance_id: uuid.UUID,
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> RiskDetailOut:
    view = await risk_service.withdraw_acceptance(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        risk_id=risk_id,
        acceptance_id=acceptance_id,
    )
    return RiskDetailOut.model_validate(view)


@risks_router.post(
    "/{risk_id}/acceptances/{acceptance_id}/revoke",
    response_model=RiskDetailOut,
    summary="Revoke an acceptance in force",
)
async def revoke_acceptance(
    risk_id: uuid.UUID,
    acceptance_id: uuid.UUID,
    body: RevokeWrite,
    _p: Annotated[Principal, Depends(require_approve)],
    context: _Ctx,
    session: _Db,
) -> RiskDetailOut:
    view = await risk_service.revoke_acceptance(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        risk_id=risk_id,
        acceptance_id=acceptance_id,
        reason=body.reason,
    )
    return RiskDetailOut.model_validate(view)
