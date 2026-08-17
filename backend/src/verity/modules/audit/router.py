"""``GET /api/v1/audit-log`` — the one read route, permission-gated.

The tenant comes from the authenticated session's :class:`TenantContext`, never from
the request: a ``tenant_id`` query parameter is not part of this route's schema and
is ignored outright (docs/conventions/api.md). Reading the trail is not a state
change, so this route writes no audit row.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Final

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.deps import TenantContext, get_tenant_context, get_tenant_session, require
from verity.modules.audit.schemas import AuditLogEntry, AuditLogPage
from verity.modules.audit.service import audit_service

DEFAULT_PAGE_SIZE: Final = 50
MAX_PAGE_SIZE: Final = 200

router = APIRouter(prefix="/audit-log", tags=["audit"])

require_audit_read = require("audit:read")
"""Named rather than inlined in the decorator so tests can override this exact
dependency while ``core.deps.require`` remains a Week 1 placeholder. The IAM change
implements ``require`` itself; nothing here changes when it does."""


@router.get(
    "",
    response_model=AuditLogPage,
    summary="The calling tenant's audit trail, newest first",
    dependencies=[Depends(require_audit_read)],
)
async def list_audit_log(  # noqa: PLR0913, PLR0917 — one per query parameter
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    cursor: Annotated[str | None, Query()] = None,
    include_system: Annotated[bool, Query()] = False,
    object_type: Annotated[str | None, Query()] = None,
    object_id: Annotated[uuid.UUID | None, Query()] = None,
) -> AuditLogPage:
    entries, next_cursor = await audit_service.list_page(
        session,
        tenant_id=context.tenant_id,
        limit=limit,
        cursor=cursor,
        include_system=include_system,
        object_type=object_type,
        object_id=object_id,
    )
    labels = await audit_service.resolve_labels(session, entries)
    items: list[AuditLogEntry] = []
    for entry in entries:
        item = AuditLogEntry.model_validate(entry)
        actor = labels.actor(entry.actor_type, entry.actor_id)
        if actor:
            item.actor_label = actor
        obj = labels.obj(entry.object_type, entry.object_id)
        if obj:
            item.object_label = obj
        items.append(item)
    return AuditLogPage(items=items, next_cursor=next_cursor)
