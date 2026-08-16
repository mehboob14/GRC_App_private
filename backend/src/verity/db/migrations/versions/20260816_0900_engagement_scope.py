"""engagement — the audit being prepared for and the scope it covers

Revision ID: b4d8f16c2e07
Revises: a7c2e5f81b93
Create Date: 2026-08-16 09:00:00.000000

One tenant-owned table, so RLS and grants land here with it (rule 12) and a
working downgrade drops it cleanly.

``categories_in_scope`` is a text[] rather than a child table on purpose: the
vocabulary is closed and tiny (five Trust Services Categories), it is read as a
whole every time, and it is never joined against. A join table would be three
more objects to keep in step for no query it would make possible.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.db.rls import enable_rls, grant_crud

revision: str = "b4d8f16c2e07"
down_revision: str | None = "a7c2e5f81b93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUDIT_TYPES = ("type_1", "type_2")
ENGAGEMENT_STATUSES = ("draft", "active", "closed")


def _in_list(column: str, allowed: tuple[str, ...]) -> str:
    joined = ", ".join(f"'{value}'" for value in allowed)
    return f"{column} IN ({joined})"


def _timestamps() -> tuple[sa.Column[Any], sa.Column[Any]]:
    return (
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def upgrade() -> None:
    op.create_table(
        "engagements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("framework_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("audit_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("window_start", sa.Date(), nullable=True),
        sa.Column("window_end", sa.Date(), nullable=True),
        sa.Column(
            "categories_in_scope",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_engagements__tenant_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["framework_version_id"],
            ["framework_versions.id"],
            name=op.f("fk_engagements__framework_version_id"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            _in_list("audit_type", AUDIT_TYPES),
            name=op.f("ck_engagements__audit_type_valid"),
        ),
        sa.CheckConstraint(
            _in_list("status", ENGAGEMENT_STATUSES),
            name=op.f("ck_engagements__status_valid"),
        ),
        # Type II observes a period and needs both bounds; Type I is a point in
        # time and needs neither. A half-specified window is a bug, not a state.
        sa.CheckConstraint(
            "(audit_type = 'type_2') = (window_start IS NOT NULL AND window_end IS NOT NULL)",
            name="ck_engagements__window_matches_type",
        ),
        sa.CheckConstraint(
            "window_end IS NULL OR window_start IS NULL OR window_end >= window_start",
            name="ck_engagements__window_ordered",
        ),
        sa.UniqueConstraint("tenant_id", name="uq_engagements__tenant"),
    )
    enable_rls("engagements")
    grant_crud("engagements")


def downgrade() -> None:
    op.drop_table("engagements")
