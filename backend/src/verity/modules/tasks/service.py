"""Task & Issue Management — business logic.

DB access lives here (no separate repository, matching the evidence and documents
modules). The rules that the frontend was built against live here too, as the one
authority: the transition allow-list (served to the client, never hardcoded in the
UI), SLA derivation (a stored deadline; breach is computed on read), and severity
resolution from the impact/urgency matrix.

Two records are written for every state change: a columnar ``task_transitions``
row (the domain history the detail page renders) and a platform ``audit_log`` row
(rule 5). They answer different questions and neither replaces the other.

Cross-module reads go through sibling *services* (rule 4): member names via IAM,
control/evidence labels via their services, links via the links primitive.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from pathlib import PurePosixPath
from typing import Any, Final

from sqlalchemy import BigInteger, Select, cast, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.core.logging import get_logger
from verity.core.storage import sanitise_filename
from verity.modules.audit.service import Actor, AuditService, Membership, System, audit_service
from verity.modules.links.service import link_service
from verity.modules.tasks.models import (
    AUTOMATION_OWNER_RULES,
    CAPA_STATUSES,
    CAPA_TYPES,
    CATEGORIES,
    IMPACTS,
    PRIORITIES,
    SEVERITIES,
    TASK_KINDS,
    TASK_STATUSES,
    URGENCIES,
    IssueAction,
    SlaDefinition,
    Task,
    TaskAssignee,
    TaskAutomation,
    TaskComment,
    TaskSavedView,
    TaskSeverityMatrixCell,
    TaskTemplate,
    TaskTransition,
    TaskWatcher,
)
from verity.modules.tasks.recurrence import Repeat, next_after, parse_rrule, summary, to_rrule
from verity.modules.tasks.severity import SeverityDecision, decide_severity
from verity.shared.ids import uuid7

logger = get_logger(__name__)

# -- shared rules (the client is served these; it never hardcodes them) ------

ALLOWED_TRANSITIONS: Final[dict[str, tuple[str, ...]]] = {
    "open": ("in_progress", "cancelled"),
    "in_progress": ("blocked", "under_review", "open", "cancelled"),
    "blocked": ("in_progress", "cancelled"),
    "under_review": ("closed", "in_progress"),
    "closed": ("in_progress",),  # reopen
    "cancelled": ("open",),  # reinstate
}

_ACTIVE: Final = ("open", "in_progress", "blocked", "under_review")

# CAPA action lifecycle — the legal moves, served to the client, never hardcoded there.
_CAPA_TRANSITIONS: Final[dict[str, tuple[str, ...]]] = {
    "planned": ("in_progress", "cancelled"),
    "in_progress": ("blocked", "completed", "cancelled"),
    "blocked": ("in_progress", "cancelled"),
    "completed": ("verified", "in_progress"),  # verify, or reopen
    "verified": ("in_progress",),  # reopen
    "cancelled": ("planned",),  # reinstate
}

# Reader-facing copy repeated across several raises. Same wording every time, so it
# lives once (the pattern audit/service.py uses for _CURSOR_ERROR).
_CODE_ERROR: Final = "We could not save this just now. Please try again in a moment."
_PRIORITY_ERROR: Final = "Pick a priority from the list: critical, high, medium or low."
_CATEGORY_ERROR: Final = "Pick a category from the list shown on the form."
_ACTION_TYPE_ERROR: Final = (
    "Pick an action type from the list: corrective, preventive, containment or verification."
)
_ACTION_TITLE_ERROR: Final = "Give this action a title before saving it."
_SEVERITY_ERROR: Final = (
    "Pick a severity from the list: critical, high, medium, low or informational."
)
_IMPACT_ERROR: Final = "Pick an impact of high, medium or low."
_URGENCY_ERROR: Final = "Pick an urgency of high, medium or low."
_APPROVAL_TO_CLOSE_ERROR: Final = (
    "This task needs approval before it can be closed. "
    "Send it for review, then ask an approver to approve it."
)
_APPROVAL_NOT_IN_REVIEW_ERROR: Final = (
    "Approval is given once the work has been sent for review. "
    "Move this task to under review first."
)
_REPEAT_NOT_HEAD_ERROR: Final = (
    "This task is one occurrence of a repeating task, so it cannot repeat on its own. "
    "Change the repeat on the first task in the series instead."
)
_REPEAT_ON_SUBTASK_ERROR: Final = "A sub-task cannot repeat. Set the repeat on the parent task."
_REPEAT_END_ERROR: Final = "Pick an end date after the first due date, or let the repeat go on."
_ATTACH_LIMIT_ERROR: Final = "Attach up to 5 files and 25 evidence items at a time."

_CODE_PREFIX: Final = "TSK-"
_MAX_UPLOADS: Final = 5
_MAX_PICKED_EVIDENCE: Final = 25

# Work the platform raises for itself is keyed on (source, external_id), the pair the
# schema makes unique per tenant (rule 9), so raising the same thing twice is refused by
# the database and not only by a check that could race a second worker.
_RECURRENCE_SOURCE: Final = "recurrence"
_AUTOMATION_SOURCE: Final = "automation"
_RENEWAL_AUTOMATION: Final = "evidence_stale"
_RENEWAL_RAISED_FROM: Final = "evidence"

# One run handles at most this many dates for one series. A scheduler that was down for a
# day catches up in one run; one that was down for a year does not flood the register in a
# single transaction, and finishes the job over the next runs.
_SPAWN_CATCH_UP_LIMIT: Final = 12

# The built-in automation catalogue. `available` follows which modules exist today;
# a rule that watches an unbuilt module reads as "Soon" and cannot be enabled. Only
# enabled/creates/owner_rule/priority/due_in_days are tenant-customisable (stored in
# task_automations); the rest are static properties of the rule.
_AUTOMATION_CATALOGUE: Final[tuple[dict[str, Any], ...]] = (
    {
        "id": "evidence_stale",
        "name": "Evidence went stale",
        "trigger": "When a piece of evidence passes its renewal date without a fresh version.",
        "source": "evidence",
        "owner_label": "the evidence's owner, or its control's owner",
        "creates": "task",
        "enabled": True,
        "owner_rule": "source_owner",
        "priority": "medium",
        "due_in_days": 7,
        "available": True,
    },
    {
        "id": "control_failed",
        "name": "Control check failed",
        "trigger": "When an automated check on a control returns a failing result.",
        "source": "control",
        "owner_label": "the control's owner",
        "creates": "issue",
        "enabled": True,
        "owner_rule": "source_owner",
        "priority": "high",
        "due_in_days": 3,
        "available": True,
    },
    {
        "id": "asset_decommissioned",
        "name": "Asset decommissioned",
        "trigger": "When an asset is moved to decommissioned, to close out access and inventory.",
        "source": "asset",
        "owner_label": "the asset's owner",
        "creates": "task",
        "enabled": False,
        "owner_rule": "source_owner",
        "priority": "medium",
        "due_in_days": 5,
        "available": True,
    },
    {
        "id": "vuln_overdue",
        "name": "Vulnerability past its remediation SLA",
        "trigger": "When an open vulnerability passes the remediation deadline for its severity.",
        "source": "vulnerability",
        "owner_label": "the affected asset's owner",
        "creates": "issue",
        "enabled": False,
        "owner_rule": "source_owner",
        "priority": "high",
        "due_in_days": 2,
        "available": False,
    },
    {
        "id": "vendor_report_expired",
        "name": "Vendor assurance report expired",
        "trigger": "When a vendor's SOC 2 or ISO report on file falls out of period.",
        "source": "vendor",
        "owner_label": "the vendor's owner",
        "creates": "issue",
        "enabled": False,
        "owner_rule": "source_owner",
        "priority": "high",
        "due_in_days": 5,
        "available": False,
    },
    {
        "id": "risk_over_appetite",
        "name": "Risk exceeded appetite",
        "trigger": "When a risk's residual score rises above the accepted appetite.",
        "source": "risk",
        "owner_label": "the risk's owner",
        "creates": "issue",
        "enabled": False,
        "owner_rule": "source_owner",
        "priority": "high",
        "due_in_days": 5,
        "available": False,
    },
)
_AUTOMATION_CUSTOMISABLE: Final = ("enabled", "creates", "owner_rule", "priority", "due_in_days")

# Zero-config fallbacks (D3/D7): a tenant that has customised nothing still gets a
# working SLA clock and severity resolution. Customised rows in the DB win.
_DEFAULT_RESOLVE_HOURS: Final[dict[str, int]] = {
    "P1 Critical": 24,
    "P2 High": 72,
    "P3 Standard": 168,
    "P4 Low": 504,
}
_DEFAULT_MATRIX: Final[dict[tuple[str, str], tuple[str, int]]] = {
    ("high", "high"): ("critical", 24),
    ("high", "medium"): ("high", 72),
    ("high", "low"): ("medium", 168),
    ("medium", "high"): ("high", 72),
    ("medium", "medium"): ("medium", 168),
    ("medium", "low"): ("low", 504),
    ("low", "high"): ("medium", 168),
    ("low", "medium"): ("low", 504),
    ("low", "low"): ("informational", 1440),
}


def sla_state(sla_due_at: datetime | None, status: str, *, now: datetime | None = None) -> str:
    """Derived on read from the stored deadline and the clock (D3)."""
    if status == "blocked":
        return "paused"
    if status in ("closed", "cancelled") or sla_due_at is None:
        return "none"
    now = now or datetime.now(UTC)
    delta = sla_due_at - now
    if delta.total_seconds() < 0:
        return "breached"
    if delta < timedelta(days=2):
        return "due_soon"
    return "on_track"


# -- domain views (returned to the router; never ORM rows) -------------------


@dataclass(frozen=True, slots=True)
class Member:
    membership_id: uuid.UUID
    name: str


@dataclass(frozen=True, slots=True)
class TaskView:
    id: uuid.UUID
    code: str
    task_kind: str
    title: str
    status: str
    priority: str
    severity: str | None
    category: str
    owner: Member | None
    assignees: list[Member]
    sla_level: str | None
    sla_due_at: datetime | None
    sla_state: str
    detected_at: datetime | None
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime
    recurrence_summary: str | None
    parent_task_id: uuid.UUID | None
    source: str
    subtask_count: int
    comment_count: int
    link_count: int
    attachment_count: int


@dataclass(frozen=True, slots=True)
class TransitionView:
    id: uuid.UUID
    actor: str | None
    field_changed: str
    old_value: str | None
    new_value: str | None
    note: str | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class CommentView:
    id: uuid.UUID
    author: str | None
    body: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CapaActionView:
    id: uuid.UUID
    action_type: str
    title: str
    description: str
    owner: Member | None
    due_at: datetime | None
    status: str
    completed_at: datetime | None
    verified_by: Member | None
    verified_at: datetime | None
    auto_generated: bool
    promoted_task_code: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AttachmentView:
    """One piece of evidence on a task. The attachment *is* the evidence item and the
    link that ties it to the task, so ``id`` is the evidence id and a file attached from
    the evidence page reads the same as one attached from the task."""

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
    # Who attached it and when, read from the task's own history. None for an item linked
    # from the evidence page, which leaves no task history to read it from.
    attached_by: str | None
    attached_at: datetime | None
    # The status change it was attached with, None when it was attached on its own.
    transition_id: uuid.UUID | None


@dataclass(frozen=True, slots=True)
class Upload:
    """A file that arrived with a request. The router has read the bytes; the store
    sniffs, hashes and caps them (``core.storage``), so none of that is repeated here."""

    filename: str
    data: bytes


@dataclass(frozen=True, slots=True)
class SeverityInput:
    """The severity fields of an edit, replaced together: impact and urgency resolve
    through the matrix, ``severity`` is the person's choice and ``reason`` explains a
    choice that differs from the matrix."""

    impact: str | None = None
    urgency: str | None = None
    severity: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class TaskDetailView(TaskView):
    description: str
    impact: str | None = None
    urgency: str | None = None
    severity_override: str | None = None
    severity_override_reason: str | None = None
    reporter: Member | None = None
    started_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    closure_note: str | None = None
    cancelled_reason: str | None = None
    approval_required: bool = False
    approval_status: str = "not_required"
    approver: Member | None = None
    approved_at: datetime | None = None
    recurrence_rule: str | None = None
    subtasks: list[TaskView] = field(default_factory=list)
    comments: list[CommentView] = field(default_factory=list)
    transitions: list[TransitionView] = field(default_factory=list)
    watchers: list[Member] = field(default_factory=list)
    capa_actions: list[CapaActionView] = field(default_factory=list)
    allowed_transitions: list[str] = field(default_factory=list)
    repeat: Repeat | None = None
    next_occurrence_at: datetime | None = None
    recurrence_parent_id: uuid.UUID | None = None
    recurrence_parent_code: str | None = None
    attachments: list[AttachmentView] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class TaskFilters:
    search: str | None = None
    kind: str | None = None
    statuses: tuple[str, ...] = ()
    priorities: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    assignee: str | None = None  # membership_id (str), "me", or "unassigned"
    sla_state: str | None = None
    source_type: str | None = None


@dataclass(frozen=True, slots=True)
class SlaAlert:
    """A task at or past its SLA horizon, and who is accountable for it — the
    unit the SLA sweep turns into notifications."""

    task_id: uuid.UUID
    code: str
    title: str
    breached: bool  # past the deadline (vs merely due soon)
    recipients: tuple[uuid.UUID, ...]  # owner + assignees, deduped


def _member_of(mid: uuid.UUID | None, names: dict[uuid.UUID, str]) -> Member | None:
    if mid is None:
        return None
    return Member(membership_id=mid, name=names.get(mid, "Unknown"))


def _title_of(filename: str) -> str:
    """A readable evidence title from a file's name: its stem, separators as spaces."""
    stem = PurePosixPath(sanitise_filename(filename)).stem
    return re.sub(r"[_\-\s]+", " ", stem).strip() or "Attachment"


