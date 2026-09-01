"""Task & Issue Management — the operational work register.

One entity, discriminated by ``task_kind`` (D1): a *task* is a piece of work, an
*issue* is a finding. A single ``status`` (D2) drives the lifecycle; the legal
moves live in the service and are served to the client, never duplicated in a
column. ``task_transitions`` is the immutable, columnar history (D4 / ADR-0005),
separate from — and additional to — the platform ``audit_log`` (rule 5).

SLA is stored as a deadline and *derived* on read (D3): ``sla_due_at`` is a fact,
whether it is breached is a function of the clock. A ``blocked`` task pauses the
clock via ``sla_paused_*``. Severity for an issue comes from the impact-by-urgency
matrix (D7); an override carries a required reason. Many people do the work
(``task_assignees``, D9) while one ``owner`` stays accountable. Anything that
links a task to a control/evidence/risk rides the polymorphic ``links`` table
(ADR-0003), never a column here.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Final

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.elements import conv

from verity.db.base import (
    Base,
    Integratable,
    TenantScoped,
    Timestamped,
    UUIDPrimaryKey,
    integration_unique,
    status_check,
    tenant_index,
)

TASK_KINDS: Final[tuple[str, ...]] = ("task", "issue")
TASK_STATUSES: Final[tuple[str, ...]] = (
    "open",
    "in_progress",
    "blocked",
    "under_review",
    "closed",
    "cancelled",
)
PRIORITIES: Final[tuple[str, ...]] = ("critical", "high", "medium", "low")
IMPACTS: Final[tuple[str, ...]] = ("high", "medium", "low")
URGENCIES: Final[tuple[str, ...]] = ("high", "medium", "low")
SEVERITIES: Final[tuple[str, ...]] = ("critical", "high", "medium", "low", "informational")
CATEGORIES: Final[tuple[str, ...]] = (
    "security",
    "privacy",
    "operations",
    "data",
    "regulatory",
    "vendor",
    "other",
)
APPROVAL_STATUSES: Final[tuple[str, ...]] = ("not_required", "pending", "approved", "rejected")

# CAPA (the corrective/preventive actions under an issue).
CAPA_TYPES: Final[tuple[str, ...]] = ("corrective", "preventive", "containment", "verification")
CAPA_STATUSES: Final[tuple[str, ...]] = (
    "planned",
    "in_progress",
    "blocked",
    "completed",
    "verified",
    "cancelled",
)
AUTOMATION_OWNER_RULES: Final[tuple[str, ...]] = ("source_owner", "unassigned")

_MEMBERSHIP_FK = "tenant_memberships.id"


class Task(UUIDPrimaryKey, TenantScoped, Timestamped, Integratable, Base):
    """A task or an issue — one row in the work register."""

    __tablename__ = "tasks"

    code: Mapped[str]  # TSK-0001
    task_kind: Mapped[str] = mapped_column(default="task")
    title: Mapped[str]
    description: Mapped[str | None] = mapped_column(default=None)

    status: Mapped[str] = mapped_column(default="open")
    priority: Mapped[str] = mapped_column(default="medium")
    category: Mapped[str] = mapped_column(default="operations")

    # Issue severity machinery (D7). Impact-by-urgency resolve to severity via the
    # matrix; an override wins and carries a reason.
    impact: Mapped[str | None] = mapped_column(default=None)
    urgency: Mapped[str | None] = mapped_column(default=None)
    severity: Mapped[str | None] = mapped_column(default=None)
    severity_override: Mapped[str | None] = mapped_column(default=None)
    severity_override_reason: Mapped[str | None] = mapped_column(default=None)

    sla_level: Mapped[str | None] = mapped_column(default=None)

    owner_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    reporter_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )

    # The clock (D3). detected_at anchors the SLA; sla_due_at is the stored
    # deadline; the paused_* pair bank elapsed time while blocked.
    detected_at: Mapped[datetime | None] = mapped_column(default=None)
    due_at: Mapped[datetime | None] = mapped_column(default=None)
    sla_due_at: Mapped[datetime | None] = mapped_column(default=None)
    sla_paused_at: Mapped[datetime | None] = mapped_column(default=None)
    sla_paused_ms: Mapped[int] = mapped_column(default=0, server_default=text("0"))

    started_at: Mapped[datetime | None] = mapped_column(default=None)
    resolved_at: Mapped[datetime | None] = mapped_column(default=None)
    closed_at: Mapped[datetime | None] = mapped_column(default=None)
    closure_note: Mapped[str | None] = mapped_column(default=None)
    cancelled_reason: Mapped[str | None] = mapped_column(default=None)

    # Sub-tasks (one level, enforced in the service). recurrence_parent points a
    # generated instance back at the one it recurred from.
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), default=None
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("task_templates.id", ondelete="SET NULL"), default=None
    )
    recurrence_rule: Mapped[str | None] = mapped_column(default=None)  # RFC 5545 RRULE
    recurrence_parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), default=None
    )
    next_occurrence_at: Mapped[datetime | None] = mapped_column(default=None)

    requires_approval: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    approval_status: Mapped[str] = mapped_column(default="not_required")
    approved_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    approved_at: Mapped[datetime | None] = mapped_column(default=None)

    # Provenance: the *kind* of object this was raised from (a control test, a
    # vendor review). NULL = raised by hand. The actual object is joined through
    # the links table; this is denormalised so a register row needs no extra
    # query to show its origin. Distinct from Integratable.source (the connector).
    raised_from_type: Mapped[str | None] = mapped_column(default=None)

    created_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )

    __table_args__ = (
        status_check("tasks", "task_kind", TASK_KINDS),
        status_check("tasks", "status", TASK_STATUSES),
        status_check("tasks", "priority", PRIORITIES),
        status_check("tasks", "category", CATEGORIES),
        status_check("tasks", "approval_status", APPROVAL_STATUSES),
        # An override without a reason is exactly the audit gap the reason exists
        # to close, so the database refuses it.
        CheckConstraint(
            "(severity_override IS NULL) OR (severity_override_reason IS NOT NULL)",
            name=conv("ck_tasks__override_has_reason"),
        ),
        CheckConstraint(
            "(status <> 'cancelled') OR (cancelled_reason IS NOT NULL)",
            name=conv("ck_tasks__cancel_has_reason"),
        ),
        UniqueConstraint("tenant_id", "code", name="uq_tasks__tenant_code"),
        integration_unique("tasks"),
        tenant_index("tasks", "status"),
        tenant_index("tasks", "task_kind", "status"),
        tenant_index("tasks", "sla_due_at"),
        tenant_index("tasks", "due_at"),
        tenant_index("tasks", "parent_task_id"),
    )

    def __repr__(self) -> str:
        return f"Task(id={self.id!r}, tenant_id={self.tenant_id!r}, code={self.code!r})"


class TaskAssignee(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A person doing the work (D9). Many per task; the owner is separate."""

    __tablename__ = "task_assignees"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    membership_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_MEMBERSHIP_FK, ondelete="CASCADE"))

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "task_id", "membership_id", name="uq_task_assignees__task_member"
        ),
        tenant_index("task_assignees", "task_id"),
        tenant_index("task_assignees", "membership_id"),
    )


