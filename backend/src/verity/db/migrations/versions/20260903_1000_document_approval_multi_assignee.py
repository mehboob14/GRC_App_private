"""Document approval tiers become multi-assignee: a tier is a mix of named
people, roles and groups, not one approver.

Two new tenant-owned, RLS-forced tables (rules 1, 2, 12):
``document_approval_targets`` (what the owner picked for the tier) and
``document_approval_assignees`` (who that resolves to today, and their own
decision). ``document_approvals.approver_membership_id`` is dropped — a tier's
completion is now computed from its assignees, not stored on one column.

Revision ID: afedee6a313a
Revises: e2a5c7d93f42
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.db.rls import disable_rls, enable_rls, grant_crud

revision = "afedee6a313a"
down_revision = "e2a5c7d93f42"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)

_TARGET_TYPES = ("user", "role", "group")
_ASSIGNEE_DECISIONS = ("pending", "approved", "rejected")

# Dropped children-first.
_TABLES = ("document_approval_assignees", "document_approval_targets")


def _ts() -> tuple[sa.Column[Any], sa.Column[Any]]:
    return (
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def _in(table: str, column: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    joined = ", ".join(f"'{v}'" for v in values)
    return sa.CheckConstraint(f"{column} IN ({joined})", name=conv(f"ck_{table}__{column}_valid"))


def _tenant_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{table}__tenant_id"
    )


def upgrade() -> None:
    # The old single-approver column: superseded by the assignee table, and no
    # tenant has live approval data yet to preserve (pre-launch).
    op.drop_constraint(
        "fk_document_approvals__approver_membership_id", "document_approvals", type_="foreignkey"
    )
    op.drop_column("document_approvals", "approver_membership_id")

    op.create_table(
        "document_approval_targets",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("approval_id", _UUID, nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", _UUID, nullable=False),
        sa.Column("target_name", sa.Text(), nullable=False),
        *_ts(),
        _tenant_fk("document_approval_targets"),
        sa.ForeignKeyConstraint(
            ["approval_id"],
            ["document_approvals.id"],
            ondelete="CASCADE",
            name="fk_document_approval_targets__approval_id",
        ),
        _in("document_approval_targets", "target_type", _TARGET_TYPES),
        sa.UniqueConstraint(
            "tenant_id",
            "approval_id",
            "target_type",
            "target_id",
            name="uq_document_approval_targets__target",
        ),
    )
    op.create_index(
        "ix_document_approval_targets__tenant_id_approval_id",
        "document_approval_targets",
        ["tenant_id", "approval_id"],
    )

    op.create_table(
        "document_approval_assignees",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("approval_id", _UUID, nullable=False),
        sa.Column("membership_id", _UUID, nullable=False),
        sa.Column(
            "source_target_ids",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("decision", sa.Text(), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("decided_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        *_ts(),
        _tenant_fk("document_approval_assignees"),
        sa.ForeignKeyConstraint(
            ["approval_id"],
            ["document_approvals.id"],
            ondelete="CASCADE",
            name="fk_document_approval_assignees__approval_id",
        ),
        sa.ForeignKeyConstraint(
            ["membership_id"],
            ["tenant_memberships.id"],
            ondelete="CASCADE",
            name="fk_document_approval_assignees__membership_id",
        ),
        _in("document_approval_assignees", "decision", _ASSIGNEE_DECISIONS),
        sa.UniqueConstraint(
            "tenant_id",
            "approval_id",
            "membership_id",
            name="uq_document_approval_assignees__member",
        ),
    )
    op.create_index(
        "ix_document_approval_assignees__tenant_id_approval_id",
        "document_approval_assignees",
        ["tenant_id", "approval_id"],
    )
    op.create_index(
        "ix_document_approval_assignees__tenant_id_membership_id",
        "document_approval_assignees",
        ["tenant_id", "membership_id"],
    )

    for table in reversed(_TABLES):
        enable_rls(table)
        grant_crud(table)


def downgrade() -> None:
    for table in _TABLES:
        disable_rls(table)
        op.drop_table(table)

    op.add_column(
        "document_approvals",
        sa.Column("approver_membership_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_document_approvals__approver_membership_id",
        "document_approvals",
        "tenant_memberships",
        ["approver_membership_id"],
        ["id"],
        ondelete="SET NULL",
    )