def _renewal_description(title: str, lapsed_on: date, control_codes: Sequence[str]) -> str:
    text = (
        f"{title} passed its renewal date on {lapsed_on.day} {lapsed_on:%b} {lapsed_on.year}. "
        "Collect a fresh copy and upload it, or move the renewal date on the evidence if it "
        "is still valid, then close this task."
    )
    return f"{text}\n\nSupports: {', '.join(control_codes)}." if control_codes else text


# -- service -----------------------------------------------------------------


class TaskService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service

    # -- cross-module resolution (rule 4) ------------------------------------

    async def _member_names(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        from verity.modules.iam.service import iam_service  # noqa: PLC0415

        members = await iam_service.list_members(session, tenant_id=tenant_id)
        return {m.membership_id: m.full_name for m in members}

    async def _notify(  # noqa: PLR0913 — the event plus its recipients
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        task: Task,
        actor: Actor,
        kind: str,
        title: str,
        body: str = "",
        email: bool = False,
    ) -> None:
        """Fan a task event out to the people on it (owner, reporter, assignees),
        minus whoever caused it. Cross-module through the service, rule 4."""
        from verity.modules.notifications.service import notification_service  # noqa: PLC0415

        assignee_ids = (await self._assignees_by_task(session, tenant_id, [task.id])).get(
            task.id, []
        )
        recipients = {task.owner_membership_id, task.reporter_membership_id, *assignee_ids}
        recipients.discard(self._actor_membership(actor))
        await notification_service.notify_many(
            session,
            tenant_id=tenant_id,
            recipients=recipients,
            kind=kind,
            title=title,
            body=body,
            object_type="task",
            object_id=task.id,
            email=email,
        )

    # -- reads ---------------------------------------------------------------

    async def _load(self, session: AsyncSession, tenant_id: uuid.UUID, task_id: uuid.UUID) -> Task:
        # populate_existing forces a fresh row: a mutating method flushes an UPDATE
        # (expiring the server-computed updated_at) and then re-renders through here,
        # and async SQLAlchemy cannot lazily reload an expired column on attribute access.
        task = await session.get(Task, task_id, populate_existing=True)
        if task is None or task.tenant_id != tenant_id:
            raise NotFound(
                "This task no longer exists. It may have been deleted.",
                detail=f"task {task_id}",
            )
        return task

    async def _assignees_by_task(
        self, session: AsyncSession, tenant_id: uuid.UUID, task_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, list[uuid.UUID]]:
        if not task_ids:
            return {}
        rows = await session.execute(
            select(TaskAssignee.task_id, TaskAssignee.membership_id).where(
                TaskAssignee.tenant_id == tenant_id, TaskAssignee.task_id.in_(list(task_ids))
            )
        )
        out: dict[uuid.UUID, list[uuid.UUID]] = {}
        for task_id, mid in rows:
            out.setdefault(task_id, []).append(mid)
        return out

    async def _subtask_counts(
        self, session: AsyncSession, tenant_id: uuid.UUID, parent_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        if not parent_ids:
            return {}
        rows = await session.execute(
            select(Task.parent_task_id, func.count())
            .where(Task.tenant_id == tenant_id, Task.parent_task_id.in_(list(parent_ids)))
            .group_by(Task.parent_task_id)
        )
        return {pid: n for pid, n in rows if pid is not None}

    async def _comment_counts(
        self, session: AsyncSession, tenant_id: uuid.UUID, task_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        if not task_ids:
            return {}
        rows = await session.execute(
            select(TaskComment.task_id, func.count())
            .where(TaskComment.tenant_id == tenant_id, TaskComment.task_id.in_(list(task_ids)))
            .group_by(TaskComment.task_id)
        )
        # dict(rows) is rejected by mypy on a Result; the comprehension is the idiom.
        return {task_id: n for task_id, n in rows}  # noqa: C416

    @staticmethod
    def _repeat_of(rule: str | None) -> Repeat | None:
        """The structured repeat behind a stored rule, or None when there is none or it
        is outside what this module writes (a hand-edited or imported rule)."""
        if not rule:
            return None
        try:
            return parse_rrule(rule)
        except ValueError:
            return None

    def _recurrence_summary(self, rule: str | None) -> str | None:
        if not rule:
            return None
        # A human phrase for the badge; the RRULE is the source of truth.
        repeat = self._repeat_of(rule)
        return summary(repeat) if repeat else "Recurring"

    def _to_row(
        self,
        task: Task,
        names: dict[uuid.UUID, str],
        assignee_ids: list[uuid.UUID],
        counts: dict[str, int],
    ) -> TaskView:
        return TaskView(
            id=task.id,
            code=task.code,
            task_kind=task.task_kind,
            title=task.title,
            status=task.status,
            priority=task.priority,
            severity=task.severity,
            category=task.category,
            owner=_member_of(task.owner_membership_id, names),
            assignees=[Member(mid, names.get(mid, "Unknown")) for mid in assignee_ids],
            sla_level=task.sla_level,
            sla_due_at=task.sla_due_at,
            sla_state=sla_state(task.sla_due_at, task.status),
            detected_at=task.detected_at,
            due_at=task.due_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
            recurrence_summary=self._recurrence_summary(task.recurrence_rule),
            parent_task_id=task.parent_task_id,
            source=task.raised_from_type or "manual",
            subtask_count=counts.get("subtasks", 0),
            comment_count=counts.get("comments", 0),
            link_count=counts.get("links", 0),
            attachment_count=counts.get("attachments", 0),
        )

    async def list_tasks(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        filters: TaskFilters,
        page: int = 1,
        page_size: int = 25,
        caller_membership_id: uuid.UUID | None = None,
    ) -> tuple[list[TaskView], int]:
        stmt: Select[tuple[Task]] = select(Task).where(
            Task.tenant_id == tenant_id, Task.parent_task_id.is_(None)
        )
        if filters.kind and filters.kind != "all":
            stmt = stmt.where(Task.task_kind == filters.kind)
        if filters.statuses:
            stmt = stmt.where(Task.status.in_(list(filters.statuses)))
        if filters.priorities:
            stmt = stmt.where(Task.priority.in_(list(filters.priorities)))
        if filters.categories:
            stmt = stmt.where(Task.category.in_(list(filters.categories)))
        if filters.source_type:
            stmt = stmt.where(Task.raised_from_type == filters.source_type)
        if filters.search:
            like = f"%{filters.search.lower()}%"
            stmt = stmt.where(func.lower(Task.title).like(like) | func.lower(Task.code).like(like))

        tasks = list((await session.execute(stmt)).scalars())

        # Assignee filter needs the join set; resolve then filter in memory (the
        # register is a bounded page, not a report).
        assignees = await self._assignees_by_task(session, tenant_id, [t.id for t in tasks])
        if filters.assignee:
            target = filters.assignee

            def keep(t: Task) -> bool:
                ids = assignees.get(t.id, [])
                if target == "unassigned":
                    return not ids
                if target == "me":
                    return caller_membership_id in ids
                return any(str(m) == target for m in ids)

            tasks = [t for t in tasks if keep(t)]

        names = await self._member_names(session, tenant_id)
        subc = await self._subtask_counts(session, tenant_id, [t.id for t in tasks])
        comc = await self._comment_counts(session, tenant_id, [t.id for t in tasks])
        attc = await link_service.counts_into(
            session,
            tenant_id=tenant_id,
            to_type="task",
            to_ids=[t.id for t in tasks],
            from_type="evidence",
        )

        rows = [
            self._to_row(
                t,
                names,
                assignees.get(t.id, []),
                {
                    "subtasks": subc.get(t.id, 0),
                    "comments": comc.get(t.id, 0),
                    "attachments": attc.get(t.id, 0),
                },
            )
            for t in tasks
        ]
        rows.sort(key=self._attention_key)
        total = len(rows)
        start = (page - 1) * page_size
        return rows[start : start + page_size], total

    @staticmethod
    def _attention_key(row: TaskView) -> tuple[int, int, int, str]:
        active = 0 if row.status in _ACTIVE else 1
        sla_rank = {"breached": 0, "due_soon": 1, "paused": 2, "on_track": 3, "none": 4}[
            row.sla_state
        ]
        prio_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}[row.priority]
        return (active, sla_rank, prio_rank, row.created_at.isoformat())

    def _capa_view(
        self, a: IssueAction, names: dict[uuid.UUID, str], codes: dict[uuid.UUID, str]
    ) -> CapaActionView:
        return CapaActionView(
            id=a.id,
            action_type=a.action_type,
            title=a.title,
            description=a.description or "",
            owner=_member_of(a.owner_membership_id, names),
            due_at=a.due_at,
            status=a.status,
            completed_at=a.completed_at,
            verified_by=_member_of(a.verified_by_membership_id, names),
            verified_at=a.verified_at,
            auto_generated=a.auto_generated,
            promoted_task_code=codes.get(a.promoted_task_id) if a.promoted_task_id else None,
            created_at=a.created_at,
        )

    async def _capa_actions_for(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        task_id: uuid.UUID,
        names: dict[uuid.UUID, str],
    ) -> list[CapaActionView]:
        rows = list(
            (
                await session.execute(
                    select(IssueAction)
                    .where(IssueAction.tenant_id == tenant_id, IssueAction.task_id == task_id)
                    .order_by(IssueAction.created_at.asc())
                )
            ).scalars()
        )
        promoted_ids = [r.promoted_task_id for r in rows if r.promoted_task_id is not None]
        codes: dict[uuid.UUID, str] = {}
        if promoted_ids:
            code_rows = await session.execute(
                select(Task.id, Task.code).where(
                    Task.tenant_id == tenant_id, Task.id.in_(promoted_ids)
                )
            )
            codes = {tid: code for tid, code in code_rows}  # noqa: C416
        return [self._capa_view(r, names, codes) for r in rows]

    async def get_task(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, task_id: uuid.UUID
    ) -> TaskDetailView:
        task = await self._load(session, tenant_id, task_id)
        names = await self._member_names(session, tenant_id)

        assignees = (await self._assignees_by_task(session, tenant_id, [task.id])).get(task.id, [])
        sub_rows = list(
            (
                await session.execute(
                    select(Task).where(Task.tenant_id == tenant_id, Task.parent_task_id == task.id)
                )
            ).scalars()
        )
        comments = list(
            (
                await session.execute(
                    select(TaskComment)
                    .where(TaskComment.tenant_id == tenant_id, TaskComment.task_id == task.id)
                    .order_by(TaskComment.created_at.desc())
                )
            ).scalars()
        )
        transitions = list(
            (
                await session.execute(
                    select(TaskTransition)
                    .where(TaskTransition.tenant_id == tenant_id, TaskTransition.task_id == task.id)
                    .order_by(TaskTransition.occurred_at.desc(), TaskTransition.id.desc())
                )
            ).scalars()
        )
        watcher_ids = [
            mid
            for (mid,) in (
                await session.execute(
                    select(TaskWatcher.membership_id).where(
                        TaskWatcher.tenant_id == tenant_id, TaskWatcher.task_id == task.id
                    )
                )
            )
        ]
        attachments = await self._attachments_of(session, tenant_id, task.id, names, transitions)
        parent_code: str | None = None
        if task.recurrence_parent_id is not None:
            parent_code = (
                await session.execute(
                    select(Task.code).where(
                        Task.tenant_id == tenant_id, Task.id == task.recurrence_parent_id
                    )
                )
            ).scalar_one_or_none()

        base = self._to_row(
            task,
            names,
            assignees,
            {
                "subtasks": len(sub_rows),
                "comments": len(comments),
                "attachments": len(attachments),
            },
        )
        return TaskDetailView(
            **{f.name: getattr(base, f.name) for f in base.__dataclass_fields__.values()},
            description=task.description or "",
            impact=task.impact,
            urgency=task.urgency,
            severity_override=task.severity_override,
            severity_override_reason=task.severity_override_reason,
            reporter=_member_of(task.reporter_membership_id, names),
            started_at=task.started_at,
            resolved_at=task.resolved_at,
            closed_at=task.closed_at,
            closure_note=task.closure_note,
            cancelled_reason=task.cancelled_reason,
            approval_required=task.requires_approval,
            approval_status=task.approval_status,
            approver=_member_of(task.approved_by_membership_id, names),
            approved_at=task.approved_at,
            recurrence_rule=task.recurrence_rule,
            subtasks=[self._to_row(s, names, [], {}) for s in sub_rows],
            comments=[
                CommentView(
                    c.id,
                    names.get(c.author_membership_id) if c.author_membership_id else None,
                    c.body,
                    c.created_at,
                )
                for c in comments
            ],
            transitions=[
                TransitionView(
                    t.id,
                    names.get(t.actor_membership_id) if t.actor_membership_id else None,
                    t.field_changed,
                    t.old_value,
                    t.new_value,
                    t.note,
                    t.occurred_at,
                )
                for t in transitions
            ],
            watchers=[Member(mid, names.get(mid, "Unknown")) for mid in watcher_ids],
            capa_actions=await self._capa_actions_for(session, tenant_id, task.id, names),
            allowed_transitions=self._allowed_for(task),
            repeat=self._repeat_of(task.recurrence_rule),
            next_occurrence_at=task.next_occurrence_at,
            recurrence_parent_id=task.recurrence_parent_id,
            recurrence_parent_code=parent_code,
            attachments=attachments,
        )

    @staticmethod
    def _allowed_for(task: Task) -> list[str]:
        """The legal moves from here. Closing is withheld until a required approval has
        been given, so the client is never offered a move the service would refuse."""
        moves = list(ALLOWED_TRANSITIONS[task.status])
        if task.requires_approval and task.approval_status != "approved":
            moves = [m for m in moves if m != "closed"]
        return moves

    async def _attachments_of(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        task_id: uuid.UUID,
        names: dict[uuid.UUID, str],
        transitions: Sequence[TaskTransition],
    ) -> list[AttachmentView]:
        from verity.modules.evidence.service import evidence_service  # noqa: PLC0415

        briefs = await evidence_service.briefs_for_task(
            session, tenant_id=tenant_id, task_id=task_id
        )
        # Who attached an item, and when, is in the task's own history: the attach event
        # names the evidence in new_value and the status change it came with in old_value.
        # The history is newest first, so the first event seen for an item is its latest.
        events: dict[str, TaskTransition] = {}
        for t in transitions:
            if t.field_changed == "attachment" and t.new_value:
                events.setdefault(t.new_value, t)
        out: list[AttachmentView] = []
        for brief in briefs:
            event = events.get(str(brief.id))
            attached_by: str | None = None
            if event is not None:
                attached_by = (
                    names.get(event.actor_membership_id, "Unknown")
                    if event.actor_membership_id
                    else "System"
                )
            out.append(
                AttachmentView(
                    id=brief.id,
                    title=brief.title,
                    evidence_type=brief.evidence_type,
                    kind=brief.kind,
                    filename=brief.filename,
                    content_type=brief.content_type,
                    size_bytes=brief.size_bytes,
                    sha256=brief.sha256,
                    link_url=brief.link_url,
                    renewal_date=brief.renewal_date,
                    freshness=brief.freshness,
                    review_status=brief.review_status,
                    attached_by=attached_by,
                    attached_at=event.occurred_at if event else None,
                    transition_id=(
                        uuid.UUID(event.old_value) if event and event.old_value else None
                    ),
                )
            )
        return out

    # -- SLA / severity resolution -------------------------------------------

    async def _resolve_sla_due(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        sla_level: str | None,
        anchor: datetime | None,
    ) -> datetime | None:
        if not sla_level or anchor is None:
            return None
        row = (
            await session.execute(
                select(SlaDefinition.resolve_hours).where(
                    SlaDefinition.tenant_id == tenant_id, SlaDefinition.level == sla_level
                )
            )
        ).scalar_one_or_none()
        hours = row if row is not None else _DEFAULT_RESOLVE_HOURS.get(sla_level)
        if hours is None:
            return None
        return anchor + timedelta(hours=hours)

    async def _resolve_severity(
        self, session: AsyncSession, tenant_id: uuid.UUID, impact: str | None, urgency: str | None
    ) -> str | None:
        if impact is None or urgency is None:
            return None
        row = (
            await session.execute(
                select(TaskSeverityMatrixCell.severity).where(
                    TaskSeverityMatrixCell.tenant_id == tenant_id,
                    TaskSeverityMatrixCell.impact == impact,
                    TaskSeverityMatrixCell.urgency == urgency,
                )
            )
        ).scalar_one_or_none()
        if row is not None:
            return row
        default = _DEFAULT_MATRIX.get((impact, urgency))
        return default[0] if default else None

    def _check_severity_inputs(
        self, impact: str | None, urgency: str | None, severity: str | None
    ) -> None:
        if impact is not None and impact not in IMPACTS:
            raise InvalidInput(_IMPACT_ERROR, detail=f"unknown impact {impact!r}")
        if urgency is not None and urgency not in URGENCIES:
            raise InvalidInput(_URGENCY_ERROR, detail=f"unknown urgency {urgency!r}")
        if severity is not None and severity not in SEVERITIES:
            raise InvalidInput(_SEVERITY_ERROR, detail=f"unknown severity {severity!r}")

    async def _decide_severity(
        self, session: AsyncSession, tenant_id: uuid.UUID, wanted: SeverityInput
    ) -> SeverityDecision:
        """What severity a set of inputs ends up with, against this tenant's matrix."""
        self._check_severity_inputs(wanted.impact, wanted.urgency, wanted.severity)
        resolved = await self._resolve_severity(session, tenant_id, wanted.impact, wanted.urgency)
        return decide_severity(resolved=resolved, requested=wanted.severity, reason=wanted.reason)

    # -- code allocation -----------------------------------------------------

    async def _allocate_code(self, session: AsyncSession, tenant_id: uuid.UUID) -> str:
        # Numeric, not the string max: "TSK-9999" sorts after "TSK-10000", which would hand
        # out a taken code once a workspace passes ten thousand tasks, and a daily repeat
        # makes that a matter of years rather than never.
        highest = (
            await session.execute(
                select(
                    func.max(cast(func.substr(Task.code, len(_CODE_PREFIX) + 1), BigInteger))
                ).where(
                    Task.tenant_id == tenant_id, Task.code.regexp_match(f"^{_CODE_PREFIX}[0-9]+$")
                )
            )
        ).scalar_one_or_none()
        return f"{_CODE_PREFIX}{(highest or 0) + 1:04d}"

    async def _insert(
        self, session: AsyncSession, tenant_id: uuid.UUID, build: Callable[[str], Task]
    ) -> Task:
        """Allocate the next code and insert the task ``build`` makes with it.

        The code is max plus one, so two creates in one workspace can pick the same one;
        the unique constraint refuses the second, and it retries with a fresh code. Each
        attempt is a savepoint: a plain rollback would end the whole transaction, and with
        it the tenant setting every later statement in the request depends on.
        """
        for _ in range(5):
            task = build(await self._allocate_code(session, tenant_id))
            try:
                async with session.begin_nested():
                    session.add(task)
                    await session.flush([task])
            except IntegrityError:
                continue
            return task
        raise Conflict(_CODE_ERROR, detail="could not allocate a task code")

    # -- history + audit -----------------------------------------------------

    def _actor_membership(self, actor: Actor) -> uuid.UUID | None:
        # Only a Membership maps to a tenant member; a PlatformAdmin's id is not a
        # membership, and System has none. (An earlier version reached for a
        # non-existent ``membership_id`` attribute and so silently attributed
        # everything to no-one.)
        return actor.id if isinstance(actor, Membership) else None

    async def _transition_row(  # noqa: PLR0913, PLR0917
        self,
        session: AsyncSession,
        task: Task,
        actor: Actor,
        field_changed: str,
        old: str | None,
        new: str | None,
        note: str | None,
    ) -> uuid.UUID:
        row_id = uuid7()
        session.add(
            TaskTransition(
                id=row_id,
                tenant_id=task.tenant_id,
                task_id=task.id,
                actor_membership_id=self._actor_membership(actor),
                field_changed=field_changed,
                old_value=old,
                new_value=new,
                note=note,
                occurred_at=datetime.now(UTC),
            )
        )
        return row_id

    # -- writes --------------------------------------------------------------

    @staticmethod
    def _anchor(due_at: datetime | None, created_at: datetime) -> date:
        """The date a series is counted from: when its first task is due, or the day it was
        made when it has no due date."""
        return (due_at or created_at).astimezone(UTC).date()

    @staticmethod
    def _next_occurrence(anchor: date, repeat: Repeat | None, today: date) -> datetime | None:
        """When the next task in a series is due: the first occurrence after the anchor and
        no earlier than today, so a rule set on a task that was due last month does not
        raise last month's tasks as well."""
        if repeat is None:
            return None
        due = next_after(anchor, repeat, max(anchor, today - timedelta(days=1)))
        return datetime.combine(due, time.min, tzinfo=UTC) if due else None

    @staticmethod
    def _check_repeat(repeat: Repeat, anchor: date) -> None:
        if repeat.until is not None and repeat.until <= anchor:
            raise InvalidInput(
                _REPEAT_END_ERROR, detail=f"repeat ends {repeat.until}, not after {anchor}"
            )

    async def create_task(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        task_kind: str,
        title: str,
        description: str | None = None,
        priority: str = "medium",
        category: str = "operations",
        sla_level: str | None = None,
        owner_membership_id: uuid.UUID | None = None,
        assignee_ids: Sequence[uuid.UUID] = (),
        due_at: datetime | None = None,
        raised_from_type: str | None = None,
        severity_input: SeverityInput | None = None,
        repeat: Repeat | None = None,
        requires_approval: bool = False,
    ) -> TaskDetailView:
        decision = await self._decide_severity(
            session, tenant_id, severity_input or SeverityInput()
        )
        task = await self._create(
            session,
            tenant_id=tenant_id,
            actor=actor,
            task_kind=task_kind,
            title=title,
            description=description,
            priority=priority,
            category=category,
            sla_level=sla_level,
            owner_membership_id=owner_membership_id,
            assignee_ids=assignee_ids,
            due_at=due_at,
            raised_from_type=raised_from_type,
            impact=severity_input.impact if severity_input else None,
            urgency=severity_input.urgency if severity_input else None,
            decision=decision,
            repeat=repeat,
            requires_approval=requires_approval,
        )
        await session.flush()
        return await self.get_task(session, tenant_id=tenant_id, task_id=task.id)

    async def _create(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        task_kind: str,
        title: str,
        description: str | None,
        priority: str,
        category: str,
        sla_level: str | None,
        owner_membership_id: uuid.UUID | None,
        assignee_ids: Sequence[uuid.UUID],
        due_at: datetime | None,
        raised_from_type: str | None,
        impact: str | None = None,
        urgency: str | None = None,
        decision: SeverityDecision | None = None,
        repeat: Repeat | None = None,
        requires_approval: bool = False,
        recurrence_parent_id: uuid.UUID | None = None,
        source: str | None = None,
        external_id: str | None = None,
        audit_extra: dict[str, object] | None = None,
    ) -> Task:
        """Insert a task with its assignees, history and audit rows, and return the row.

        The one place a task is made, whoever asks: a person through ``create_task``, the
        recurrence job for the next occurrence of a series, the evidence job for a
        renewal. ``source`` and ``external_id`` are the key a job raises its work under
        (rule 9), refused by the database when the same work is raised twice.
        """
        if task_kind not in TASK_KINDS:
            raise InvalidInput(
                "Choose whether this is a task or an issue, then try again.",
                detail=f"unknown task kind {task_kind!r}",
            )
        if priority not in PRIORITIES:
            raise InvalidInput(_PRIORITY_ERROR, detail=f"unknown priority {priority!r}")
        if category not in CATEGORIES:
            raise InvalidInput(_CATEGORY_ERROR, detail=f"unknown category {category!r}")

        member = self._actor_membership(actor)
        now = datetime.now(UTC)
        decided = decision or SeverityDecision(severity=None)
        anchor = self._anchor(due_at, now)
        if repeat is not None:
            self._check_repeat(repeat, anchor)
        sla_due_at = await self._resolve_sla_due(session, tenant_id, sla_level, now)

        def build(code: str) -> Task:
            task = Task(
                id=uuid7(),
                tenant_id=tenant_id,
                code=code,
                task_kind=task_kind,
                title=title.strip(),
                description=(description or None),
                priority=priority,
                category=category,
                status="open",
                impact=impact,
                urgency=urgency,
                severity=decided.severity,
                severity_override=decided.override,
                severity_override_reason=decided.override_reason,
                sla_level=sla_level,
                sla_due_at=sla_due_at,
                owner_membership_id=owner_membership_id,
                reporter_membership_id=member,
                created_by_membership_id=member,
                due_at=due_at,
                raised_from_type=raised_from_type,
                recurrence_rule=to_rrule(repeat) if repeat else None,
                recurrence_parent_id=recurrence_parent_id,
                next_occurrence_at=self._next_occurrence(anchor, repeat, now.date()),
                requires_approval=requires_approval,
                approval_status="pending" if requires_approval else "not_required",
            )
            if source is not None:
                task.source, task.external_id, task.synced_at = source, external_id, now
            return task

        task = await self._insert(session, tenant_id, build)

        for mid in dict.fromkeys(assignee_ids):
            session.add(
                TaskAssignee(id=uuid7(), tenant_id=tenant_id, task_id=task.id, membership_id=mid)
            )

        await self._transition_row(session, task, actor, "created", None, task.code, None)
        after: dict[str, object] = {"code": task.code, "title": task.title, "kind": task_kind}
        if decided.severity is not None:
            after["severity"] = decided.severity
        if repeat is not None:
            after["repeat"] = summary(repeat)
        await self._audit.record(
            session,
            action="create",
            object_type="task",
            object_id=task.id,
            actor=actor,
            tenant_id=tenant_id,
            after={**after, **(audit_extra or {})},
        )
        # An issue raised from an event gets one corrective action to work from.
        if task_kind == "issue" and raised_from_type is not None:
            await self.ensure_initial_capa(session, tenant_id=tenant_id, actor=actor, task=task)
        return task

    # -- CAPA actions (issues only) ------------------------------------------

    async def _load_issue(
        self, session: AsyncSession, tenant_id: uuid.UUID, task_id: uuid.UUID
    ) -> Task:
        task = await self._load(session, tenant_id, task_id)
        if task.task_kind != "issue":
            raise InvalidInput(
                "Corrective and preventive actions can only be added to an issue, not a task.",
                detail="CAPA actions exist only on issues",
            )
        return task

    async def _load_action(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        task_id: uuid.UUID,
        action_id: uuid.UUID,
    ) -> IssueAction:
        action = await session.get(IssueAction, action_id, populate_existing=True)
        if action is None or action.tenant_id != tenant_id or action.task_id != task_id:
            raise NotFound(
                "This action no longer exists. It may have been deleted.",
                detail=f"issue action {action_id}",
            )
        return action

    async def ensure_initial_capa(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor, task: Task
    ) -> None:
        """Create one corrective action for an issue, inheriting its owner and due
        date. Idempotent: does nothing if the issue already has any action."""
        existing = (
            await session.execute(
                select(func.count())
                .select_from(IssueAction)
                .where(IssueAction.tenant_id == tenant_id, IssueAction.task_id == task.id)
            )
        ).scalar_one()
        if existing:
            return
        action = IssueAction(
            id=uuid7(),
            tenant_id=tenant_id,
            task_id=task.id,
            action_type="corrective",
            title=f"Investigate and remediate: {task.title}",
            owner_membership_id=task.owner_membership_id,
            due_at=task.due_at,
            status="planned",
            auto_generated=True,
        )
        session.add(action)
        await self._audit.record(
            session,
            action="create",
            object_type="issue_action",
            object_id=action.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"task_id": str(task.id), "auto": True, "type": "corrective"},
        )

    async def add_capa_action(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        task_id: uuid.UUID,
        title: str,
        action_type: str = "corrective",
        description: str | None = None,
        owner_membership_id: uuid.UUID | None = None,
        due_at: datetime | None = None,
    ) -> TaskDetailView:
        await self._load_issue(session, tenant_id, task_id)
        if action_type not in CAPA_TYPES:
            raise InvalidInput(_ACTION_TYPE_ERROR, detail=f"unknown action type {action_type!r}")
        if not title.strip():
            raise InvalidInput(_ACTION_TITLE_ERROR, detail="an action needs a title")
        action = IssueAction(
            id=uuid7(),
            tenant_id=tenant_id,
            task_id=task_id,
            action_type=action_type,
            title=title.strip(),
            description=(description or None),
            owner_membership_id=owner_membership_id,
            due_at=due_at,
            status="planned",
        )
        session.add(action)
        await self._audit.record(
            session,
            action="create",
            object_type="issue_action",
            object_id=action.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"task_id": str(task_id), "type": action_type, "title": action.title},
        )
        await session.flush()
        return await self.get_task(session, tenant_id=tenant_id, task_id=task_id)

    async def update_capa_action(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        task_id: uuid.UUID,
        action_id: uuid.UUID,
        action_type: str | None = None,
        title: str | None = None,
        description: str | None = None,
        owner_membership_id: uuid.UUID | None = None,
        clear_owner: bool = False,
        due_at: datetime | None = None,
    ) -> TaskDetailView:
        await self._load_issue(session, tenant_id, task_id)
        action = await self._load_action(session, tenant_id, task_id, action_id)
        before = {"title": action.title, "type": action.action_type}
        if action_type is not None:
            if action_type not in CAPA_TYPES:
                raise InvalidInput(
                    _ACTION_TYPE_ERROR, detail=f"unknown action type {action_type!r}"
                )
            action.action_type = action_type
        if title is not None:
            if not title.strip():
                raise InvalidInput(_ACTION_TITLE_ERROR, detail="an action needs a title")
            action.title = title.strip()
        if description is not None:
            action.description = description or None
        if clear_owner:
            action.owner_membership_id = None
        elif owner_membership_id is not None:
            action.owner_membership_id = owner_membership_id
        if due_at is not None:
            action.due_at = due_at
        await self._audit.record(
            session,
            action="update",
            object_type="issue_action",
            object_id=action.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after={"title": action.title, "type": action.action_type},
        )
        await session.flush()
        return await self.get_task(session, tenant_id=tenant_id, task_id=task_id)

    async def transition_capa_action(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        task_id: uuid.UUID,
        action_id: uuid.UUID,
        to_status: str,
    ) -> TaskDetailView:
        await self._load_issue(session, tenant_id, task_id)
        action = await self._load_action(session, tenant_id, task_id, action_id)
        if to_status not in CAPA_STATUSES:
            raise InvalidInput(
                "Pick a status from the list shown on the action.",
                detail=f"unknown action status {to_status!r}",
            )
        if to_status not in _CAPA_TRANSITIONS[action.status]:
            raise Conflict(
                "This action cannot move to that status from where it is now. "
                "Reload the page to see the moves available.",
                detail=f"cannot move a {action.status} action to {to_status}",
            )
        old = action.status
        now = datetime.now(UTC)
        action.status = to_status
        if to_status == "completed":
            action.completed_at = now
        elif to_status == "verified":
            action.verified_by_membership_id = self._actor_membership(actor)
            action.verified_at = now
        elif to_status in ("in_progress", "planned"):
            # Reopening clears the completion/verification stamps so they can't go stale.
            action.completed_at = None
            action.verified_by_membership_id = None
            action.verified_at = None
        await self._audit.record(
            session,
            action="transition",
            object_type="issue_action",
            object_id=action.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"status": old},
            after={"status": to_status},
        )
        await session.flush()
        return await self.get_task(session, tenant_id=tenant_id, task_id=task_id)

    async def promote_capa_to_task(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        task_id: uuid.UUID,
        action_id: uuid.UUID,
    ) -> TaskDetailView:
        issue = await self._load_issue(session, tenant_id, task_id)
        action = await self._load_action(session, tenant_id, task_id, action_id)
        if action.promoted_task_id is not None:
            return await self.get_task(session, tenant_id=tenant_id, task_id=task_id)  # idempotent
        member = self._actor_membership(actor)
        note = f"Promoted from {issue.code} · {issue.title}"
        body = f"{action.description}\n\n{note}" if action.description else note
        new_task = await self._insert(
            session,
            tenant_id,
            lambda code: Task(
                id=uuid7(),
                tenant_id=tenant_id,
                code=code,
                task_kind="task",
                title=action.title,
                description=body,
                priority=issue.priority,
                category=issue.category,
                status="open",
                owner_membership_id=action.owner_membership_id,
                reporter_membership_id=member,
                created_by_membership_id=member,
                due_at=action.due_at,
                raised_from_type="capa",
            ),
        )
        if action.owner_membership_id is not None:
            session.add(
                TaskAssignee(
                    id=uuid7(),
                    tenant_id=tenant_id,
                    task_id=new_task.id,
                    membership_id=action.owner_membership_id,
                )
            )
        await self._transition_row(session, new_task, actor, "created", None, new_task.code, None)
        action.promoted_task_id = new_task.id
        await self._audit.record(
            session,
            action="create",
            object_type="task",
            object_id=new_task.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"code": new_task.code, "promoted_from_action": str(action.id)},
        )
        await session.flush()
        return await self.get_task(session, tenant_id=tenant_id, task_id=task_id)

    # -- automations (curated catalogue + tenant overrides) ------------------

    def _merge_automation(
        self, default: dict[str, Any], row: TaskAutomation | None
    ) -> dict[str, Any]:
        merged = dict(default)
        if row is not None:
            merged["enabled"] = row.enabled and bool(default["available"])
            merged["creates"] = row.creates
            merged["owner_rule"] = row.owner_rule
            merged["priority"] = row.priority
            merged["due_in_days"] = row.due_in_days
        return merged

    async def list_automations(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        rows = (
            await session.execute(
                select(TaskAutomation).where(TaskAutomation.tenant_id == tenant_id)
            )
        ).scalars()
        overrides = {r.automation_key: r for r in rows}
        return [
            self._merge_automation(d, overrides.get(str(d["id"]))) for d in _AUTOMATION_CATALOGUE
        ]

    async def update_automation(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        automation_key: str,
        patch: dict[str, Any],
    ) -> dict[str, Any]:
        default = next((d for d in _AUTOMATION_CATALOGUE if d["id"] == automation_key), None)
        if default is None:
            raise NotFound(
                "This automation is no longer available. Reload the page to see the current list.",
                detail=f"automation {automation_key}",
            )
        if patch.get("enabled") and not default["available"]:
            raise Conflict(
                "This automation is not ready yet, so it cannot be turned on. "
                "It will become available once the module it watches is live.",
                detail="this automation's module is not available yet",
            )
        creates = patch.get("creates")
        if creates is not None and creates not in TASK_KINDS:
            raise InvalidInput(
                "Choose whether this automation should raise a task or an issue.",
                detail=f"unknown kind {creates!r}",
            )
        owner_rule = patch.get("owner_rule")
        if owner_rule is not None and owner_rule not in AUTOMATION_OWNER_RULES:
            raise InvalidInput(
                "Choose who should own what this automation raises, "
                "either the source owner or nobody.",
                detail=f"unknown owner rule {owner_rule!r}",
            )
        priority = patch.get("priority")
        if priority is not None and priority not in PRIORITIES:
            raise InvalidInput(_PRIORITY_ERROR, detail=f"unknown priority {priority!r}")

        row = (
            await session.execute(
                select(TaskAutomation).where(
                    TaskAutomation.tenant_id == tenant_id,
                    TaskAutomation.automation_key == automation_key,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            row = TaskAutomation(
                id=uuid7(),
                tenant_id=tenant_id,
                automation_key=automation_key,
                enabled=bool(default["enabled"]),
                creates=str(default["creates"]),
                owner_rule=str(default["owner_rule"]),
                priority=str(default["priority"]),
                due_in_days=int(default["due_in_days"]),
            )
            session.add(row)
        for key in _AUTOMATION_CUSTOMISABLE:
            if patch.get(key) is not None:
                setattr(row, key, patch[key])
        await self._audit.record(
            session,
            action="update",
            object_type="task_automation",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"key": automation_key, "enabled": row.enabled},
        )
        await session.flush()
        return self._merge_automation(default, row)

    async def update_task(  # noqa: PLR0913, PLR0912, PLR0915
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        task_id: uuid.UUID,
        title: str | None = None,
        description: str | None = None,
        priority: str | None = None,
        category: str | None = None,
        sla_level: str | None = None,
        owner_membership_id: uuid.UUID | None = None,
        clear_owner: bool = False,
        due_at: datetime | None = None,
        severity_input: SeverityInput | None = None,
        repeat: Repeat | None = None,
        clear_repeat: bool = False,
        requires_approval: bool | None = None,
    ) -> TaskDetailView:
        task = await self._load(session, tenant_id, task_id)
        # (field, old, new, note): the note is how an override says why.
        changed: list[tuple[str, str | None, str | None, str | None]] = []
        reschedule = False

        if title is not None and title.strip() != task.title:
            changed.append(("title", task.title, title.strip(), None))
            task.title = title.strip()
        if description is not None:
            task.description = description.strip() or None
        if priority is not None and priority != task.priority:
            if priority not in PRIORITIES:
                raise InvalidInput(_PRIORITY_ERROR, detail=f"unknown priority {priority!r}")
            changed.append(("priority", task.priority, priority, None))
            task.priority = priority
        if category is not None and category != task.category:
            if category not in CATEGORIES:
                raise InvalidInput(_CATEGORY_ERROR, detail=f"unknown category {category!r}")
            changed.append(("category", task.category, category, None))
            task.category = category
        if sla_level is not None and sla_level != task.sla_level:
            task.sla_level = sla_level or None
            task.sla_due_at = await self._resolve_sla_due(
                session, tenant_id, task.sla_level, task.detected_at or task.created_at
            )
        if clear_owner:
            task.owner_membership_id = None
        elif owner_membership_id is not None and owner_membership_id != task.owner_membership_id:
            changed.append(("owner", str(task.owner_membership_id), str(owner_membership_id), None))
            task.owner_membership_id = owner_membership_id
        if due_at is not None and due_at != task.due_at:
            changed.append(
                ("due", task.due_at.isoformat() if task.due_at else None, due_at.isoformat(), None)
            )
            task.due_at = due_at
            reschedule = True

        if severity_input is not None:
            decision = await self._decide_severity(session, tenant_id, severity_input)
            was_override = (task.severity_override, task.severity_override_reason)
            severity_moved = False
            for fld, new in (
                ("impact", severity_input.impact),
                ("urgency", severity_input.urgency),
                ("severity", decision.severity),
            ):
                old = getattr(task, fld)
                if old != new:
                    changed.append(
                        (fld, old, new, decision.override_reason if fld == "severity" else None)
                    )
                    setattr(task, fld, new)
                    severity_moved = fld == "severity" or severity_moved
            task.severity_override = decision.override
            task.severity_override_reason = decision.override_reason
            if not severity_moved and was_override != (decision.override, decision.override_reason):
                changed.append(
                    (
                        "severity_override",
                        was_override[0],
                        decision.override,
                        decision.override_reason,
                    )
                )

        if clear_repeat and repeat is not None:
            raise InvalidInput(
                "Choose a repeat or clear it, not both.", detail="repeat and clear_repeat together"
            )
        if clear_repeat or repeat is not None:
            if task.recurrence_parent_id is not None:
                raise InvalidInput(_REPEAT_NOT_HEAD_ERROR, detail="task is an occurrence")
            if task.parent_task_id is not None:
                raise InvalidInput(_REPEAT_ON_SUBTASK_ERROR, detail="task is a sub-task")
            new_rule = to_rrule(repeat) if repeat is not None else None
            if new_rule != task.recurrence_rule:
                changed.append(
                    (
                        "repeat",
                        self._recurrence_summary(task.recurrence_rule),
                        summary(repeat) if repeat is not None else None,
                        None,
                    )
                )
                task.recurrence_rule = new_rule
                reschedule = True

        if requires_approval is not None and requires_approval != task.requires_approval:
            changed.append(
                (
                    "approval_required",
                    str(task.requires_approval).lower(),
                    str(requires_approval).lower(),
                    None,
                )
            )
            task.requires_approval = requires_approval
            task.approval_status = "pending" if requires_approval else "not_required"
            task.approved_by_membership_id = None
            task.approved_at = None

        if reschedule:
            if (rule := self._repeat_of(task.recurrence_rule)) is not None:
                self._check_repeat(rule, self._anchor(task.due_at, task.created_at))
            self._reschedule(task)

        for fld, old, new, note in changed:
            await self._transition_row(session, task, actor, fld, old, new, note)
        if changed:
            await self._audit.record(
                session,
                action="update",
                object_type="task",
                object_id=task.id,
                actor=actor,
                tenant_id=tenant_id,
                before={fld: old for fld, old, _new, _note in changed},
                after={fld: new for fld, _old, new, _note in changed},
            )
        await session.flush()
        return await self.get_task(session, tenant_id=tenant_id, task_id=task.id)

    def _reschedule(self, task: Task) -> None:
        """Work out again when a series head next repeats, from its rule, its due date and
        its status. A cancelled head ends its series, so it has no next occurrence; one
        that is reinstated picks the series up from today and does not raise the tasks it
        missed while it was cancelled."""
        repeat = self._repeat_of(task.recurrence_rule)
        if repeat is None or task.status == "cancelled":
            task.next_occurrence_at = None
            return
        anchor = self._anchor(task.due_at, task.created_at)
        task.next_occurrence_at = self._next_occurrence(anchor, repeat, datetime.now(UTC).date())

    async def transition(  # noqa: PLR0913, PLR0912
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        task_id: uuid.UUID,
        to_status: str,
        note: str | None = None,
        evidence_ids: Sequence[uuid.UUID] = (),
        uploads: Sequence[Upload] = (),
    ) -> TaskDetailView:
        task = await self._load(session, tenant_id, task_id)
        if to_status not in TASK_STATUSES:
            raise InvalidInput(
                "Pick a status from the list shown on the task.",
                detail=f"unknown status {to_status!r}",
            )
        if to_status not in ALLOWED_TRANSITIONS[task.status]:
            raise Conflict(
                "This task cannot move to that status from where it is now. "
                "Reload the page to see the moves available.",
                detail=f"cannot move a {task.status} task to {to_status}",
            )
        if to_status in ("closed", "cancelled") and not note:
            raise InvalidInput(
                "Add a note explaining why, then close or cancel this task.",
                detail="a note is required to close or cancel a task",
            )
        if to_status == "closed" and task.requires_approval and task.approval_status != "approved":
            raise Conflict(_APPROVAL_TO_CLOSE_ERROR, detail=f"approval is {task.approval_status}")

        now = datetime.now(UTC)
        old = task.status
        task.status = to_status
        if to_status == "in_progress" and task.started_at is None:
            task.started_at = now
        elif to_status == "blocked":
            task.sla_paused_at = now
        elif old == "blocked" and task.sla_paused_at is not None:
            # Resuming: bank the paused span and push the deadline out by it.
            paused_ms = int((now - task.sla_paused_at).total_seconds() * 1000)
            task.sla_paused_ms += paused_ms
            if task.sla_due_at is not None:
                task.sla_due_at += timedelta(milliseconds=paused_ms)
            task.sla_paused_at = None
        if to_status == "under_review":
            task.resolved_at = now
            if task.requires_approval:
                # Sending it for review is what asks for the decision, every time: a task
                # that was approved or turned back and is sent again needs a fresh one.
                task.approval_status = "pending"
                task.approved_by_membership_id = None
                task.approved_at = None
        elif to_status == "closed":
            task.closed_at = now
            task.closure_note = note
        elif to_status == "cancelled":
            task.cancelled_reason = note
        if task.recurrence_rule is not None and "cancelled" in (old, to_status):
            self._reschedule(task)

        status_row = await self._transition_row(
            session, task, actor, "status", old, to_status, note
        )
        await self._attach(
            session,
            tenant_id=tenant_id,
            actor=actor,
            task=task,
            evidence_ids=evidence_ids,
            uploads=uploads,
            status_row=status_row,
        )
        await self._audit.record(
            session,
            action="transition",
            object_type="task",
            object_id=task.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"status": old},
            after={"status": to_status},
        )
        await self._notify(
            session,
            tenant_id=tenant_id,
            task=task,
            actor=actor,
            kind="status",
            title=f"{task.code} moved to {to_status.replace('_', ' ')}",
            body=task.title,
        )
        await session.flush()
        return await self.get_task(session, tenant_id=tenant_id, task_id=task.id)

    # -- evidence on a task --------------------------------------------------

    async def attach(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        task_id: uuid.UUID,
        evidence_ids: Sequence[uuid.UUID] = (),
        uploads: Sequence[Upload] = (),
    ) -> TaskDetailView:
        """Attach evidence to a task on its own, outside any status change: items already
        in the library by id, and files as new evidence. Add only: nothing here removes an
        attachment, so what a task was shown stays on its record."""
        task = await self._load(session, tenant_id, task_id)
        if not evidence_ids and not uploads:
            raise InvalidInput(
                "Choose an evidence item or a file to attach.",
                detail="nothing to attach",
            )
        await self._attach(
            session,
            tenant_id=tenant_id,
            actor=actor,
            task=task,
            evidence_ids=evidence_ids,
            uploads=uploads,
        )
        await session.flush()
        return await self.get_task(session, tenant_id=tenant_id, task_id=task.id)

    async def _attach(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        task: Task,
        evidence_ids: Sequence[uuid.UUID],
        uploads: Sequence[Upload],
        status_row: uuid.UUID | None = None,
    ) -> list[uuid.UUID]:
        """The shared half of ``attach`` and ``transition``. A file becomes an evidence
        item through the evidence service (which stores, hashes and sniffs it) mapped to
        the controls this task is linked to; every item is then linked to the task and
        written to its history, naming the status change it came with when there is one.
        Returns the evidence newly attached: one already on the task is left as it is."""
        if len(uploads) > _MAX_UPLOADS or len(set(evidence_ids)) > _MAX_PICKED_EVIDENCE:
            raise InvalidInput(_ATTACH_LIMIT_ERROR, detail="too many attachments in one request")
        if not evidence_ids and not uploads:
            return []
        from verity.modules.evidence.service import evidence_service  # noqa: PLC0415

        on_task = {
            b.id
            for b in await evidence_service.briefs_for_task(
                session, tenant_id=tenant_id, task_id=task.id
            )
        }
        fresh = [e for e in dict.fromkeys(evidence_ids) if e not in on_task]
        if uploads:
            controls = await self._linked_control_ids(session, tenant_id, task.id)
            today = datetime.now(UTC).date()
            for upload in uploads:
                created = await evidence_service.add_file(
                    session,
                    tenant_id=tenant_id,
                    actor=actor,
                    title=_title_of(upload.filename),
                    filename=upload.filename,
                    data=upload.data,
                    evidence_type="other",
                    collected_at=today,
                    owner_membership_id=self._actor_membership(actor),
                    control_ids=controls,
                )
                fresh.append(created.id)
        for evidence_id in fresh:
            await evidence_service.link_to_task(
                session,
                tenant_id=tenant_id,
                actor=actor,
                evidence_id=evidence_id,
                task_id=task.id,
            )
            await self._transition_row(
                session,
                task,
                actor,
                "attachment",
                str(status_row) if status_row else None,
                str(evidence_id),
                None,
            )
        if fresh:
            await self._audit.record(
                session,
                action="update",
                object_type="task",
                object_id=task.id,
                actor=actor,
                tenant_id=tenant_id,
                after={"attached_evidence": [str(e) for e in fresh]},
            )
        return fresh

    async def _linked_control_ids(
        self, session: AsyncSession, tenant_id: uuid.UUID, task_id: uuid.UUID
    ) -> list[uuid.UUID]:
        edges = await link_service.for_object(
            session, tenant_id=tenant_id, obj_type="task", obj_id=task_id
        )
        return list(dict.fromkeys(e.other_id for e in edges if e.other_type == "control"))

    async def download_attachment(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        task_id: uuid.UUID,
        evidence_id: uuid.UUID,
    ) -> tuple[bytes, str, str]:
        """The bytes, filename and content type of a file attached to this task. Only what
        is attached to it: the task's id does not open the rest of the evidence library."""
        from verity.modules.evidence.service import evidence_service  # noqa: PLC0415

        await self._load(session, tenant_id, task_id)
        on_task = {
            b.id
            for b in await evidence_service.briefs_for_task(
                session, tenant_id=tenant_id, task_id=task_id
            )
        }
        if evidence_id not in on_task:
            raise NotFound(
                "That file is not attached to this task.",
                detail=f"evidence {evidence_id} is not on task {task_id}",
            )
        return await evidence_service.download(
            session, tenant_id=tenant_id, evidence_id=evidence_id
        )

    async def set_assignees(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        task_id: uuid.UUID,
        membership_ids: Sequence[uuid.UUID],
    ) -> TaskDetailView:
        task = await self._load(session, tenant_id, task_id)
        current = set(
            (await self._assignees_by_task(session, tenant_id, [task.id])).get(task.id, [])
        )
        target = dict.fromkeys(membership_ids)
        if set(target) == current:
            return await self.get_task(session, tenant_id=tenant_id, task_id=task.id)
        await session.execute(
            delete(TaskAssignee).where(
                TaskAssignee.tenant_id == tenant_id, TaskAssignee.task_id == task.id
            )
        )
        for mid in target:
            session.add(
                TaskAssignee(id=uuid7(), tenant_id=tenant_id, task_id=task.id, membership_id=mid)
            )
        await self._transition_row(
            session, task, actor, "assignees", str(len(current)), str(len(target)), None
        )
        await self._audit.record(
            session,
            action="update",
            object_type="task",
            object_id=task.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"assignees": [str(m) for m in target]},
        )
        # Tell the newly-assigned they picked up work — not the whole task, and
        # not whoever did the assigning.
        added = [m for m in target if m not in current and m != self._actor_membership(actor)]
        if added:
            from verity.modules.notifications.service import (  # noqa: PLC0415
                notification_service,
            )

            await notification_service.notify_many(
                session,
                tenant_id=tenant_id,
                recipients=added,
                kind="assigned",
                title=f"You were assigned {task.code}",
                body=task.title,
                object_type="task",
                object_id=task.id,
                email=True,
            )
        await session.flush()
        return await self.get_task(session, tenant_id=tenant_id, task_id=task.id)

    async def add_comment(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        task_id: uuid.UUID,
        body: str,
    ) -> TaskDetailView:
        task = await self._load(session, tenant_id, task_id)
        if not body.strip():
            raise InvalidInput(
                "Write something before posting your comment.",
                detail="a comment cannot be empty",
            )
        session.add(
            TaskComment(
                id=uuid7(),
                tenant_id=tenant_id,
                task_id=task.id,
                author_membership_id=self._actor_membership(actor),
                body=body.strip(),
            )
        )
        await self._notify(
            session,
            tenant_id=tenant_id,
            task=task,
            actor=actor,
            kind="comment",
            title=f"New comment on {task.code}",
            body=body.strip()[:200],
        )
        await session.flush()
        return await self.get_task(session, tenant_id=tenant_id, task_id=task.id)

    async def add_subtask(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        parent_id: uuid.UUID,
        title: str,
    ) -> TaskDetailView:
        parent = await self._load(session, tenant_id, parent_id)
        if parent.parent_task_id is not None:
            raise InvalidInput(
                "This is already a sub-task, so it cannot have sub-tasks of its own. "
                "Add it to the parent task instead.",
                detail="sub-tasks are one level deep",
            )
        member = self._actor_membership(actor)
        child = await self._insert(
            session,
            tenant_id,
            lambda code: Task(
                id=uuid7(),
                tenant_id=tenant_id,
                code=code,
                task_kind=parent.task_kind,
                title=title.strip(),
                priority=parent.priority,
                category=parent.category,
                status="open",
                parent_task_id=parent.id,
                reporter_membership_id=member,
                created_by_membership_id=member,
            ),
        )
        await self._transition_row(session, child, actor, "created", None, child.code, None)
        await session.flush()
        return await self.get_task(session, tenant_id=tenant_id, task_id=parent.id)

    async def decide_approval(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        task_id: uuid.UUID,
        decision: str,
        note: str | None = None,
    ) -> TaskDetailView:
        task = await self._load(session, tenant_id, task_id)
        if decision not in ("approved", "rejected"):
            raise InvalidInput(
                "Choose either approve or reject to record your decision.",
                detail="decision must be approved or rejected",
            )
        if not task.requires_approval or task.approval_status != "pending":
            raise Conflict(
                "This task is not waiting for approval. "
                "Someone may have already decided it, so reload the page to see where it stands.",
                detail="this task is not awaiting approval",
            )
        if task.status != "under_review":
            raise Conflict(
                _APPROVAL_NOT_IN_REVIEW_ERROR,
                detail=f"approval decided on a {task.status} task",
            )
        task.approval_status = decision
        task.approved_by_membership_id = self._actor_membership(actor)
        task.approved_at = datetime.now(UTC)
        await self._transition_row(session, task, actor, "approval", "pending", decision, note)
        await self._audit.record(
            session,
            action="transition",
            object_type="task",
            object_id=task.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"approval": "pending"},
            after={"approval": decision},
        )
        await self._notify(
            session,
            tenant_id=tenant_id,
            task=task,
            actor=actor,
            kind="approval",
            title=f"{task.code} was {decision}",
            body=note or task.title,
            email=True,
        )
        await session.flush()
        return await self.get_task(session, tenant_id=tenant_id, task_id=task.id)

    # -- jobs ----------------------------------------------------------------

    async def sla_watchlist(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> list[SlaAlert]:
        """Active tasks that are breached or due within the same 2-day window
        ``sla_state`` uses. ``blocked`` (paused), ``closed`` and ``cancelled``
        never count. Read-only — turning these into notices is the job's call,
        so the sweep can dedupe with ``notify_once`` and stay idempotent."""
        now = datetime.now(UTC)
        horizon = now + timedelta(days=2)
        tasks = list(
            (
                await session.execute(
                    select(Task).where(
                        Task.tenant_id == tenant_id,
                        Task.status.in_(("open", "in_progress", "under_review")),
                        Task.sla_due_at.is_not(None),
                        Task.sla_due_at <= horizon,
                    )
                )
            ).scalars()
        )
        if not tasks:
            return []
        assignees = await self._assignees_by_task(session, tenant_id, [t.id for t in tasks])
        alerts: list[SlaAlert] = []
        for t in tasks:
            recipients = tuple(
                dict.fromkeys(
                    m for m in (t.owner_membership_id, *assignees.get(t.id, [])) if m is not None
                )
            )
            assert t.sla_due_at is not None  # noqa: S101 — filtered above
            alerts.append(
                SlaAlert(
                    task_id=t.id,
                    code=t.code,
                    title=t.title,
                    breached=t.sla_due_at <= now,
                    recipients=recipients,
                )
            )
        return alerts

    async def spawn_due_occurrences(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, now: datetime | None = None
    ) -> int:
        """Raise the next task of every series whose date has come, as the system.

        A series is its first task, the head, which alone carries the rule; each
        occurrence is a fresh task pointing back at it. Idempotent three ways: the head's
        ``next_occurrence_at`` moves on in the same transaction, a head another run holds
        is skipped, and the database refuses a second task for the same head and date.
        Returns how many tasks it made.
        """
        now = now or datetime.now(UTC)
        heads = list(
            (
                await session.execute(
                    select(Task)
                    .where(
                        Task.tenant_id == tenant_id,
                        Task.recurrence_rule.is_not(None),
                        Task.next_occurrence_at.is_not(None),
                        Task.next_occurrence_at <= now,
                        Task.status != "cancelled",
                    )
                    .order_by(Task.next_occurrence_at)
                    .with_for_update(skip_locked=True)
                )
            ).scalars()
        )
        return sum([await self._spawn_series(session, tenant_id, head, now) for head in heads])

    async def _spawn_series(
        self, session: AsyncSession, tenant_id: uuid.UUID, head: Task, now: datetime
    ) -> int:
        repeat = self._repeat_of(head.recurrence_rule)
        if repeat is None:
            logger.warning("tasks.spawn_unreadable_rule", task=head.code)
            return 0
        anchor = self._anchor(head.due_at, head.created_at)
        made = handled = 0
        while (
            head.next_occurrence_at is not None
            and head.next_occurrence_at <= now
            and handled < _SPAWN_CATCH_UP_LIMIT
        ):
            handled += 1
            due = head.next_occurrence_at
            key = f"{head.id}:{due.astimezone(UTC).date().isoformat()}"
            child: Task | None = None
            # A task already raised for this head and date (a run that stopped before it
            # moved the head on) is not raised again; the head just moves on.
            taken = await session.scalar(
                select(Task.id).where(
                    Task.tenant_id == tenant_id,
                    Task.source == _RECURRENCE_SOURCE,
                    Task.external_id == key,
                )
            )
            if taken is None:
                try:
                    child = await self._spawn_occurrence(session, tenant_id, head, due, key)
                except Conflict:
                    # The code would not allocate, or another run raised it between the check
                    # and the insert. Leave the head as it is; the next run looks again.
                    logger.warning("tasks.spawn_conflict", task=head.code, due=due.isoformat())
                    break
                made += 1
            following = next_after(anchor, repeat, due.astimezone(UTC).date())
            head.next_occurrence_at = (
                datetime.combine(following, time.min, tzinfo=UTC) if following else None
            )
            await self._audit.record(
                session,
                action="update",
                object_type="task",
                object_id=head.id,
                actor=System(),
                tenant_id=tenant_id,
                before={"next_occurrence_at": due.isoformat()},
                after={
                    "next_occurrence_at": head.next_occurrence_at.isoformat()
                    if head.next_occurrence_at
                    else None,
                    "occurrence": child.code if child else None,
                },
            )
        await session.flush()
        return made

    async def _spawn_occurrence(
        self, session: AsyncSession, tenant_id: uuid.UUID, head: Task, due: datetime, key: str
    ) -> Task:
        """A fresh copy of the head, due on its scheduled date. What carries over is what
        describes the work: its words, priority, severity, SLA level, people and links. What
        does not is what happened to the head: its status, history, comments, and the
        evidence attached to it, since the next one starts with none."""
        from verity.modules.notifications.service import notification_service  # noqa: PLC0415

        assignees = (await self._assignees_by_task(session, tenant_id, [head.id])).get(head.id, [])
        due_on = due.astimezone(UTC).date()
        child = await self._create(
            session,
            tenant_id=tenant_id,
            actor=System(),
            task_kind=head.task_kind,
            title=head.title,
            description=head.description,
            priority=head.priority,
            category=head.category,
            sla_level=head.sla_level,
            owner_membership_id=head.owner_membership_id,
            assignee_ids=assignees,
            due_at=due,
            raised_from_type=head.raised_from_type,
            impact=head.impact,
            urgency=head.urgency,
            decision=SeverityDecision(
                head.severity, head.severity_override, head.severity_override_reason
            ),
            requires_approval=head.requires_approval,
            recurrence_parent_id=head.id,
            source=_RECURRENCE_SOURCE,
            external_id=key,
            audit_extra={"repeats": head.code, "due": due_on.isoformat()},
        )
        for edge in await link_service.for_object(
            session, tenant_id=tenant_id, obj_type="task", obj_id=head.id
        ):
            if edge.other_type == "evidence":
                continue
            outgoing = edge.direction == "outgoing"
            await link_service.create(
                session,
                tenant_id=tenant_id,
                from_type="task" if outgoing else edge.other_type,
                from_id=child.id if outgoing else edge.other_id,
                to_type=edge.other_type if outgoing else "task",
                to_id=edge.other_id if outgoing else child.id,
                relation=edge.relation,
                note=edge.note,
            )
        await notification_service.notify_many(
            session,
            tenant_id=tenant_id,
            recipients={head.owner_membership_id, *assignees},
            kind="recurrence",
            title=f"{child.code} was created from {head.code}",
            body=f"{child.title}, due {due_on.day} {due_on:%b}",
            object_type="task",
            object_id=child.id,
            email=True,
        )
        return child

    async def raise_evidence_renewals(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> int:
        """Raise one renewal task for each evidence item past its validity, as the system.

        Follows the ``evidence_stale`` automation: nothing when it is switched off, and
        its owner rule, kind, priority and days to due otherwise. An item gets one task
        per stale spell, keyed on its renewal date, so a task someone closed without
        renewing the evidence is not raised again for the same lapse, while renewing the
        evidence and letting it lapse a second time earns a new one. An item that already
        has an open renewal task is left alone whatever its date. Returns how many tasks
        it made.
        """
        from verity.modules.compliance.control_service import control_service  # noqa: PLC0415
        from verity.modules.evidence.service import evidence_service  # noqa: PLC0415
        from verity.modules.notifications.service import notification_service  # noqa: PLC0415

        rule = next(
            a
            for a in await self.list_automations(session, tenant_id=tenant_id)
            if a["id"] == _RENEWAL_AUTOMATION
        )
        if not rule["enabled"]:
            return 0
        stale = await evidence_service.list_evidence(
            session, tenant_id=tenant_id, freshness_filter="stale"
        )
        # What a connector filed is replaced by its next run, not renewed by a person: a
        # lapsed file is history, or the sign that the connection stopped, which the
        # control page and the connection already say. A task for each would be one
        # per check per day.
        stale = [item for item in stale if item.source is None]
        if not stale:
            return 0

        keys = {
            item.id: f"{_RENEWAL_AUTOMATION}:{item.id}:{item.renewal_date.isoformat()}"
            for item in stale
            if item.renewal_date is not None
        }
        raised = set(
            (
                await session.execute(
                    select(Task.external_id).where(
                        Task.tenant_id == tenant_id,
                        Task.source == _AUTOMATION_SOURCE,
                        Task.external_id.in_(list(keys.values())),
                    )
                )
            ).scalars()
        )
        linked = await link_service.ids_of_type_linked_from(
            session, tenant_id=tenant_id, from_type="evidence", from_ids=list(keys), to_type="task"
        )
        linked_tasks = {task_id for ids in linked.values() for task_id in ids}
        open_renewals = (
            set(
                (
                    await session.execute(
                        select(Task.id).where(
                            Task.tenant_id == tenant_id,
                            Task.id.in_(list(linked_tasks)),
                            Task.raised_from_type == _RENEWAL_RAISED_FROM,
                            Task.status.in_(_ACTIVE),
                        )
                    )
                ).scalars()
            )
            if linked_tasks
            else set()
        )
        controls = await control_service.list_controls(
            session, tenant_id=tenant_id, include_disabled=True
        )
        code_of = {c.id: c.code for c in controls}
        owner_of = {c.id: c.owner_membership_id for c in controls}

        system = System()
        today = datetime.now(UTC).date()
        due_at = datetime.combine(
            today + timedelta(days=int(rule["due_in_days"])), time.min, tzinfo=UTC
        )
        made = 0
        for item in stale:
            key, lapsed_on = keys.get(item.id), item.renewal_date
            if (
                key is None
                or lapsed_on is None
                or key in raised
                or open_renewals.intersection(linked.get(item.id, []))
            ):
                continue
            # The item's own owner first; failing that, the owner of the first of its controls
            # (by code) that has one.
            owner = None
            if rule["owner_rule"] != "unassigned":
                owner = item.owner_membership_id
                for control_id in sorted(item.control_ids, key=lambda c: code_of.get(c, "")):
                    if owner is not None:
                        break
                    owner = owner_of.get(control_id)
            codes = sorted(code_of[c] for c in item.control_ids if c in code_of)
            try:
                task = await self._create(
                    session,
                    tenant_id=tenant_id,
                    actor=system,
                    task_kind=str(rule["creates"]),
                    title=f"Renew evidence: {item.title}"[:300],
                    description=_renewal_description(item.title, lapsed_on, codes),
                    priority=str(rule["priority"]),
                    category="regulatory",
                    sla_level=None,
                    owner_membership_id=owner,
                    assignee_ids=[owner] if owner else [],
                    due_at=due_at,
                    raised_from_type=_RENEWAL_RAISED_FROM,
                    source=_AUTOMATION_SOURCE,
                    external_id=key,
                    audit_extra={"evidence_id": str(item.id), "renewal_date": str(lapsed_on)},
                )
            except Conflict:
                logger.warning("tasks.renewal_conflict", evidence=str(item.id))
                continue
            await evidence_service.link_to_task(
                session, tenant_id=tenant_id, actor=system, evidence_id=item.id, task_id=task.id
            )
            await self._transition_row(
                session, task, system, "attachment", None, str(item.id), None
            )
            for control_id in item.control_ids:
                await link_service.create(
                    session,
                    tenant_id=tenant_id,
                    from_type="task",
                    from_id=task.id,
                    to_type="control",
                    to_id=control_id,
                )
            if owner is not None:
                await notification_service.notify(
                    session,
                    tenant_id=tenant_id,
                    recipient_membership_id=owner,
                    kind="assigned",
                    title=f"You were assigned {task.code}",
                    body=task.title,
                    object_type="task",
                    object_id=task.id,
                    email=True,
                )
            made += 1
        await session.flush()
        return made

    # -- config --------------------------------------------------------------

    async def sla_definitions(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        # Merge the built-in default levels with any the tenant has customised, so a
        # fresh tenant still has a working SLA picker (mirrors the severity matrix).
        rows = {
            r.level: r
            for r in (
                await session.execute(
                    select(SlaDefinition).where(SlaDefinition.tenant_id == tenant_id)
                )
            ).scalars()
        }
        out: list[dict[str, Any]] = []
        for level, resolve in _DEFAULT_RESOLVE_HOURS.items():
            row = rows.pop(level, None)
            if row is not None:
                out.append(
                    {
                        "level": row.level,
                        "respond_hours": row.respond_hours,
                        "resolve_hours": row.resolve_hours,
                    }
                )
            else:
                out.append(
                    {
                        "level": level,
                        "respond_hours": max(1, resolve // 4),
                        "resolve_hours": resolve,
                    }
                )
        # Any remaining rows are tenant-defined levels beyond the built-ins.
        for row in rows.values():
            out.append(
                {
                    "level": row.level,
                    "respond_hours": row.respond_hours,
                    "resolve_hours": row.resolve_hours,
                }
            )
        out.sort(key=lambda d: d["resolve_hours"])
        return out

    async def upsert_sla_definition(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        original_level: str | None,
        level: str,
        respond_hours: int,
        resolve_hours: int,
    ) -> list[dict[str, Any]]:
        level = level.strip()
        if not level:
            raise InvalidInput(
                "Give this SLA level a name before saving it.",
                detail="an SLA level needs a name",
            )
        # A rename drops the old customised row (a built-in level then re-defaults).
        if original_level and original_level != level:
            await session.execute(
                delete(SlaDefinition).where(
                    SlaDefinition.tenant_id == tenant_id, SlaDefinition.level == original_level
                )
            )
        row = (
            await session.execute(
                select(SlaDefinition).where(
                    SlaDefinition.tenant_id == tenant_id, SlaDefinition.level == level
                )
            )
        ).scalar_one_or_none()
        if row is None:
            row = SlaDefinition(
                id=uuid7(),
                tenant_id=tenant_id,
                level=level,
                respond_hours=respond_hours,
                resolve_hours=resolve_hours,
            )
            session.add(row)
        else:
            row.respond_hours = respond_hours
            row.resolve_hours = resolve_hours
        await self._audit.record(
            session,
            action="update",
            object_type="sla_definition",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"level": level, "respond_hours": respond_hours, "resolve_hours": resolve_hours},
        )
        await session.flush()
        return await self.sla_definitions(session, tenant_id=tenant_id)

    async def delete_sla_definition(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor, level: str
    ) -> list[dict[str, Any]]:
        row = (
            await session.execute(
                select(SlaDefinition).where(
                    SlaDefinition.tenant_id == tenant_id, SlaDefinition.level == level
                )
            )
        ).scalar_one_or_none()
        if row is not None:
            await self._audit.record(
                session,
                action="delete",
                object_type="sla_definition",
                object_id=row.id,
                actor=actor,
                tenant_id=tenant_id,
                before={"level": level},
            )
            await session.delete(row)
            await session.flush()
        return await self.sla_definitions(session, tenant_id=tenant_id)

    async def severity_matrix(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        rows = {
            (c.impact, c.urgency): c
            for c in (
                await session.execute(
                    select(TaskSeverityMatrixCell).where(
                        TaskSeverityMatrixCell.tenant_id == tenant_id
                    )
                )
            ).scalars()
        }
        out: list[dict[str, Any]] = []
        for impact in IMPACTS:
            for urgency in URGENCIES:
                cell = rows.get((impact, urgency))
                if cell is not None:
                    out.append(
                        {
                            "impact": impact,
                            "urgency": urgency,
                            "severity": cell.severity,
                            "respond_hours": cell.respond_hours,
                            "resolve_hours": cell.resolve_hours,
                            "default_owner_membership_id": cell.default_owner_membership_id,
                            "is_default": False,
                        }
                    )
                else:
                    sev, hours = _DEFAULT_MATRIX[(impact, urgency)]
                    out.append(
                        {
                            "impact": impact,
                            "urgency": urgency,
                            "severity": sev,
                            "respond_hours": max(1, hours // 4),
                            "resolve_hours": hours,
                            "default_owner_membership_id": None,
                            "is_default": True,
                        }
                    )
        return out

    async def upsert_matrix_cell(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        impact: str,
        urgency: str,
        severity: str,
        respond_hours: int,
        resolve_hours: int,
    ) -> list[dict[str, Any]]:
        if impact not in IMPACTS or urgency not in URGENCIES:
            raise InvalidInput(
                "Pick an impact and an urgency of high, medium or low for this cell.",
                detail="invalid matrix cell",
            )
        cell = (
            await session.execute(
                select(TaskSeverityMatrixCell).where(
                    TaskSeverityMatrixCell.tenant_id == tenant_id,
                    TaskSeverityMatrixCell.impact == impact,
                    TaskSeverityMatrixCell.urgency == urgency,
                )
            )
        ).scalar_one_or_none()
        if cell is None:
            cell = TaskSeverityMatrixCell(
                id=uuid7(), tenant_id=tenant_id, impact=impact, urgency=urgency
            )
            session.add(cell)
        cell.severity = severity
        cell.respond_hours = respond_hours
        cell.resolve_hours = resolve_hours
        await self._audit.record(
            session,
            action="update",
            object_type="task_severity_matrix",
            object_id=tenant_id,
            actor=actor,
            tenant_id=tenant_id,
            after={"cell": f"{impact}/{urgency}", "severity": severity},
        )
        await session.flush()
        return await self.severity_matrix(session, tenant_id=tenant_id)

    async def saved_views(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[TaskSavedView]:
        rows = (
            await session.execute(
                select(TaskSavedView)
                .where(TaskSavedView.tenant_id == tenant_id)
                .order_by(TaskSavedView.position)
            )
        ).scalars()
        return list(rows)

    async def templates(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> list[TaskTemplate]:
        rows = (
            await session.execute(
                select(TaskTemplate)
                .where(TaskTemplate.tenant_id == tenant_id)
                .order_by(TaskTemplate.name)
            )
        ).scalars()
        return list(rows)

    # -- summary -------------------------------------------------------------

    async def summary(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> dict[str, Any]:
        tasks = list(
            (
                await session.execute(
                    select(Task).where(Task.tenant_id == tenant_id, Task.parent_task_id.is_(None))
                )
            ).scalars()
        )
        active = [t for t in tasks if t.status in _ACTIVE]
        by_priority: dict[str, int] = dict.fromkeys(PRIORITIES, 0)
        for t in active:
            by_priority[t.priority] += 1

        now = datetime.now(UTC)
        bands = [("< 3 days", 3.0), ("3-7 days", 7.0), ("1-4 weeks", 28.0), ("> 4 weeks", 1e9)]
        ageing = []
        prev = 0.0
        for label, hi in bands:
            count = sum(1 for t in active if prev <= (now - t.created_at).days < hi)
            ageing.append({"band": label, "count": count})
            prev = hi

        assignees = await self._assignees_by_task(session, tenant_id, [t.id for t in active])
        names = await self._member_names(session, tenant_id)
        load: dict[uuid.UUID, int] = {}
        for t in active:
            for mid in assignees.get(t.id, []):
                load[mid] = load.get(mid, 0) + 1

        mttr: dict[str, list[float]] = {}
        for t in tasks:
            if t.status == "closed" and t.detected_at and t.resolved_at and t.severity:
                mttr.setdefault(t.severity, []).append(
                    (t.resolved_at - t.detected_at).total_seconds() / 86400
                )

        return {
            "open_total": len(active),
            "open_by_priority": by_priority,
            "breaching_now": sum(
                1 for t in active if sla_state(t.sla_due_at, t.status) == "breached"
            ),
            "due_soon": sum(1 for t in active if sla_state(t.sla_due_at, t.status) == "due_soon"),
            "ageing": ageing,
            "throughput": sum(1 for t in tasks if t.status == "closed"),
            "by_assignee": [
                {"member": {"membership_id": mid, "name": names.get(mid, "Unknown")}, "open": n}
                for mid, n in sorted(load.items(), key=lambda kv: -kv[1])
            ],
            "mttr": [
                {"severity": sev, "days": round(sum(v) / len(v), 1), "count": len(v)}
                for sev, v in mttr.items()
            ],
        }


task_service = TaskService()
