"""HTTP for a member's notification inbox.

Every route is gated by ``tenant:read`` — the key every workspace member holds —
because reading and clearing *your own* inbox needs no capability beyond seeing
the workspace. The row-level scope (only your own notifications) is applied in
the service on top of that, which is the object-level half rule 7 requires. A
dedicated ``notifications:*`` key would add a permission every role must be
granted for a feature every member uses; ``tenant:read`` already means exactly
"is a member of this workspace".
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
from verity.modules.notifications.schemas import (
    MarkedReadOut,
    NotificationInboxOut,
    NotificationOut,
)
from verity.modules.notifications.service import notification_service

notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])

require_read = require("tenant:read")

_Ctx = Annotated[TenantContext, Depends(get_tenant_context)]
_Db = Annotated[AsyncSession, Depends(get_tenant_session)]


def _membership(context: TenantContext) -> uuid.UUID:
    assert context.membership_id is not None  # noqa: S101
    return context.membership_id


@notifications_router.get("", response_model=NotificationInboxOut, summary="My inbox")
async def inbox(
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    unread_only: bool = False,
    limit: int = 50,
) -> NotificationInboxOut:
    mid = _membership(context)
    items = await notification_service.list_for(
        session,
        tenant_id=context.tenant_id,
        membership_id=mid,
        unread_only=unread_only,
        limit=limit,
    )
    unread = await notification_service.unread_count(
        session, tenant_id=context.tenant_id, membership_id=mid
    )
    return NotificationInboxOut(
        items=[NotificationOut.model_validate(n) for n in items], unread_count=unread
    )


@notifications_router.post(
    "/read-all", response_model=MarkedReadOut, summary="Mark all read"
)
async def mark_all_read(
    _p: Annotated[Principal, Depends(require_read)], context: _Ctx, session: _Db
) -> MarkedReadOut:
    marked = await notification_service.mark_all_read(
        session, tenant_id=context.tenant_id, membership_id=_membership(context)
    )
    return MarkedReadOut(marked=marked)


@notifications_router.post(
    "/{notification_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark one read",
)
async def mark_read(
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    notification_id: uuid.UUID,
) -> None:
    await notification_service.mark_read(
        session,
        tenant_id=context.tenant_id,
        membership_id=_membership(context),
        notification_id=notification_id,
    )
