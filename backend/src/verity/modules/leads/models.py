"""The ``demo_requests`` table: who asked for a demo, from where, and what we did about it.

**Provider plane, no ``tenant_id``** (CLAUDE.md, rule 2). A demo request is a prospect
asking the platform's owner for a conversation, made before any tenant exists, so it
belongs to no tenant and cannot be scoped to one. It is therefore not ``TenantScoped``;
what polices it instead is the provider plane's own wall. The migration enables and
forces row-level security with a policy keyed on ``app.provider_plane``, which only
``core.db.provider_session_scope`` sets, and gives the application role no ``DELETE``.

``source`` here is *which button on the website was clicked*, a label for the owner to
read. It is not the integration-origin column other tables carry (``Integratable``): a
demo request is typed by a visitor, not synced from a system, and nothing will ever
upsert one by an external id.

Personal data lives only in this table, never in a log line and never in the audit
trail: the audit row for a request carries its id and the three non-personal labels.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column

from verity.db.base import Base, Timestamped, UUIDPrimaryKey


class DemoRequest(UUIDPrimaryKey, Timestamped, Base):
    """One submission of the website's demo-request form."""

    __tablename__ = "demo_requests"

    full_name: Mapped[str]
    email: Mapped[str]
    """Lower-cased and stripped, so the once-a-day confirmation check can compare it
    for equality and the ``(email, created_at)`` index can serve it."""

    company: Mapped[str]
    message: Mapped[str | None] = mapped_column(default=None)
    interest: Mapped[str | None] = mapped_column(default=None)
    source: Mapped[str | None] = mapped_column(default=None)
    page: Mapped[str | None] = mapped_column(default=None)

    notified_at: Mapped[datetime | None] = mapped_column(default=None)
    """When the owner's notification was sent. NULL means it was not: either nobody was
    configured to receive it or the mail failed, and the request is still stored."""

    confirmation_sent_at: Mapped[datetime | None] = mapped_column(default=None)
    """When the visitor's receipt was sent. Also the memory behind "at most one receipt
    per address per day"."""

    __table_args__ = (Index("ix_demo_requests__email_created_at", "email", "created_at"),)

    def __repr__(self) -> str:
        # Deliberately only the id: this string ends up in tracebacks, and every other
        # column is somebody's personal data.
        return f"DemoRequest(id={self.id!r})"
