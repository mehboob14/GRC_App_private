"""document reminders: acknowledgement chasing and review notices

Three small additions, no new table, so no new policy: the two tables already carry
forced RLS and their grants, and a column inherits both.

* ``document_ack_campaign_recipients`` records when each person was last chased and how
  often (``last_reminded_at``, ``reminder_count``), so a manual reminder can skip
  someone chased today and the campaign page can say who has been nudged.
* ``notifications.dedupe_key`` names the occasion a notice is about when the object
  alone does not. A document review notice is keyed on the review date, so one notice
  goes out per date and moving the date starts a new one. The kind and the object were
  already part of the existing once-only check; the date was the missing part.
* The notification kind constraint is widened by ``document_review_due``,
  ``document_review_overdue`` and ``document_ack_reminder``, the way the risk register
  migration widened it.

Revision ID: b4e1f9a2c7d3
Revises: a3b9c7e15d68
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql.elements import conv

revision: str = "b4e1f9a2c7d3"
down_revision: str | None = "a3b9c7e15d68"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_RECIPIENTS = "document_ack_campaign_recipients"

# Restated, not imported: a migration describes the schema at this revision.
OLD_NOTIFICATION_KINDS = (
    "assigned",
    "comment",
    "status",
    "sla_breach",
    "sla_due",
    "approval",
    "recurrence",
    "vendor_reassessment_due",
    "vendor_document_expiring",
    "risk_acceptance_requested",
    "risk_acceptance_decided",
    "risk_acceptance_expired",
    "risk_review_due",
)
NEW_NOTIFICATION_KINDS = (
    *OLD_NOTIFICATION_KINDS,
    "document_review_due",
    "document_review_overdue",
    "document_ack_reminder",
)


def _in(column: str, values: tuple[str, ...]) -> str:
    joined = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({joined})"


def _unforced(table: str, statement: str) -> None:
    """Run a data statement as the owner past FORCE RLS, which would otherwise
    filter every row out of an owner session with no tenant bound."""
    op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.execute(statement)
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def _set_notification_kinds(kinds: tuple[str, ...]) -> None:
    op.drop_constraint(conv("ck_notifications__kind_valid"), "notifications", type_="check")
    op.create_check_constraint(
        conv("ck_notifications__kind_valid"), "notifications", _in("kind", kinds)
    )


def upgrade() -> None:
    op.add_column(_RECIPIENTS, sa.Column("last_reminded_at", sa.TIMESTAMP(timezone=True)))
    op.add_column(
        _RECIPIENTS,
        sa.Column("reminder_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column("notifications", sa.Column("dedupe_key", sa.Text()))
    _set_notification_kinds(NEW_NOTIFICATION_KINDS)


def downgrade() -> None:
    new_only = tuple(k for k in NEW_NOTIFICATION_KINDS if k not in OLD_NOTIFICATION_KINDS)
    _unforced("notifications", f"DELETE FROM notifications WHERE {_in('kind', new_only)}")  # noqa: S608
    _set_notification_kinds(OLD_NOTIFICATION_KINDS)
    op.drop_column("notifications", "dedupe_key")
    op.drop_column(_RECIPIENTS, "reminder_count")
    op.drop_column(_RECIPIENTS, "last_reminded_at")
