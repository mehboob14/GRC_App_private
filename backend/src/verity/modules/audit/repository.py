"""Data access for the audit trail. Insert, and the keyset-paginated list.

Both methods run on the caller's session and never commit — the transaction boundary
belongs to ``core.db.session_scope`` (backend/CLAUDE.md). The explicit ``tenant_id``
filter is the first wall; the row-level security policy behind it is the second.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection
from datetime import datetime

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from verity.modules.audit.models import AuditLog


class AuditLogRepository:
    async def add(self, session: AsyncSession, entry: AuditLog) -> None:
        """Insert on the caller's session, flushed so the row — and any refusal of
        it, such as the RLS ``WITH CHECK`` — happens inside the caller's transaction
        rather than at some later commit the caller no longer sees."""
        session.add(entry)
        await session.flush([entry])

    async def list_page(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID | None,
        limit: int,
        before: tuple[datetime, uuid.UUID] | None = None,
        exclude_object_types: Collection[str] | None = None,
    ) -> list[AuditLog]:
        """Newest first, keyed on ``(occurred_at, id)``.

        Keyset rather than offset: rows inserted while a client pages must not shift
        or repeat what it sees (docs/conventions/api.md). The UUIDv7 ``id`` breaks
        ties between rows that share ``occurred_at`` — every row written in one
        transaction carries the same ``now()``.

        ``exclude_object_types`` drops rows the *view* should not show (auth
        telemetry, tenant-provisioning plumbing). The rows still exist — the trail
        stays complete — the caller simply does not surface them here.
        """
        statement = (
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
            .limit(limit)
        )
        if exclude_object_types:
            statement = statement.where(AuditLog.object_type.notin_(list(exclude_object_types)))
        if before is not None:
            statement = statement.where(tuple_(AuditLog.occurred_at, AuditLog.id) < before)
        result = await session.execute(statement)
        return list(result.scalars())
