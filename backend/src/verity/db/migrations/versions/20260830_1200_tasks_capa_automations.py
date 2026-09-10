"""CAPA actions on issues, and the tenant automations config table.

Both tables are tenant-owned and RLS-forced (rules 1, 2, 12). ``issue_actions`` is a
mutable child of ``tasks`` carrying the corrective/preventive-action lifecycle under
an issue. ``task_automations`` stores only a tenant's *overrides* of the built-in
automation catalogue — the catalogue and its defaults live in the service, exactly
like ``sla_definitions`` and the severity matrix — so nothing is seeded here.

No new permission keys: CAPA and automation config are governed by ``tasks:read`` /
``tasks:manage``, which the built-in Admin role already resolves (decision 13).

Revision ID: f3b9c1a20e57
Revises: a7d2e9f10b34
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.db.rls import disable_rls, enable_rls, grant_crud

revision = "f3b9c1a20e57"
down_revision = "a7d2e9f10b34"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)

_CAPA_TYPES = ("corrective", "preventive", "containment", "verification")
_CAPA_STATUSES = ("planned", "in_progress", "blocked", "completed", "verified", "cancelled")
_TASK_KINDS = ("task", "issue")
_OWNER_RULES = ("source_owner", "unassigned")
_PRIORITIES = ("critical", "high", "medium", "low")

# Dropped in FK-safe order (children before anything they reference).
_TABLES = ("issue_actions", "task_automations")


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


def upgrade() -> None:
    op.create_table(
        "issue_actions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("task_id", _UUID, nullable=False),
        sa.Column("action_type", sa.Text(), nullable=False, server_default=sa.text("'corrective'")),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_membership_id", _UUID, nullable=True),
        sa.Column("due_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'planned'")),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("verified_by_membership_id", _UUID, nullable=True),
        sa.Column("verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("auto_generated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("promoted_task_id", _UUID, nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name="fk_issue_actions__tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["tasks.id"], ondelete="CASCADE", name="fk_issue_actions__task_id"
        ),
        sa.ForeignKeyConstraint(
            ["owner_membership_id"],
            ["tenant_memberships.id"],
            ondelete="SET NULL",
            name="fk_issue_actions__owner_membership_id",
        ),
        sa.ForeignKeyConstraint(
            ["verified_by_membership_id"],
            ["tenant_memberships.id"],
            ondelete="SET NULL",
            name="fk_issue_actions__verified_by_membership_id",
        ),
        sa.ForeignKeyConstraint(
            ["promoted_task_id"],
            ["tasks.id"],
            ondelete="SET NULL",
            name="fk_issue_actions__promoted_task_id",
        ),
        _in("issue_actions", "action_type", _CAPA_TYPES),
        _in("issue_actions", "status", _CAPA_STATUSES),
    )
    op.create_index(
        "ix_issue_actions__tenant_id_task_id", "issue_actions", ["tenant_id", "task_id"]
    )

    op.create_table(
        "task_automations",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("automation_key", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("creates", sa.Text(), nullable=False, server_default=sa.text("'task'")),
        sa.Column(
            "owner_rule", sa.Text(), nullable=False, server_default=sa.text("'source_owner'")
        ),
        sa.Column("priority", sa.Text(), nullable=False, server_default=sa.text("'medium'")),
        sa.Column("due_in_days", sa.Integer(), nullable=False, server_default=sa.text("7")),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name="fk_task_automations__tenant_id"
        ),
        _in("task_automations", "creates", _TASK_KINDS),
        _in("task_automations", "owner_rule", _OWNER_RULES),
        _in("task_automations", "priority", _PRIORITIES),
        sa.UniqueConstraint("tenant_id", "automation_key", name="uq_task_automations__tenant_key"),
    )

    for table in _TABLES:
        enable_rls(table)
        grant_crud(table)


def downgrade() -> None:
    for table in _TABLES:
        disable_rls(table)
        op.drop_table(table)
