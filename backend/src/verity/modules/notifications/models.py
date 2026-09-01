"""In-app notifications, with an email outbox.

One row is one thing a member should know about — assigned to a task, a status
moved, an SLA about to breach. The row is the source of truth and shows in the
in-app inbox immediately. Email is *optional and out of band*: setting
``email_requested`` asks a worker to deliver a copy, and ``emailed_at`` stamps
when it did. That split is deliberate — email delivery is best-effort and must
never sit inside the transaction that produced the event (see ``core.email``),
so the sweep only ever sees already-committed rows and cannot resend a stamped
one (idempotent, rule for scheduled jobs in CLAUDE.md).

Notifications are ephemeral UX, not a compliance object (rule 6), so they carry
full CRUD and may be pruned.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Final

from sqlalchemy import ForeignKey, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column

from verity.db.base import Base, TenantScoped, UUIDPrimaryKey, status_check, tenant_index

NOTIFICATION_KINDS: Final[tuple[str, ...]] = (
    "assigned",  # you are now an assignee on a task
    "comment",  # a new comment on a task you are on
    "status",  # a task you are on changed status
    "sla_breach",  # a task you own/work has passed its SLA deadline
    "sla_due",  # a task you own/work is due within the warning window
    "approval",  # an approval decision was recorded on your task
    "recurrence",  # a recurring task spawned a new occurrence
)

_MEMBERSHIP_FK = "tenant_memberships.id"


class Notification(UUIDPrimaryKey, TenantScoped, Base):
    """One item in a member's inbox. ``object_type``/``object_id`` point at what
    it is about (a task, today) so the client can deep-link; both null for a
    notification that is not about a specific object."""

    __tablename__ = "notifications"

    recipient_membership_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="CASCADE")
    )
    kind: Mapped[str]
    title: Mapped[str]
    body: Mapped[str] = mapped_column(default="")
    object_type: Mapped[str | None] = mapped_column(default=None)
    object_id: Mapped[uuid.UUID | None] = mapped_column(default=None)

    # Outbox: email is a copy delivered by a worker, never in the request txn.
    email_requested: Mapped[bool] = mapped_column(server_default=text("false"), default=False)
    emailed_at: Mapped[datetime | None] = mapped_column(default=None)

    read_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        # "my inbox", newest first, is (tenant_id, recipient, created_at).
        tenant_index("notifications", "recipient_membership_id", "created_at"),
        # The outbox sweep only ever touches unsent rows; keep that set indexed
        # and tiny rather than scanning the whole table every tick.
        Index(
            "ix_notifications__outbox",
            "tenant_id",
            postgresql_where=text("email_requested AND emailed_at IS NULL"),
        ),
        status_check("notifications", "kind", NOTIFICATION_KINDS),
    )
