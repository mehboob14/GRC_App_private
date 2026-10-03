"""Engagement setup, scope resolution, and the coverage view.

Scope is elected at the Trust Services Category level, which is how SOC 2 scope
is actually chosen. The criteria in scope are then *derived*, never stored: a
criterion is in scope if its category was elected, or if it is always in scope
(the Common Criteria). Deriving rather than copying means a scope change is one
column write and cannot leave a stale criterion list behind.

Coverage answers two questions the Week 2 brief asks: which criteria in scope
have no control, and which controls have no evidence. The second is answered
honestly — the evidence module does not exist yet, so every control reports as
having none, and the response says so rather than implying zero is a finding.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import InvalidInput, NotFound
from verity.modules.audit.service import Actor, AuditService, audit_service
from verity.modules.compliance.models import (
    CONTROL_STATUSES,
    Control,
    ControlRequirement,
    Engagement,
    Framework,
    FrameworkVersion,
    FrameworkVersionRequirement,
    Requirement,
)
from verity.modules.compliance.readiness import control_ready, requirement_ready
from verity.shared.ids import uuid7

_ENGAGEMENT_SNAPSHOT = (
    "id",
    "name",
    "audit_type",
    "status",
    "window_start",
    "window_end",
    "categories_in_scope",
)


@dataclass(frozen=True, slots=True)
class CriterionCoverage:
    requirement_id: uuid.UUID
    requirement_key: str
    code: str
    name: str
    trust_services_category: str
    in_scope: bool
    control_count: int


@dataclass(frozen=True, slots=True)
class ControlGap:
    control_id: uuid.UUID
    code: str
    name: str
    reason: str


@dataclass(frozen=True, slots=True)
class CoverageReport:
    """What is covered, what is not, and what the numbers are counted over.

    ``criteria_total`` counts the criteria **in scope**, not the framework's
    whole set — a readiness figure measured against criteria a tenant has not
    elected would be wrong in the flattering direction.
    """

    criteria_total: int
    criteria_covered: int
    criteria_uncovered: list[CriterionCoverage]
    controls_total: int
    controls_without_evidence: int
    controls_no_evidence: list[ControlGap]
    """Itemised, not just counted. The other two gap lists are itemised, and a
    bare number the user cannot open is a dead end rather than a finding."""

    evidence_tracking_available: bool
    """Retained for the existing client contract, now always ``True``. The
    evidence module shipped on 2026-08-17; while this was hardcoded ``False``
    the scope screen told users evidence tracking had not arrived yet."""

    controls_unmapped: list[ControlGap]


@dataclass(frozen=True, slots=True)
class StatusCount:
    status: str
    count: int


@dataclass(frozen=True, slots=True)
class CategoryCoverage:
    category: str
    in_scope: int
    covered: int
    ready: int
    """Criteria with at least one control that is implemented *and* evidenced.
    ``ready <= covered <= in_scope``; the three split a category's bar into
    ready / covered-but-not-ready / no-control."""


@dataclass(frozen=True, slots=True)
class TimelinePoint:
    on: date
    controls: int
    evidence: int


@dataclass(frozen=True, slots=True)
class ActivityItem:
    occurred_at: datetime
    action: str
    actor_name: str | None
    control_code: str | None
    control_name: str | None


@dataclass(frozen=True, slots=True)
class OwnerCount:
    membership_id: uuid.UUID | None
    name: str
    role: str | None
    count: int


@dataclass(frozen=True, slots=True)
class DisabledControl:
    control_id: uuid.UUID
    code: str
    name: str
    reason: str | None


@dataclass(frozen=True, slots=True)
class RecentEvidence:
    title: str
    control_code: str | None
    collected_on: date
    freshness: str


@dataclass(frozen=True, slots=True)
class DashboardReport:
    """One read behind the compliance dashboard.

    Every number is measured, never estimated. Where the platform cannot yet
    measure something — automated checks, which need a connector — the report
    says so with a flag rather than reporting a zero that reads as a finding.

    Two headline figures are deliberately kept apart. ``criteria_covered`` asks
    only whether a control *exists* for a criterion; ``controls_ready`` asks
    whether a control is implemented, evidenced with something that still counts,
    and not contradicted by an automated test (``readiness.py``). A library that
    is fully adopted but unworked reads high on the first and near-zero on the
    second, and showing either alone would mislead.
    """

    has_engagement: bool
    criteria_total: int
    criteria_covered: int
    controls_total: int
    controls_evidenced: int
    controls_owned: int
    controls_disabled: int
    controls_internal: int
    controls_ready: int
    by_status: list[StatusCount]
    by_category: list[CategoryCoverage]
    tenant_created_on: date
    timeline_from: date
    timeline_to: date
    timeline: list[TimelinePoint]
    checks_available: bool
    recent_activity: list[ActivityItem]
    criteria_uncovered: int = 0
    controls_unmapped: int = 0
    controls_no_evidence: int = 0
    controls_in_progress: int = 0
    framework_name: str | None = None
    audit_type: str | None = None
    categories_in_scope: list[str] = field(default_factory=list)
    by_owner: list[OwnerCount] = field(default_factory=list)
    disabled: list[DisabledControl] = field(default_factory=list)
    evidence_total: int = 0
    evidence_fresh: int = 0
    evidence_aging: int = 0
    evidence_stale: int = 0
    evidence_recent: list[RecentEvidence] = field(default_factory=list)
    automation_passing: int = 0
    automation_failing: int = 0
    automation_error: int = 0


class EngagementService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service

    async def get(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> Engagement | None:
        result = await session.execute(select(Engagement).where(Engagement.tenant_id == tenant_id))
        return result.scalar_one_or_none()

    async def upsert(  # noqa: PLR0913 — the engagement's own fields
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        name: str,
        framework_version_id: uuid.UUID,
        audit_type: str,
        categories_in_scope: list[str],
        window_start: date | None = None,
        window_end: date | None = None,
        status: str | None = None,
    ) -> Engagement:
        version = await session.get(FrameworkVersion, framework_version_id)
        if version is None:
            raise NotFound(
                "That framework version is no longer available. "
                "Pick a version from the list and try again.",
                detail=f"framework version {framework_version_id}",
            )

        # Enforced here as well as by the CHECK so the client gets a typed
        # message instead of a constraint-violation surfaced as a 500.
        if audit_type == "type_2" and (window_start is None or window_end is None):
            raise InvalidInput(
                "A Type II audit covers a period of time, "
                "so add both a start date and an end date.",
                detail="a Type II engagement observes a period: both window dates are required",
            )
        if audit_type == "type_1" and (window_start is not None or window_end is not None):
            raise InvalidInput(
                "A Type I audit looks at a single point in time, "
                "so remove the start and end dates.",
                detail="a Type I engagement is a point in time and takes no observation window",
            )
        if window_start and window_end and window_end < window_start:
            raise InvalidInput(
                "The end date falls before the start date. "
                "Choose an end date on or after the start date.",
                detail="the observation window ends before it starts",
            )

        existing = await self.get(session, tenant_id=tenant_id)
        before = AuditService.snapshot(existing, fields=_ENGAGEMENT_SNAPSHOT) if existing else None

        if existing is None:
            engagement = Engagement(
                id=uuid7(),
                tenant_id=tenant_id,
                name=name.strip(),
                framework_version_id=framework_version_id,
                audit_type=audit_type,
                status=status or "draft",
                window_start=window_start,
                window_end=window_end,
                categories_in_scope=categories_in_scope,
            )
            session.add(engagement)
            await session.flush([engagement])
        else:
            engagement = existing
            engagement.name = name.strip()
            engagement.framework_version_id = framework_version_id
            engagement.audit_type = audit_type
            engagement.window_start = window_start
            engagement.window_end = window_end
            engagement.categories_in_scope = categories_in_scope
            if status is not None:
                engagement.status = status

        await self._audit.record(
            session,
            action="create" if existing is None else "update",
            object_type="engagement",
            object_id=engagement.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(engagement, fields=_ENGAGEMENT_SNAPSHOT),
        )
        return engagement

    # -- scope -------------------------------------------------------------------

    async def criteria_in_scope(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[Requirement]:
        """The criteria this tenant's engagement actually covers.

        No engagement yet means nothing has been elected, so only the
        always-in-scope Common Criteria apply — never "everything", which would
        overstate what a tenant has committed to.
        """
        engagement = await self.get(session, tenant_id=tenant_id)
        if engagement is None:
            return []

        rows = await session.execute(
            select(Requirement)
            .join(
                FrameworkVersionRequirement,
                FrameworkVersionRequirement.requirement_id == Requirement.id,
            )
            .where(
                FrameworkVersionRequirement.framework_version_id == engagement.framework_version_id
            )
            .order_by(Requirement.code)
        )
        elected = set(engagement.categories_in_scope)
        return [
            requirement
            for requirement in rows.scalars()
            if requirement.is_always_in_scope or requirement.trust_services_category in elected
        ]

    # -- coverage ----------------------------------------------------------------

    async def coverage(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> CoverageReport:
        in_scope = await self.criteria_in_scope(session, tenant_id=tenant_id)
        in_scope_ids = {requirement.id for requirement in in_scope}

        # How many live controls satisfy each criterion. A disabled control is
        # not coverage: it was retired, and counting it would hide a real gap.
        mapped = await session.execute(
            select(ControlRequirement.requirement_id, Control.id)
            .join(Control, Control.id == ControlRequirement.control_id)
            .where(
                ControlRequirement.tenant_id == tenant_id,
                Control.disabled_at.is_(None),
            )
        )
        per_criterion: dict[uuid.UUID, int] = {}
        mapped_control_ids: set[uuid.UUID] = set()
        for requirement_id, control_id in mapped:
            if requirement_id in in_scope_ids:
                per_criterion[requirement_id] = per_criterion.get(requirement_id, 0) + 1
            mapped_control_ids.add(control_id)

        uncovered = [
            CriterionCoverage(
                requirement_id=requirement.id,
                requirement_key=requirement.requirement_key,
                code=requirement.code,
                name=requirement.name,
                trust_services_category=requirement.trust_services_category,
                in_scope=True,
                control_count=per_criterion.get(requirement.id, 0),
            )
            for requirement in in_scope
            if per_criterion.get(requirement.id, 0) == 0
        ]

        controls = list(
            (
                await session.execute(
                    select(Control).where(
                        Control.tenant_id == tenant_id, Control.disabled_at.is_(None)
                    )
                )
            ).scalars()
        )
        unmapped = [
            ControlGap(
                control_id=control.id,
                code=control.code,
                name=control.name,
                reason="Not mapped to any criterion",
            )
            for control in controls
            if control.id not in mapped_control_ids
        ]

        # Deferred import, and through the service rather than the table: rule 4
        # forbids this module reading evidence's models, and evidence already
        # imports control_service the same way, so a module-level import here
        # would close the cycle.
        from verity.modules.evidence.service import evidence_service  # noqa: PLC0415

        with_evidence = await evidence_service.control_ids_with_evidence(session, tenant_id)
        no_evidence = [
            ControlGap(
                control_id=control.id,
                code=control.code,
                name=control.name,
                reason="No evidence attached",
            )
            for control in controls
            if control.id not in with_evidence
        ]

        return CoverageReport(
            criteria_total=len(in_scope),
            criteria_covered=len(in_scope) - len(uncovered),
            criteria_uncovered=uncovered,
            controls_total=len(controls),
            controls_without_evidence=len(no_evidence),
            controls_no_evidence=no_evidence,
            evidence_tracking_available=True,
            controls_unmapped=unmapped,
        )

    async def dashboard(  # noqa: PLR0915 — one straight-line aggregation; splitting into
        # single-use helpers that share a dozen locals would read worse, not better.
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        window_from: date | None = None,
        window_to: date | None = None,
    ) -> DashboardReport:
        """Everything the compliance dashboard shows, in one read.

        Point-in-time aggregates ignore the window; the timeline respects it.
        The window is clamped to [first control adoption, today] so a picker can
        never ask for a period the tenant did not exist for, or the future.
        """
        # The tenant's own controls and their criterion mappings — this module's
        # tables, so read directly. Everything else is derived from these rows in
        # Python; a library is ~120 rows, so one load beats a query per metric.
        controls = list(
            (await session.execute(select(Control).where(Control.tenant_id == tenant_id))).scalars()
        )
        by_control = {c.id: c for c in controls}
        live = [c for c in controls if c.disabled_at is None]

        mapped_rows = (
            await session.execute(
                select(ControlRequirement.requirement_id, ControlRequirement.control_id)
                .join(Control, Control.id == ControlRequirement.control_id)
                .where(ControlRequirement.tenant_id == tenant_id, Control.disabled_at.is_(None))
            )
        ).all()
        controls_by_requirement: dict[uuid.UUID, list[uuid.UUID]] = {}
        mapped_control_ids: set[uuid.UUID] = set()
        for requirement_id, control_id in mapped_rows:
            controls_by_requirement.setdefault(requirement_id, []).append(control_id)
            mapped_control_ids.add(control_id)
        mapped_requirement_ids = set(controls_by_requirement)

        from verity.modules.connectors.service import connector_service  # noqa: PLC0415
        from verity.modules.evidence.service import evidence_service  # noqa: PLC0415

        with_evidence = await evidence_service.control_ids_with_evidence(session, tenant_id)
        # Readiness asks for evidence that still counts (not rejected, not past its
        # renewal date) and for no automated test saying otherwise.
        with_current = await evidence_service.control_ids_with_current_evidence(session, tenant_id)
        automation = await connector_service.automation_statuses(session, tenant_id=tenant_id)

        def _ready(control: Control) -> bool:
            return control_ready(
                status=control.status,
                has_current_evidence=control.id in with_current,
                automation=automation.get(control.id),
            )

        def _requirement_ready(requirement_id: uuid.UUID) -> bool:
            # CF-4: met only when every control that applies to it is ready.
            return requirement_ready(
                (by_control[control_id].status, _ready(by_control[control_id]))
                for control_id in controls_by_requirement.get(requirement_id, ())
                if control_id in by_control
            )

        # Scope and criteria coverage, per Trust Services category. Each category
        # splits three ways: ready, covered-but-not-ready, and no control at all.
        in_scope = await self.criteria_in_scope(session, tenant_id=tenant_id)
        by_category_map: dict[str, list[int]] = {}
        for requirement in in_scope:
            covered = 1 if requirement.id in mapped_requirement_ids else 0
            ready = 1 if _requirement_ready(requirement.id) else 0
            bucket = by_category_map.setdefault(requirement.trust_services_category, [0, 0, 0])
            bucket[0] += 1
            bucket[1] += covered
            bucket[2] += ready
        by_category = [
            CategoryCoverage(category=name, in_scope=totals[0], covered=totals[1], ready=totals[2])
            for name, totals in sorted(by_category_map.items())
        ]
        criteria_covered = sum(row.covered for row in by_category)
        criteria_total = len(in_scope)

        status_counts = dict.fromkeys(CONTROL_STATUSES, 0)
        for control in live:
            status_counts[control.status] = status_counts.get(control.status, 0) + 1
        by_status = [StatusCount(status=s, count=status_counts[s]) for s in CONTROL_STATUSES]

        controls_evidenced = sum(1 for c in live if c.id in with_evidence)
        controls_ready = sum(1 for c in live if _ready(c))
        live_ids = {c.id for c in live}
        # A control whose last check is too old to count is one nobody can currently
        # verify, so it is counted with the ones that could not be checked.
        automation_counts = {
            label: sum(
                1
                for cid, state in automation.items()
                if cid in live_ids and state in ((label, "stale") if label == "error" else (label,))
            )
            for label in ("passing", "failing", "error")
        }

        # Timeline bounds. The earliest control adoption stands in for tenant
        # creation: the library is instantiated when the tenant is, and it keeps
        # the read inside this module rather than reaching for the tenants table.
        today = datetime.now(UTC).date()
        control_days = sorted(c.created_at.date() for c in controls)
        evidence_days = await evidence_service.collected_dates(session, tenant_id)
        floor = control_days[0] if control_days else today
        eff_to = min(window_to or today, today)
        eff_from = max(window_from or floor, floor)
        eff_from = min(eff_from, eff_to)

        change_days = sorted(
            {d for d in control_days + list(evidence_days) if eff_from <= d <= eff_to}
            | {eff_from, eff_to}
        )
        timeline = [
            TimelinePoint(
                on=day,
                controls=sum(1 for d in control_days if d <= day),
                evidence=sum(1 for d in evidence_days if d <= day),
            )
            for day in change_days
        ]

        entries, _ = await self._audit.list_page(
            session, tenant_id=tenant_id, limit=8, object_type="control"
        )
        labels = await self._audit.resolve_labels(session, entries)
        recent_activity = []
        for e in entries:
            # The event's object is a control; the code/name come from the rows
            # already loaded, so no per-event query. A disabled control removed
            # from the library would be absent here — its events then show no
            # code, which is correct rather than a crash.
            subject = by_control.get(e.object_id)
            recent_activity.append(
                ActivityItem(
                    occurred_at=e.occurred_at,
                    action=e.action,
                    actor_name=labels.actor(e.actor_type, e.actor_id),
                    control_code=subject.code if subject else None,
                    control_name=subject.name if subject else None,
                )
            )

        # Engagement context for the framework-progress header.
        engagement = await self.get(session, tenant_id=tenant_id)
        framework_name: str | None = None
        if engagement is not None:
            framework_name = (
                await session.execute(
                    select(Framework.name)
                    .join(FrameworkVersion, FrameworkVersion.framework_id == Framework.id)
                    .where(FrameworkVersion.id == engagement.framework_version_id)
                )
            ).scalar_one_or_none()

        # Controls per owner, names resolved through IAM's service (rule 4). The
        # unassigned bucket is a first-class row, not an omission — it is the one
        # a reviewer acts on first.
        from verity.modules.iam.service import iam_service  # noqa: PLC0415

        members = await iam_service.list_members(session, tenant_id=tenant_id)
        member_meta = {
            m.membership_id: (m.full_name, m.role_names[0] if m.role_names else None)
            for m in members
        }
        owner_counts: dict[uuid.UUID, int] = {}
        unassigned = 0
        for c in live:
            if c.owner_membership_id is None:
                unassigned += 1
            else:
                owner_counts[c.owner_membership_id] = owner_counts.get(c.owner_membership_id, 0) + 1
        by_owner = [
            OwnerCount(
                membership_id=mid,
                name=member_meta.get(mid, ("Unknown member", None))[0],
                role=member_meta.get(mid, (None, None))[1],
                count=count,
            )
            for mid, count in sorted(owner_counts.items(), key=lambda kv: kv[1], reverse=True)
        ]
        if unassigned:
            by_owner.append(
                OwnerCount(membership_id=None, name="Unassigned", role=None, count=unassigned)
            )

        disabled = [
            DisabledControl(control_id=c.id, code=c.code, name=c.name, reason=c.disabled_reason)
            for c in controls
            if c.disabled_at is not None
        ]

        # Evidence summary through the evidence service — freshness is its call to
        # make, and the views already carry the control codes for the recent list.
        ev_views = await evidence_service.list_evidence(session, tenant_id=tenant_id)
        evidence_recent = [
            RecentEvidence(
                title=v.title,
                control_code=v.control_codes[0] if v.control_codes else None,
                collected_on=v.collected_at,
                freshness=v.freshness,
            )
            for v in ev_views[:5]
        ]

        return DashboardReport(
            has_engagement=engagement is not None,
            framework_name=framework_name,
            audit_type=engagement.audit_type if engagement else None,
            categories_in_scope=list(engagement.categories_in_scope) if engagement else [],
            criteria_total=criteria_total,
            criteria_covered=criteria_covered,
            controls_total=len(live),
            controls_evidenced=controls_evidenced,
            controls_owned=sum(1 for c in live if c.owner_membership_id is not None),
            controls_disabled=len(controls) - len(live),
            controls_internal=sum(1 for c in live if c.origin != "template"),
            controls_ready=controls_ready,
            controls_in_progress=status_counts.get("in_progress", 0),
            by_status=by_status,
            by_category=by_category,
            by_owner=by_owner,
            disabled=disabled,
            evidence_total=len(ev_views),
            evidence_fresh=sum(1 for v in ev_views if v.freshness == "current"),
            evidence_aging=sum(1 for v in ev_views if v.freshness == "aging"),
            evidence_stale=sum(1 for v in ev_views if v.freshness == "stale"),
            evidence_recent=evidence_recent,
            tenant_created_on=floor,
            timeline_from=eff_from,
            timeline_to=eff_to,
            timeline=timeline,
            checks_available=bool(automation),
            automation_passing=automation_counts["passing"],
            automation_failing=automation_counts["failing"],
            automation_error=automation_counts["error"],
            recent_activity=recent_activity,
            criteria_uncovered=criteria_total - criteria_covered,
            controls_unmapped=sum(1 for c in live if c.id not in mapped_control_ids),
            controls_no_evidence=len(live) - controls_evidenced,
        )


engagement_service = EngagementService()