class TaskTransition(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """Immutable, columnar history (D4 / ADR-0005). One row per changed field, so
    "who changed the assignee, and when" is a WHERE clause. Append-only: insert
    only, enforced by revoked grant + trigger."""

    __tablename__ = "task_transitions"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    actor_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    field_changed: Mapped[str]  # "status", "priority", "assignees", "created", …
    old_value: Mapped[str | None] = mapped_column(default=None)
    new_value: Mapped[str | None] = mapped_column(default=None)
    note: Mapped[str | None] = mapped_column(default=None)
    occurred_at: Mapped[datetime] = mapped_column()

    __table_args__ = (tenant_index("task_transitions", "task_id"),)


class TaskComment(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """Discussion on a task. Flat — no threading until it is actually built."""

    __tablename__ = "task_comments"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    author_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    body: Mapped[str]

    __table_args__ = (tenant_index("task_comments", "task_id"),)


class TaskAttachment(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A file on a task, or on one of its transitions. Held in the object store."""

    __tablename__ = "task_attachments"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    # Set when the file was attached as part of a transition, not standalone.
    transition_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("task_transitions.id", ondelete="SET NULL"), default=None
    )
    filename: Mapped[str]
    object_key: Mapped[str]
    size_bytes: Mapped[int | None] = mapped_column(default=None)
    uploaded_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )

    __table_args__ = (tenant_index("task_attachments", "task_id"),)


class TaskWatcher(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """Someone kept in the loop on a task without owning or working it."""

    __tablename__ = "task_watchers"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    membership_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_MEMBERSHIP_FK, ondelete="CASCADE"))

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "task_id", "membership_id", name="uq_task_watchers__task_member"
        ),
        tenant_index("task_watchers", "task_id"),
    )


class TaskTemplate(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A reusable task definition with its sub-task checklist and optional
    recurrence. Instantiating clones the sub-tasks as fresh open rows."""

    __tablename__ = "task_templates"

    name: Mapped[str]
    task_kind: Mapped[str] = mapped_column(default="task")
    priority: Mapped[str] = mapped_column(default="medium")
    category: Mapped[str] = mapped_column(default="operations")
    sla_level: Mapped[str | None] = mapped_column(default=None)
    description: Mapped[str | None] = mapped_column(default=None)
    # The sub-task titles to create with the task, in order.
    subtasks: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    recurrence_rule: Mapped[str | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("task_templates", "task_kind", TASK_KINDS),
        status_check("task_templates", "priority", PRIORITIES),
        status_check("task_templates", "category", CATEGORIES),
        UniqueConstraint("tenant_id", "name", name="uq_task_templates__tenant_name"),
    )


class SlaDefinition(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A named SLA level a task can carry. Per tenant; the service falls back to a
    hardcoded default set so a fresh tenant works with zero configuration."""

    __tablename__ = "sla_definitions"

    level: Mapped[str]
    respond_hours: Mapped[int]
    resolve_hours: Mapped[int]

    __table_args__ = (
        UniqueConstraint("tenant_id", "level", name="uq_sla_definitions__tenant_level"),
    )


class TaskSeverityMatrixCell(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One impact-by-urgency cell (D7): the severity, the SLA hours and the default
    owner an issue at that intersection gets. Absent cells fall back to a built-in
    default in the service, so the grid never has to be fully filled in."""

    __tablename__ = "task_severity_matrix"

    impact: Mapped[str]
    urgency: Mapped[str]
    severity: Mapped[str]
    respond_hours: Mapped[int]
    resolve_hours: Mapped[int]
    default_owner_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )

    __table_args__ = (
        status_check("task_severity_matrix", "impact", IMPACTS),
        status_check("task_severity_matrix", "urgency", URGENCIES),
        status_check("task_severity_matrix", "severity", SEVERITIES),
        UniqueConstraint("tenant_id", "impact", "urgency", name="uq_task_severity_matrix__cell"),
    )


class TaskSavedView(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A named, shareable filter set over the register (D8). Contract Compliance,
    Awaiting approval and the rest are seeded rows, not bespoke screens."""

    __tablename__ = "task_saved_views"

    name: Mapped[str]
    filters: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    is_shared: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    owner_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    position: Mapped[int] = mapped_column(default=0, server_default=text("0"))

    __table_args__ = (tenant_index("task_saved_views", "owner_membership_id"),)


class IssueAction(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A corrective or preventive action (CAPA) under an issue. It runs its own
    lifecycle (planned → in_progress → completed → verified, plus blocked/cancelled)
    independently of the parent issue's status; the legal moves live in the service.
    An action can be promoted into its own task once it needs assignees of its own."""

    __tablename__ = "issue_actions"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    action_type: Mapped[str] = mapped_column(
        default="corrective", server_default=text("'corrective'")
    )
    title: Mapped[str]
    description: Mapped[str | None] = mapped_column(default=None)
    owner_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    due_at: Mapped[datetime | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="planned", server_default=text("'planned'"))
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    verified_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    verified_at: Mapped[datetime | None] = mapped_column(default=None)
    # True for the action auto-created when an issue is raised from an event.
    auto_generated: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    # Set once this action has been promoted into its own task.
    promoted_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), default=None
    )

    __table_args__ = (
        status_check("issue_actions", "action_type", CAPA_TYPES),
        status_check("issue_actions", "status", CAPA_STATUSES),
        tenant_index("issue_actions", "task_id"),
    )


class TaskAutomation(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A tenant's customisation of a built-in automation rule. The catalogue and its
    defaults live in the service; a row exists here only once a tenant changes a rule,
    matching how sla_definitions and the severity matrix are stored."""

    __tablename__ = "task_automations"

    automation_key: Mapped[str]
    enabled: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    creates: Mapped[str] = mapped_column(default="task", server_default=text("'task'"))
    owner_rule: Mapped[str] = mapped_column(
        default="source_owner", server_default=text("'source_owner'")
    )
    priority: Mapped[str] = mapped_column(default="medium", server_default=text("'medium'"))
    due_in_days: Mapped[int] = mapped_column(default=7, server_default=text("7"))

    __table_args__ = (
        status_check("task_automations", "creates", TASK_KINDS),
        status_check("task_automations", "owner_rule", AUTOMATION_OWNER_RULES),
        status_check("task_automations", "priority", PRIORITIES),
        UniqueConstraint("tenant_id", "automation_key", name="uq_task_automations__tenant_key"),
    )
