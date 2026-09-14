"""The whole committed audit stream, for assertions."""

from __future__ import annotations

import uuid

from verity.core.db import provider_session_scope
from verity.modules.audit.models import AuditLog
from verity.modules.audit.service import audit_service


async def full_stream(tenant_id: uuid.UUID | None) -> list[AuditLog]:
    """Every row for a tenant (or the provider plane), newest first, system rows included.

    The audit view pages and hides auth and provisioning telemetry by default, and
    signup alone now writes more than a page (every SOC 2 control is adopted), so
    a single ``list_page`` call silently dropped the rows these tests look for.
    """
    entries: list[AuditLog] = []
    cursor: str | None = None
    async with provider_session_scope() as session:
        while True:
            page, cursor = await audit_service.list_page(
                session, tenant_id=tenant_id, limit=500, cursor=cursor, include_system=True
            )
            entries.extend(page)
            if cursor is None:
                return entries
