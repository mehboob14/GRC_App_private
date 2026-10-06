"""The audit trail over HTTP: ``GET /api/v1/audit-log`` and its export, both permission-gated.

The tenant comes from the authenticated session's :class:`TenantContext`, never from
the request: a ``tenant_id`` query parameter is not part of either route's schema and
is ignored outright (docs/conventions/api.md). Reading the trail is not a state
change, so the list route writes no audit row. The export does: leaving with the whole
trail is an event the trail records about itself.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, Final

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.deps import TenantContext, get_tenant_context, get_tenant_session, require
from verity.modules.audit.export import build_xlsx, csv_stream, events
from verity.modules.audit.schemas import AuditLogEntry, AuditLogPage
from verity.modules.audit.service import ExportFormat, ExportRequest, Membership, audit_service

DEFAULT_PAGE_SIZE: Final = 50
MAX_PAGE_SIZE: Final = 200

XLSX_MEDIA_TYPE: Final = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

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
    items = [AuditLogEntry.labelled(entry, labels) for entry in entries]
    return AuditLogPage(items=items, next_cursor=next_cursor)


# No session dependency, on purpose. FastAPI closes a yield dependency of the default
# scope only after the response body has been sent, so a session taken here would sit
# in an open transaction for as long as the download takes. The export opens a unit of
# work per batch instead.
@router.get(
    "/export",
    summary="Export the audit trail as CSV (the default) or Excel, oldest first",
    dependencies=[Depends(require_audit_read)],
)
async def export_audit_log(  # noqa: PLR0913, PLR0917 — one per query parameter
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    file_format: Annotated[ExportFormat, Query(alias="format")] = "csv",
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
    include_system: Annotated[bool, Query()] = False,
    # Bounded because the filter is written into the trail, which is append only.
    object_type: Annotated[str | None, Query(max_length=100)] = None,
) -> Response:
    assert context.membership_id is not None  # noqa: S101 — a tenant route always has one
    run = await audit_service.begin_export(
        tenant_id=context.tenant_id,
        actor=Membership(context.membership_id),
        request=ExportRequest(
            file_format=file_format,
            date_from=date_from,
            date_to=date_to,
            include_system=include_system,
            object_type=object_type,
        ),
    )
    filename = f"audit-log-{run.cut_off.date()}.{file_format}"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-store",
    }
    batches = events(audit_service.export_batches(run))
    if file_format == "csv":
        return StreamingResponse(csv_stream(batches), media_type="text/csv", headers=headers)
    return Response(
        content=await build_xlsx(batches, run), media_type=XLSX_MEDIA_TYPE, headers=headers
    )
