"""Data access for the audit trail. Insert, the keyset-paginated list, and the export reads.

Every method runs on the caller's session and never commits — the transaction boundary
belongs to ``core.db.session_scope`` (backend/CLAUDE.md). The explicit ``tenant_id``
filter is the first wall; the row-level security policy behind it is the second.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from verity.modules.audit.models import AuditLog


@dataclass(frozen=True, slots=True)
class ExportWindow:
    """The slice of one tenant's stream an export reads.

    ``occurred_before`` is the cut-off and is exclusive; ``occurred_from`` and
    ``occurred_to`` are the optional inclusive ends of the date range the person chose.
    """

    tenant_id: uuid.UUID
    occurred_before: datetime
    occurred_from: datetime | None = None
    occurred_to: datetime | None = None
    exclude_object_types: Collection[str] | None = None
    object_type: str | None = None


def _within(statement: Select[Any], window: ExportWindow) -> Select[Any]:
    statement = statement.where(
        AuditLog.tenant_id == window.tenant_id, AuditLog.occurred_at < window.occurred_before
    )
    if window.occurred_from is not None:
        statement = statement.where(AuditLog.occurred_at >= window.occurred_from)
    if window.occurred_to is not None:
        statement = statement.where(AuditLog.occurred_at <= window.occurred_to)
    if window.exclude_object_types:
        statement = statement.where(AuditLog.object_type.notin_(list(window.exclude_object_types)))
    if window.object_type is not None:
        statement = statement.where(AuditLog.object_type == window.object_type)
    return statement


class AuditLogRepository:
    async def add(self, session: AsyncSession, entry: AuditLog) -> None:
        """Insert on the caller's session, flushed so the row — and any refusal of
        it, such as the RLS ``WITH CHECK`` — happens inside the caller's transaction
        rather than at some later commit the caller no longer sees."""
        session.add(entry)
        await session.flush([entry])

    async def list_page(  # noqa: PLR0913 — one keyword per documented filter
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID | None,
        limit: int,
        before: tuple[datetime, uuid.UUID] | None = None,
        exclude_object_types: Collection[str] | None = None,
        object_type: str | None = None,
        object_id: uuid.UUID | None = None,
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
        # Scoping to one object is what makes a per-record History tab possible
        # without the client pulling the whole trail and filtering client-side.
        if object_type is not None:
            statement = statement.where(AuditLog.object_type == object_type)
        if object_id is not None:
            statement = statement.where(AuditLog.object_id == object_id)
        if before is not None:
            statement = statement.where(tuple_(AuditLog.occurred_at, AuditLog.id) < before)
        result = await session.execute(statement)
        return list(result.scalars())

    async def database_time(self, session: AsyncSession) -> datetime:
        """The database's clock for this transaction — the same ``now()`` that stamps
        ``occurred_at`` on any row written in it, which is what lets an export take its
        cut-off from here and never depend on the app server's clock agreeing."""
        value: datetime = (await session.execute(select(func.now()))).scalar_one()
        return value.astimezone(UTC)

    async def export_count(self, session: AsyncSession, window: ExportWindow, *, limit: int) -> int:
        """How many rows the window holds, counted no further than ``limit + 1``.

        A caller that only asks "is it over the limit" never pays for a full count of
        a trail that has grown for years."""
        capped = _within(select(AuditLog.id), window).limit(limit + 1).subquery()
        count: int = (await session.execute(select(func.count()).select_from(capped))).scalar_one()
        return count

    async def export_batch(
        self,
        session: AsyncSession,
        window: ExportWindow,
        *,
        after: tuple[datetime, uuid.UUID] | None,
        limit: int,
    ) -> list[AuditLog]:
        """Oldest first, keyed on ``(occurred_at, id)`` — the order an auditor reads in.

        Keyset for the reason ``list_page`` is: an export walks the whole trail in
        batches, and an offset would skip or repeat rows as the trail grows under it."""
        statement = (
            _within(select(AuditLog), window)
            .order_by(AuditLog.occurred_at, AuditLog.id)
            .limit(limit)
        )
        if after is not None:
            statement = statement.where(tuple_(AuditLog.occurred_at, AuditLog.id) > after)
        result = await session.execute(statement)
        return list(result.scalars())
