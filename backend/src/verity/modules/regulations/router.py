"""HTTP for the country reference panel. Reading needs ``tenant:read``; recording the
workspace's call on a law needs ``tenant:manage``, the key that edits the profile."""

from __future__ import annotations

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
from verity.modules.regulations.schemas import DecisionIn, PanelOut
from verity.modules.regulations.service import regulations_service

regulations_router = APIRouter(prefix="/regulations", tags=["regulations"])

require_read = require("tenant:read")
require_manage = require("tenant:manage")

_Ctx = Annotated[TenantContext, Depends(get_tenant_context)]
_Db = Annotated[AsyncSession, Depends(get_tenant_session)]


@regulations_router.get(
    "", response_model=PanelOut, summary="Laws that may apply, from the profile"
)
async def get_panel(
    _principal: Annotated[Principal, Depends(require_read)], context: _Ctx, session: _Db
) -> PanelOut:
    return PanelOut.model_validate(
        await regulations_service.panel(session, tenant_id=context.tenant_id)
    )


@regulations_router.put("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def decide(
    key: Annotated[str, Path(max_length=20, pattern=r"^[A-Z]{2,6}-\d{2}$")],
    body: DecisionIn,
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
) -> None:
    """Record whether a law is relevant to the workspace, with a note."""
    assert principal.membership_id is not None  # noqa: S101 — tenant route
    await regulations_service.decide(
        session,
        tenant_id=context.tenant_id,
        actor=Membership(principal.membership_id),
        membership_id=principal.membership_id,
        key=key,
        relevance=body.relevance,
        note=body.note,
    )
