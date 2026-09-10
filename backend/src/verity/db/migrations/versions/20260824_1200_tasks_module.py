"""tasks module — register, history, workflow, SLA, templates, saved views

Revision ID: c7e0a1f2b8d3
Revises: b2f4a7c19d05
Create Date: 2026-08-24 12:00:00.000000

Ten tenant-owned tables, so RLS + grants land with them (rule 12).
``task_transitions`` is append-only (rule 5 / ADR-0005): revoked UPDATE/DELETE
plus the shared BEFORE UPDATE OR DELETE trigger. Seeds the four ``tasks:*``
permission keys — Admin resolves to every key that exists, so it picks them up
automatically; custom roles opt in through the Roles screen.

Per-tenant config (SLA levels, the severity matrix, saved views) is *not* seeded
here: the service carries hardcoded defaults, so a tenant with an empty matrix
still resolves severities. Rows are written when a tenant customises them.

Check-constraint names use ``conv()`` so the ``ck`` naming convention does not
wrap them a second time (the model does the same via ``status_check``).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.db.rls import disable_rls, drop_append_only, enable_rls, grant_crud, make_append_only

revision: str = "c7e0a1f2b8d3"
down_revision: str | None = "b2f4a7c19d05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TASK_KINDS = ("task", "issue")
TASK_STATUSES = ("open", "in_progress", "blocked", "under_review", "closed", "cancelled")
PRIORITIES = ("critical", "high", "medium", "low")
IMPACTS = ("high", "medium", "low")
URGENCIES = ("high", "medium", "low")
SEVERITIES = ("critical", "high", "medium", "low", "informational")
CATEGORIES = ("security", "privacy", "operations", "data", "regulatory", "vendor", "other")
APPROVAL_STATUSES = ("not_required", "pending", "approved", "rejected")

# Creation order respects the foreign keys; downgrade drops the reverse.
_TABLES = (
    "task_attachments",
    "task_transitions",
    "task_watchers",
    "task_comments",
    "task_assignees",
    "tasks",
    "task_saved_views",
    "task_severity_matrix",
    "sla_definitions",
    "task_templates",
)

_UUID = postgresql.UUID(as_uuid=True)


def _check(table: str, column: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    joined = ", ".join(f"'{v}'" for v in values)
    return sa.CheckConstraint(f"{column} IN ({joined})", name=conv(f"ck_{table}__{column}_valid"))


def _ts() -> tuple[sa.Column[Any], sa.Column[Any]]:
    return (
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def _member_fk(table: str, column: str, ondelete: str = "SET NULL") -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], ["tenant_memberships.id"], ondelete=ondelete, name=f"fk_{table}__{column}"
    )


def _tenant_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{table}__tenant_id"
    )


def _task_fk(table: str, ondelete: str = "CASCADE") -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["task_id"], ["tasks.id"], ondelete=ondelete, name=f"fk_{table}__task_id"
    )


def upgrade() -> None:
    op.create_table(
        "task_templates",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("task_kind", sa.Text(), nullable=False, server_default="task"),
        sa.Column("priority", sa.Text(), nullable=False, server_default="medium"),
        sa.Column("category", sa.Text(), nullable=False, server_default="operations"),
        sa.Column("sla_level", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "subtasks", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column("recurrence_rule", sa.Text(), nullable=True),
        *_ts(),
        _tenant_fk("task_templates"),
        _check("task_templates", "task_kind", TASK_KINDS),
        _check("task_templates", "priority", PRIORITIES),
        _check("task_templates", "category", CATEGORIES),
        sa.UniqueConstraint("tenant_id", "name", name="uq_task_templates__tenant_name"),
    )

    op.create_table(
        "sla_definitions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("level", sa.Text(), nullable=False),
        sa.Column("respond_hours", sa.Integer(), nullable=False),
        sa.Column("resolve_hours", sa.Integer(), nullable=False),
        *_ts(),
        _tenant_fk("sla_definitions"),
        sa.UniqueConstraint("tenant_id", "level", name="uq_sla_definitions__tenant_level"),
    )

    op.create_table(
        "task_severity_matrix",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("impact", sa.Text(), nullable=False),
        sa.Column("urgency", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("respond_hours", sa.Integer(), nullable=False),
        sa.Column("resolve_hours", sa.Integer(), nullable=False),
        sa.Column("default_owner_membership_id", _UUID, nullable=True),
        *_ts(),
        _tenant_fk("task_severity_matrix"),
        _member_fk("task_severity_matrix", "default_owner_membership_id"),
        _check("task_severity_matrix", "impact", IMPACTS),
        _check("task_severity_matrix", "urgency", URGENCIES),
        _check("task_severity_matrix", "severity", SEVERITIES),
        sa.UniqueConstraint("tenant_id", "impact", "urgency", name="uq_task_severity_matrix__cell"),
    )

    op.create_table(
        "task_saved_views",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "filters", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("owner_membership_id", _UUID, nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default=sa.text("0")),
        *_ts(),
        _tenant_fk("task_saved_views"),
        _member_fk("task_saved_views", "owner_membership_id"),
    )
    op.create_index(
        "ix_task_saved_views__tenant_id_owner_membership_id",
        "task_saved_views",
        ["tenant_id", "owner_membership_id"],
    )

    op.create_table(
        "tasks",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("task_kind", sa.Text(), nullable=False, server_default="task"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("priority", sa.Text(), nullable=False, server_default="medium"),
        sa.Column("category", sa.Text(), nullable=False, server_default="operations"),
        sa.Column("impact", sa.Text(), nullable=True),
        sa.Column("urgency", sa.Text(), nullable=True),
        sa.Column("severity", sa.Text(), nullable=True),
        sa.Column("severity_override", sa.Text(), nullable=True),
        sa.Column("severity_override_reason", sa.Text(), nullable=True),
        sa.Column("sla_level", sa.Text(), nullable=True),
        sa.Column("owner_membership_id", _UUID, nullable=True),
        sa.Column("reporter_membership_id", _UUID, nullable=True),
        sa.Column("detected_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("due_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("sla_due_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("sla_paused_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("sla_paused_ms", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("closure_note", sa.Text(), nullable=True),
        sa.Column("cancelled_reason", sa.Text(), nullable=True),
        sa.Column("parent_task_id", _UUID, nullable=True),
        sa.Column("template_id", _UUID, nullable=True),
        sa.Column("recurrence_rule", sa.Text(), nullable=True),
        sa.Column("recurrence_parent_id", _UUID, nullable=True),
        sa.Column("next_occurrence_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "requires_approval", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("approval_status", sa.Text(), nullable=False, server_default="not_required"),
        sa.Column("approved_by_membership_id", _UUID, nullable=True),
        sa.Column("approved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("raised_from_type", sa.Text(), nullable=True),
        sa.Column("created_by_membership_id", _UUID, nullable=True),
        sa.Column("source", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_ts(),
        _tenant_fk("tasks"),
        _member_fk("tasks", "owner_membership_id"),
        _member_fk("tasks", "reporter_membership_id"),
        _member_fk("tasks", "approved_by_membership_id"),
        _member_fk("tasks", "created_by_membership_id"),
        sa.ForeignKeyConstraint(
            ["parent_task_id"], ["tasks.id"], ondelete="CASCADE", name="fk_tasks__parent_task_id"
        ),
        sa.ForeignKeyConstraint(
            ["recurrence_parent_id"],
            ["tasks.id"],
            ondelete="SET NULL",
            name="fk_tasks__recurrence_parent_id",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["task_templates.id"],
            ondelete="SET NULL",
            name="fk_tasks__template_id",
        ),
        _check("tasks", "task_kind", TASK_KINDS),
        _check("tasks", "status", TASK_STATUSES),
        _check("tasks", "priority", PRIORITIES),
        _check("tasks", "category", CATEGORIES),
        _check("tasks", "approval_status", APPROVAL_STATUSES),
        sa.CheckConstraint(
            "(severity_override IS NULL) OR (severity_override_reason IS NOT NULL)",
            name=conv("ck_tasks__override_has_reason"),
        ),
        sa.CheckConstraint(
            "(status <> 'cancelled') OR (cancelled_reason IS NOT NULL)",
            name=conv("ck_tasks__cancel_has_reason"),
        ),
        sa.UniqueConstraint("tenant_id", "code", name="uq_tasks__tenant_code"),
        sa.UniqueConstraint(
            "tenant_id", "source", "external_id", name="uq_tasks__tenant_id_source_external_id"
        ),
    )
    op.create_index("ix_tasks__tenant_id_status", "tasks", ["tenant_id", "status"])
    op.create_index(
        "ix_tasks__tenant_id_task_kind_status", "tasks", ["tenant_id", "task_kind", "status"]
    )
    op.create_index("ix_tasks__tenant_id_sla_due_at", "tasks", ["tenant_id", "sla_due_at"])
    op.create_index("ix_tasks__tenant_id_due_at", "tasks", ["tenant_id", "due_at"])
    op.create_index("ix_tasks__tenant_id_parent_task_id", "tasks", ["tenant_id", "parent_task_id"])

    op.create_table(
        "task_assignees",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("task_id", _UUID, nullable=False),
        sa.Column("membership_id", _UUID, nullable=False),
        *_ts(),
        _tenant_fk("task_assignees"),
        _task_fk("task_assignees"),
        _member_fk("task_assignees", "membership_id", ondelete="CASCADE"),
        sa.UniqueConstraint(
            "tenant_id", "task_id", "membership_id", name="uq_task_assignees__task_member"
        ),
    )
    op.create_index(
        "ix_task_assignees__tenant_id_task_id", "task_assignees", ["tenant_id", "task_id"]
    )
    op.create_index(
        "ix_task_assignees__tenant_id_membership_id",
        "task_assignees",
        ["tenant_id", "membership_id"],
    )

    op.create_table(
        "task_comments",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("task_id", _UUID, nullable=False),
        sa.Column("author_membership_id", _UUID, nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        *_ts(),
        _tenant_fk("task_comments"),
        _task_fk("task_comments"),
        _member_fk("task_comments", "author_membership_id"),
    )
    op.create_index(
        "ix_task_comments__tenant_id_task_id", "task_comments", ["tenant_id", "task_id"]
    )

    op.create_table(
        "task_watchers",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("task_id", _UUID, nullable=False),
        sa.Column("membership_id", _UUID, nullable=False),
        *_ts(),
        _tenant_fk("task_watchers"),
        _task_fk("task_watchers"),
        _member_fk("task_watchers", "membership_id", ondelete="CASCADE"),
        sa.UniqueConstraint(
            "tenant_id", "task_id", "membership_id", name="uq_task_watchers__task_member"
        ),
    )
    op.create_index(
        "ix_task_watchers__tenant_id_task_id", "task_watchers", ["tenant_id", "task_id"]
    )

    op.create_table(
        "task_transitions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("task_id", _UUID, nullable=False),
        sa.Column("actor_membership_id", _UUID, nullable=True),
        sa.Column("field_changed", sa.Text(), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False),
        *_ts(),
        _tenant_fk("task_transitions"),
        _task_fk("task_transitions"),
        _member_fk("task_transitions", "actor_membership_id"),
    )
    op.create_index(
        "ix_task_transitions__tenant_id_task_id", "task_transitions", ["tenant_id", "task_id"]
    )

    op.create_table(
        "task_attachments",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("task_id", _UUID, nullable=False),
        sa.Column("transition_id", _UUID, nullable=True),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("uploaded_by_membership_id", _UUID, nullable=True),
        *_ts(),
        _tenant_fk("task_attachments"),
        _task_fk("task_attachments"),
        sa.ForeignKeyConstraint(
            ["transition_id"],
            ["task_transitions.id"],
            ondelete="SET NULL",
            name="fk_task_attachments__transition_id",
        ),
        _member_fk("task_attachments", "uploaded_by_membership_id"),
    )
    op.create_index(
        "ix_task_attachments__tenant_id_task_id", "task_attachments", ["tenant_id", "task_id"]
    )

    # RLS + grants on every table (rule 12).
    for table in reversed(_TABLES):
        enable_rls(table)
        grant_crud(table)
    # task_transitions is insert-only (rule 5 / ADR-0005): revoke UPDATE/DELETE and
    # attach the shared trigger, on top of the grant above.
    make_append_only("task_transitions")

    op.execute(
        "INSERT INTO permissions (key, module, action) VALUES "
        "('tasks:read', 'tasks', 'read'), "
        "('tasks:manage', 'tasks', 'manage'), "
        "('tasks:assign', 'tasks', 'assign'), "
        "('tasks:approve', 'tasks', 'approve') ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM permissions WHERE key IN "
        "('tasks:read', 'tasks:manage', 'tasks:assign', 'tasks:approve')"
    )
    drop_append_only("task_transitions")
    for table in _TABLES:
        disable_rls(table)
        op.drop_table(table)
