"""notifications — in-app inbox with an email outbox

Revision ID: e4a9c7d21f08
Revises: c7e0a1f2b8d3
Create Date: 2026-08-24 13:00:00.000000

One tenant-owned table, so RLS + grants land with it (rule 12). Not append-only:
a notification is read and eventually pruned, unlike the history tables. The kind
values are duplicated here rather than imported so the migration stays a fixed
snapshot of the schema at this revision.

No permission key ships with this table: the routes reuse ``tenant:read`` (every
member holds it) and scope to the caller's own rows in the service, so there is
no key to seed and no role to backfill.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.db.rls import disable_rls, enable_rls, grant_crud

revision: str = "e4a9c7d21f08"
down_revision: str | None = "c7e0a1f2b8d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOTIFICATION_KINDS = (
    "assigned",
    "comment",
    "status",
    "sla_breach",
    "sla_due",
    "approval",
    "recurrence",
)


def _in(column: str, values: tuple[str, ...]) -> str:
    joined = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({joined})"


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_membership_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("object_type", sa.Text(), nullable=True),
        sa.Column("object_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("email_requested", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("emailed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("read_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name="fk_notifications__tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["recipient_membership_id"],
            ["tenant_memberships.id"],
            ondelete="CASCADE",
            name="fk_notifications__recipient_membership_id",
        ),
        sa.CheckConstraint(
            _in("kind", NOTIFICATION_KINDS), name=conv("ck_notifications__kind_valid")
        ),
    )
    op.create_index(
        "ix_notifications__tenant_id_recipient_membership_id_created_at",
        "notifications",
        ["tenant_id", "recipient_membership_id", "created_at"],
    )
    # The outbox sweep only ever touches unsent rows; a partial index keeps that
    # set indexed and tiny rather than scanning the whole table every tick.
    op.create_index(
        "ix_notifications__outbox",
        "notifications",
        ["tenant_id"],
        postgresql_where=sa.text("email_requested AND emailed_at IS NULL"),
    )
    enable_rls("notifications")
    grant_crud("notifications")


def downgrade() -> None:
    disable_rls("notifications")
    op.drop_index("ix_notifications__outbox", table_name="notifications")
    op.drop_index(
        "ix_notifications__tenant_id_recipient_membership_id_created_at",
        table_name="notifications",
    )
    op.drop_table("notifications")
