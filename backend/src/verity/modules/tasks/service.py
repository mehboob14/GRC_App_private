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

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import Select, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.modules.audit.service import Actor, AuditService, Membership, audit_service
from verity.modules.tasks.models import (
    AUTOMATION_OWNER_RULES,
    CAPA_STATUSES,
    CAPA_TYPES,
    CATEGORIES,
    IMPACTS,
    PRIORITIES,
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
from verity.shared.ids import uuid7

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
        "owner_label": "the evidence's control owner",
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

    def _recurrence_summary(self, rule: str | None) -> str | None:
        if not rule:
            return None
        # A human hint for the badge; the RRULE is the source of truth.
        if "MONTHLY" in rule and "INTERVAL=3" in rule:
            return "Every 3 months"
        if "MONTHLY" in rule:
            return "Monthly"
        if "WEEKLY" in rule:
            return "Weekly"
        if "YEARLY" in rule:
            return "Yearly"
        return "Recurring"

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

        rows = [
            self._to_row(
                t,
                names,
                assignees.get(t.id, []),
                {"subtasks": subc.get(t.id, 0), "comments": comc.get(t.id, 0)},
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
                    .order_by(TaskTransition.occurred_at.desc())
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

        base = self._to_row(
            task, names, assignees, {"subtasks": len(sub_rows), "comments": len(comments)}
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
            allowed_transitions=list(ALLOWED_TRANSITIONS[task.status]),
        )

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

    # -- code allocation (with the retry documents lacks) --------------------

    async def _allocate_code(self, session: AsyncSession, tenant_id: uuid.UUID) -> str:
        highest = (
            await session.execute(
                select(func.max(Task.code)).where(
                    Task.tenant_id == tenant_id, Task.code.like("TSK-%")
                )
            )
        ).scalar_one_or_none()
        n = int(highest.removeprefix("TSK-")) if highest else 0
        return f"TSK-{n + 1:04d}"

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
    ) -> None:
        session.add(
            TaskTransition(
                id=uuid7(),
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

    # -- writes --------------------------------------------------------------

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
    ) -> TaskDetailView:
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
        # Retry the max+1 code against the unique constraint, so two concurrent
        # creates in one tenant both succeed with distinct codes.
        for _ in range(5):
            code = await self._allocate_code(session, tenant_id)
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
                sla_level=sla_level,
                sla_due_at=await self._resolve_sla_due(session, tenant_id, sla_level, now),
                owner_membership_id=owner_membership_id,
                reporter_membership_id=member,
                created_by_membership_id=member,
                due_at=due_at,
                raised_from_type=raised_from_type,
            )
            session.add(task)
            try:
                await session.flush([task])
                break
            except IntegrityError:
                await session.rollback()
        else:
            raise Conflict(_CODE_ERROR, detail="could not allocate a task code")

        for mid in dict.fromkeys(assignee_ids):
            session.add(
                TaskAssignee(id=uuid7(), tenant_id=tenant_id, task_id=task.id, membership_id=mid)
            )

        await self._transition_row(session, task, actor, "created", None, code, None)
        await self._audit.record(
            session,
            action="create",
            object_type="task",
            object_id=task.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"code": code, "title": task.title, "kind": task_kind},
        )
        # An issue raised from an event gets one corrective action to work from.
        if task_kind == "issue" and raised_from_type is not None:
            await self.ensure_initial_capa(session, tenant_id=tenant_id, actor=actor, task=task)
        await session.flush()
        return await self.get_task(session, tenant_id=tenant_id, task_id=task.id)

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
        for _ in range(5):
            code = await self._allocate_code(session, tenant_id)
            new_task = Task(
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
            )
            session.add(new_task)
            try:
                await session.flush([new_task])
                break
            except IntegrityError:
                await session.rollback()
        else:
            raise Conflict(_CODE_ERROR, detail="could not allocate a task code")
        if action.owner_membership_id is not None:
            session.add(
                TaskAssignee(
                    id=uuid7(),
                    tenant_id=tenant_id,
                    task_id=new_task.id,
                    membership_id=action.owner_membership_id,
                )
            )
        await self._transition_row(session, new_task, actor, "created", None, code, None)
        action.promoted_task_id = new_task.id
        await self._audit.record(
            session,
            action="create",
            object_type="task",
            object_id=new_task.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"code": code, "promoted_from_action": str(action.id)},
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

    async def update_task(  # noqa: PLR0913
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
    ) -> TaskDetailView:
        task = await self._load(session, tenant_id, task_id)
        changed: list[tuple[str, str | None, str | None]] = []

        if title is not None and title.strip() != task.title:
            changed.append(("title", task.title, title.strip()))
            task.title = title.strip()
        if description is not None:
            task.description = description.strip() or None
        if priority is not None and priority != task.priority:
            if priority not in PRIORITIES:
                raise InvalidInput(_PRIORITY_ERROR, detail=f"unknown priority {priority!r}")
            changed.append(("priority", task.priority, priority))
            task.priority = priority
        if category is not None and category != task.category:
            if category not in CATEGORIES:
                raise InvalidInput(_CATEGORY_ERROR, detail=f"unknown category {category!r}")
            changed.append(("category", task.category, category))
            task.category = category
        if sla_level is not None and sla_level != task.sla_level:
            task.sla_level = sla_level or None
            task.sla_due_at = await self._resolve_sla_due(
                session, tenant_id, task.sla_level, task.detected_at or task.created_at
            )
        if clear_owner:
            task.owner_membership_id = None
        elif owner_membership_id is not None and owner_membership_id != task.owner_membership_id:
            changed.append(("owner", str(task.owner_membership_id), str(owner_membership_id)))
            task.owner_membership_id = owner_membership_id
        if due_at is not None:
            task.due_at = due_at

        for fld, old, new in changed:
            await self._transition_row(session, task, actor, fld, old, new, None)
        if changed:
            await self._audit.record(
                session,
                action="update",
                object_type="task",
                object_id=task.id,
                actor=actor,
                tenant_id=tenant_id,
                after={fld: new for fld, _old, new in changed},
            )
        await session.flush()
        return await self.get_task(session, tenant_id=tenant_id, task_id=task.id)

    async def transition(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        task_id: uuid.UUID,
        to_status: str,
        note: str | None = None,
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
        elif to_status == "closed":
            task.closed_at = now
            task.closure_note = note
        elif to_status == "cancelled":
            task.cancelled_reason = note

        await self._transition_row(session, task, actor, "status", old, to_status, note)
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
        for _ in range(5):
            code = await self._allocate_code(session, tenant_id)
            child = Task(
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
            )
            session.add(child)
            try:
                await session.flush([child])
                break
            except IntegrityError:
                await session.rollback()
        else:
            raise Conflict(_CODE_ERROR, detail="could not allocate a task code")
        await self._transition_row(session, child, actor, "created", None, code, None)
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

    async def sla_watchlist(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[SlaAlert]:
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
                    m
                    for m in (t.owner_membership_id, *assignees.get(t.id, []))
                    if m is not None
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
