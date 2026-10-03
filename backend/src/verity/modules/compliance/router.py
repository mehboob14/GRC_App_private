"""HTTP for the compliance module: parse, authorise, call the service, shape.

Every route declares ``frameworks:read`` — deny by default (CLAUDE.md rule 7).
These reads serve global content, so they resolve nothing from the tenant
context beyond proving the caller is authenticated and permitted; there is no
tenant column on any table behind them.

No ORM object reaches a response: the service returns views, and the response
models here are the contract with the frontend.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.deps import (
    Principal,
    TenantContext,
    get_tenant_context,
    get_tenant_session,
    require,
)
from verity.modules.compliance.chain_service import chain_service
from verity.modules.compliance.schemas import (
    ChainControlOut,
    ChainRequirementOut,
    ControlTemplateDetailOut,
    ControlTemplateOut,
    ControlTemplatePage,
    FrameworkOut,
    RequirementChainOut,
    RequirementOut,
)
from verity.modules.compliance.service import compliance_service
from verity.modules.connectors.schemas import ControlChainOut

MAX_PAGE_SIZE = 200

frameworks_router = APIRouter(prefix="/frameworks", tags=["compliance"])
templates_router = APIRouter(prefix="/control-templates", tags=["compliance"])
requirements_router = APIRouter(prefix="/requirements", tags=["compliance"])

require_frameworks_read = require("frameworks:read")


@frameworks_router.get(
    "",
    response_model=list[FrameworkOut],
    summary="The framework catalogue with each framework's versions",
)
async def list_frameworks(
    _principal: Annotated[Principal, Depends(require_frameworks_read)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> list[FrameworkOut]:
    views = await compliance_service.list_frameworks(session)
    return [FrameworkOut.model_validate(view) for view in views]


@frameworks_router.get(
    "/{framework_id}/requirements",
    response_model=list[RequirementOut],
    summary="The criteria of a framework version, with how many templates satisfy each",
)
async def list_requirements(
    framework_id: uuid.UUID,
    _principal: Annotated[Principal, Depends(require_frameworks_read)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
    version_id: uuid.UUID | None = None,
) -> list[RequirementOut]:
    views = await compliance_service.list_requirements(
        session, framework_id=framework_id, version_id=version_id
    )
    return [RequirementOut.model_validate(view) for view in views]


@templates_router.get(
    "",
    response_model=ControlTemplatePage,
    summary="The shipped control template library",
)
async def list_control_templates(  # noqa: PLR0913, PLR0917 — one parameter per filter
    _principal: Annotated[Principal, Depends(require_frameworks_read)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
    framework_id: uuid.UUID | None = None,
    category: str | None = None,
    control_type: str | None = None,
    importance: str | None = None,
    search: str | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ControlTemplatePage:
    rows, total = await compliance_service.list_templates(
        session,
        framework_id=framework_id,
        category=category,
        control_type=control_type,
        importance=importance,
        search=search,
        limit=limit,
        offset=offset,
    )
    return ControlTemplatePage(
        items=[ControlTemplateOut.model_validate(row) for row in rows], total=total
    )


@templates_router.get(
    "/{template_id}",
    response_model=ControlTemplateDetailOut,
    summary="One control template and the criteria it satisfies",
)
async def get_control_template(
    template_id: uuid.UUID,
    _principal: Annotated[Principal, Depends(require_frameworks_read)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> ControlTemplateDetailOut:
    view = await compliance_service.get_template(session, template_id)
    return ControlTemplateDetailOut.model_validate(view)


@requirements_router.get(
    "/{requirement_id}/chain",
    response_model=RequirementChainOut,
    summary="A criterion, the controls that answer it, and what evidences each",
)
async def get_requirement_chain(
    requirement_id: uuid.UUID,
    _principal: Annotated[Principal, Depends(require_frameworks_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> RequirementChainOut:
    view = await chain_service.requirement_chain(
        session, tenant_id=context.tenant_id, requirement_id=requirement_id
    )
    return RequirementChainOut(
        requirement=ChainRequirementOut.model_validate(view.requirement),
        state=view.state,
        controls=[
            ChainControlOut(
                control_id=item.control.id,
                code=item.control.code,
                name=item.control.name,
                status=item.control.status,
                owner_name=item.control.owner_name,
                coverage=item.coverage,
                rationale=item.rationale,
                origin=item.origin,
                ready=item.ready,
                chain=ControlChainOut.model_validate(item.chain) if item.chain else None,
            )
            for item in view.controls
        ],
    )
