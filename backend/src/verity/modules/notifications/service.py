"""Creating and reading notifications.

Writes happen on the caller's session, inside the caller's transaction, so a
notification and the event that caused it commit together or not at all. Email
does *not*: ``email_requested`` marks a row for the outbox, and the worker
(``workers.tasks.flush_notification_emails``) delivers it after commit.

Reads are always scoped to one member — you only ever see your own inbox. The
route's permission (``tenant:read``) says "may see this workspace"; this scope
is the row-level half rule 7 asks for on top of it.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import NotFound
from verity.modules.notifications.models import Notification


class NotificationService:
    async def notify(  # noqa: PLR0913 — the fields of one notification, no more
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        recipient_membership_id: uuid.UUID,
        kind: str,
        title: str,
        body: str = "",
        object_type: str | None = None,
        object_id: uuid.UUID | None = None,
        email: bool = False,
    ) -> Notification:
        row = Notification(
            tenant_id=tenant_id,
            recipient_membership_id=recipient_membership_id,
            kind=kind,
            title=title,
            body=body,
            object_type=object_type,
            object_id=object_id,
            email_requested=email,
        )
        session.add(row)
        await session.flush()
        return row

    async def notify_many(  # noqa: PLR0913 — mirrors notify(), fanned to recipients
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        recipients: Iterable[uuid.UUID | None],
        kind: str,
        title: str,
        body: str = "",
        object_type: str | None = None,
        object_id: uuid.UUID | None = None,
        email: bool = False,
    ) -> None:
        """Notify a set of members at once. Nulls and duplicates are dropped, so
        callers can pass ``[owner, *assignees, actor]`` and let this sort it out."""
        seen: set[uuid.UUID] = set()
        for mid in recipients:
            if mid is None or mid in seen:
                continue
            seen.add(mid)
            await self.notify(
                session,
                tenant_id=tenant_id,
                recipient_membership_id=mid,
                kind=kind,
                title=title,
                body=body,
                object_type=object_type,
                object_id=object_id,
                email=email,
            )

    async def notify_once(  # noqa: PLR0913 — notify() plus the dedup key
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        recipient_membership_id: uuid.UUID,
        kind: str,
        title: str,
        body: str = "",
        object_type: str | None = None,
        object_id: uuid.UUID | None = None,
        email: bool = False,
    ) -> bool:
        """Notify unless an identical (recipient, kind, object) notice already
        exists. This is what makes the SLA sweep idempotent without a marker
        column: one breach alert per task per person, however often it runs.
        Returns True if a row was written."""
        exists = (
            await session.execute(
                select(Notification.id).where(
                    Notification.tenant_id == tenant_id,
                    Notification.recipient_membership_id == recipient_membership_id,
                    Notification.kind == kind,
                    Notification.object_id == object_id,
                )
            )
        ).first()
        if exists is not None:
            return False
        await self.notify(
            session,
            tenant_id=tenant_id,
            recipient_membership_id=recipient_membership_id,
            kind=kind,
            title=title,
            body=body,
            object_type=object_type,
            object_id=object_id,
            email=email,
        )
        return True

    async def list_for(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        membership_id: uuid.UUID,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Notification]:
        stmt = select(Notification).where(
            Notification.tenant_id == tenant_id,
            Notification.recipient_membership_id == membership_id,
        )
        if unread_only:
            stmt = stmt.where(Notification.read_at.is_(None))
        stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
        return list((await session.execute(stmt)).scalars())

    async def unread_count(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, membership_id: uuid.UUID
    ) -> int:
        return (
            await session.execute(
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.tenant_id == tenant_id,
                    Notification.recipient_membership_id == membership_id,
                    Notification.read_at.is_(None),
                )
            )
        ).scalar_one()

    async def mark_read(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        membership_id: uuid.UUID,
        notification_id: uuid.UUID,
    ) -> None:
        """Mark one of the caller's own notifications read. Scoping by recipient
        is what stops a member marking someone else's inbox. RETURNING tells us a
        row matched without reaching for the untyped CursorResult.rowcount."""
        updated = (
            await session.execute(
                update(Notification)
                .where(
                    Notification.tenant_id == tenant_id,
                    Notification.id == notification_id,
                    Notification.recipient_membership_id == membership_id,
                    Notification.read_at.is_(None),
                )
                .values(read_at=datetime.now(UTC))
                .returning(Notification.id)
            )
        ).scalar_one_or_none()
        if updated is None:
            # It did not match: not theirs, gone, or already read. Only the first
            # two are errors; a re-read is a no-op, so check existence.
            owned = (
                await session.execute(
                    select(Notification.id).where(
                        Notification.tenant_id == tenant_id,
                        Notification.id == notification_id,
                        Notification.recipient_membership_id == membership_id,
                    )
                )
            ).first()
            if owned is None:
                raise NotFound(
                    "This notification no longer exists. It may have been deleted.",
                    detail=f"notification {notification_id}",
                )

    async def mark_all_read(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, membership_id: uuid.UUID
    ) -> int:
        rows = (
            (
                await session.execute(
                    update(Notification)
                    .where(
                        Notification.tenant_id == tenant_id,
                        Notification.recipient_membership_id == membership_id,
                        Notification.read_at.is_(None),
                    )
                    .values(read_at=datetime.now(UTC))
                    .returning(Notification.id)
                )
            )
            .scalars()
            .all()
        )
        return len(rows)

    # -- outbox (worker only) ----------------------------------------------------

    async def pending_emails(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, limit: int = 200
    ) -> list[Notification]:
        """Committed notifications asking for an email that have not had one."""
        return list(
            (
                await session.execute(
                    select(Notification)
                    .where(
                        Notification.tenant_id == tenant_id,
                        Notification.email_requested.is_(True),
                        Notification.emailed_at.is_(None),
                    )
                    .order_by(Notification.created_at)
                    .limit(limit)
                )
            ).scalars()
        )

    async def mark_emailed(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, ids: Sequence[uuid.UUID]
    ) -> None:
        if not ids:
            return
        await session.execute(
            update(Notification)
            .where(Notification.tenant_id == tenant_id, Notification.id.in_(list(ids)))
            .values(emailed_at=datetime.now(UTC))
        )


notification_service = NotificationService()
