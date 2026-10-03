"""Request/response contracts for the Task & Issue module.

Response shapes mirror the frontend's `types.ts` so the mock → real swap (Phase C)
is a one-file change on that side. Responses are built from the service's View
dataclasses (and, for config, ORM rows) via ``from_attributes``.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from verity.modules.tasks.recurrence import MAX_COUNT, MAX_INTERVAL
from verity.modules.tenancy.schemas import UtcDateTime


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# -- responses ---------------------------------------------------------------


class MemberOut(_Response):
    membership_id: uuid.UUID
    name: str


class TaskOut(_Response):
    id: uuid.UUID
    code: str
    task_kind: str
    title: str
    status: str
    priority: str
    severity: str | None
    category: str
    owner: MemberOut | None
    assignees: list[MemberOut]
    sla_level: str | None
    sla_due_at: UtcDateTime | None
    sla_state: str
    detected_at: UtcDateTime | None
    due_at: UtcDateTime | None
    created_at: UtcDateTime
    updated_at: UtcDateTime
    recurrence_summary: str | None
    parent_task_id: uuid.UUID | None
    source: str
    subtask_count: int
    comment_count: int
    link_count: int
    attachment_count: int


class TransitionOut(_Response):
    id: uuid.UUID
    actor: str | None
    field_changed: str
    old_value: str | None
    new_value: str | None
    note: str | None
    occurred_at: UtcDateTime


class CommentOut(_Response):
    id: uuid.UUID
    author: str | None
    body: str
    created_at: UtcDateTime


class CapaActionOut(_Response):
    id: uuid.UUID
    action_type: str
    title: str
    description: str
    owner: MemberOut | None
    due_at: UtcDateTime | None
    status: str
    completed_at: UtcDateTime | None
    verified_by: MemberOut | None
    verified_at: UtcDateTime | None
    auto_generated: bool
    promoted_task_code: str | None
    created_at: UtcDateTime


class RepeatOut(_Response):
    frequency: str
    interval: int
    until: date | None
    count: int | None


class AttachmentOut(_Response):
    """One piece of evidence on a task. ``id`` is the evidence item's own id, the one the
    evidence library knows it by."""

    id: uuid.UUID
    title: str
    evidence_type: str
    kind: str
    filename: str | None
    content_type: str | None
    size_bytes: int | None
    sha256: str | None
    link_url: str | None
    renewal_date: date | None
    freshness: str
    review_status: str
    attached_by: str | None
    attached_at: UtcDateTime | None
    transition_id: uuid.UUID | None


class TaskDetailOut(TaskOut):
    description: str
    impact: str | None
    urgency: str | None
    severity_override: str | None
    severity_override_reason: str | None
    reporter: MemberOut | None
    started_at: UtcDateTime | None
    resolved_at: UtcDateTime | None
    closed_at: UtcDateTime | None
    closure_note: str | None
    cancelled_reason: str | None
    approval_required: bool
    approval_status: str
    approver: MemberOut | None
    approved_at: UtcDateTime | None
    recurrence_rule: str | None
    repeat: RepeatOut | None
    next_occurrence_at: UtcDateTime | None
    recurrence_parent_id: uuid.UUID | None
    recurrence_parent_code: str | None
    subtasks: list[TaskOut]
    comments: list[CommentOut]
    transitions: list[TransitionOut]
    watchers: list[MemberOut]
    capa_actions: list[CapaActionOut]
    attachments: list[AttachmentOut]
    allowed_transitions: list[str]


class TaskPageOut(_Response):
    items: list[TaskOut]
    total: int


class SlaDefinitionOut(_Response):
    level: str
    respond_hours: int
    resolve_hours: int


class SeverityMatrixCellOut(_Response):
    impact: str
    urgency: str
    severity: str
    respond_hours: int
    resolve_hours: int
    default_owner_membership_id: uuid.UUID | None
    is_default: bool


class SavedViewOut(_Response):
    id: uuid.UUID
    name: str
    filters: dict[str, Any]
    is_shared: bool
    position: int


class TaskTemplateOut(_Response):
    id: uuid.UUID
    name: str
    task_kind: str
    priority: str
    category: str
    sla_level: str | None
    description: str | None
    subtasks: list[str]
    recurrence_rule: str | None


class _AssigneeLoadOut(_Response):
    member: MemberOut
    open: int


class _AgeBandOut(_Response):
    band: str
    count: int


class _MttrOut(_Response):
    severity: str
    days: float
    count: int


class TaskSummaryOut(_Response):
    open_total: int
    open_by_priority: dict[str, int]
    breaching_now: int
    due_soon: int
    ageing: list[_AgeBandOut]
    throughput: int
    by_assignee: list[_AssigneeLoadOut]
    mttr: list[_MttrOut]


class AutomationOut(_Response):
    id: str
    name: str
    trigger: str
    source: str
    owner_label: str
    creates: str
    enabled: bool
    owner_rule: str
    priority: str
    due_in_days: int
    available: bool


# -- requests ----------------------------------------------------------------


class RepeatIn(_Request):
    """How a task repeats: every ``interval`` days, weeks, months, quarters or years, until
    a date, for a number of tasks (the first included), or without end."""

    frequency: str = Field(pattern="^(daily|weekly|monthly|quarterly|yearly)$")
    interval: int = Field(default=1, ge=1, le=MAX_INTERVAL)
    until: date | None = None
    count: int | None = Field(default=None, ge=1, le=MAX_COUNT)


class TaskCreate(_Request):
    task_kind: str = "task"
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=8000)
    priority: str = "medium"
    category: str = "operations"
    sla_level: str | None = None
    owner_membership_id: uuid.UUID | None = None
    assignee_ids: list[uuid.UUID] = Field(default_factory=list)
    due_at: datetime | None = None
    # Impact and urgency resolve to a severity through the workspace's matrix; a severity
    # chosen against the matrix is an override and carries its reason.
    impact: str | None = None
    urgency: str | None = None
    severity: str | None = None
    severity_reason: str | None = Field(default=None, max_length=1000)
    repeat: RepeatIn | None = None
    requires_approval: bool = False


class TaskUpdate(_Request):
    """An edit. The severity fields (impact, urgency, severity, severity_reason) are
    replaced together when any of them is sent, so send the whole set you want."""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=8000)
    priority: str | None = None
    category: str | None = None
    sla_level: str | None = None
    owner_membership_id: uuid.UUID | None = None
    clear_owner: bool = False
    due_at: datetime | None = None
    impact: str | None = None
    urgency: str | None = None
    severity: str | None = None
    severity_reason: str | None = Field(default=None, max_length=1000)
    repeat: RepeatIn | None = None
    clear_repeat: bool = False
    requires_approval: bool | None = None


class TransitionRequest(_Request):
    to_status: str
    note: str | None = Field(default=None, max_length=2000)
    # Evidence already in the library, attached to the task with this move.
    evidence_ids: list[uuid.UUID] = Field(default_factory=list, max_length=25)


class AssignRequest(_Request):
    membership_ids: list[uuid.UUID] = Field(default_factory=list)


class CommentRequest(_Request):
    body: str = Field(min_length=1, max_length=8000)


class SubtaskRequest(_Request):
    title: str = Field(min_length=1, max_length=300)


class ApprovalDecision(_Request):
    decision: str = Field(pattern="^(approved|rejected)$")
    note: str | None = Field(default=None, max_length=2000)


class MatrixCellUpdate(_Request):
    impact: str
    urgency: str
    severity: str
    respond_hours: int = Field(ge=0, le=100000)
    resolve_hours: int = Field(ge=0, le=100000)


class CapaCreate(_Request):
    action_type: str = "corrective"
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=8000)
    owner_membership_id: uuid.UUID | None = None
    due_at: datetime | None = None


class CapaUpdate(_Request):
    action_type: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=8000)
    owner_membership_id: uuid.UUID | None = None
    clear_owner: bool = False
    due_at: datetime | None = None


class CapaTransitionRequest(_Request):
    to_status: str


class SlaDefinitionUpsert(_Request):
    original_level: str | None = None
    level: str = Field(min_length=1, max_length=100)
    respond_hours: int = Field(ge=0, le=100000)
    resolve_hours: int = Field(ge=0, le=100000)


class AutomationUpdate(_Request):
    enabled: bool | None = None
    creates: str | None = None
    owner_rule: str | None = None
    priority: str | None = None
    due_in_days: int | None = Field(default=None, ge=0, le=3650)
