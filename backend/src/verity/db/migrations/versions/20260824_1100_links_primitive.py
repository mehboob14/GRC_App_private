"""links — the polymorphic 360-degree association table (ADR-0003)

Revision ID: b2f4a7c19d05
Revises: a4c81f37b902
Create Date: 2026-08-24 11:00:00.000000

One tenant-owned table, so RLS + grants land with it (rule 12). Indexed in both
directions, so a lookup from either end is a tenant-scoped index scan. It is the
first table many later modules (tasks, risk, vendors, assets) depend on for their
long-tail linkage, which is why it ships on its own.

Not append-only: a link is an association that is drawn and removed, unlike the
history tables. The check-constraint values are duplicated here rather than
imported so the migration stays a fixed snapshot of the schema at this revision.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.db.rls import disable_rls, enable_rls, grant_crud

revision: str = "b2f4a7c19d05"
down_revision: str | None = "a4c81f37b902"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LINK_TYPES = (
    "task",
    "control",
    "evidence",
    "risk",
    "document",
    "vendor",
    "asset",
    "vulnerability",
    "incident",
)
LINK_RELATIONS = ("relates_to", "remediates", "caused_by", "depends_on", "duplicates")


def _in(column: str, values: tuple[str, ...]) -> str:
    # Values are module constants in this file, never input, so the interpolation
    # is safe (same pattern as the earlier category re-code migration).
    joined = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({joined})"


def upgrade() -> None:
    op.create_table(
        "links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_type", sa.Text(), nullable=False),
        sa.Column("from_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_type", sa.Text(), nullable=False),
        sa.Column("to_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation", sa.Text(), nullable=False, server_default="relates_to"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_membership_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name="fk_links__tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_membership_id"],
            ["tenant_memberships.id"],
            ondelete="SET NULL",
            name="fk_links__created_by_membership_id",
        ),
        # conv() marks these names as already convention-shaped; without it the ck
        # naming convention wraps them again into ck_links__ck_links__… and the model
        # (which uses status_check → conv) and the DB disagree on the name.
        sa.CheckConstraint(_in("from_type", LINK_TYPES), name=conv("ck_links__from_type_valid")),
        sa.CheckConstraint(_in("to_type", LINK_TYPES), name=conv("ck_links__to_type_valid")),
        sa.CheckConstraint(_in("relation", LINK_RELATIONS), name=conv("ck_links__relation_valid")),
        sa.UniqueConstraint(
            "tenant_id",
            "from_type",
            "from_id",
            "to_type",
            "to_id",
            "relation",
            name="uq_links__pair",
        ),
    )
    op.create_index(
        "ix_links__tenant_id_from_type_from_id", "links", ["tenant_id", "from_type", "from_id"]
    )
    op.create_index("ix_links__tenant_id_to_type_to_id", "links", ["tenant_id", "to_type", "to_id"])
    enable_rls("links")
    grant_crud("links")


def downgrade() -> None:
    disable_rls("links")
    op.drop_index("ix_links__tenant_id_to_type_to_id", table_name="links")
    op.drop_index("ix_links__tenant_id_from_type_from_id", table_name="links")
    op.drop_table("links")
