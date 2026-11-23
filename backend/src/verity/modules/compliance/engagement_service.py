"""Engagement setup, scope resolution, and the coverage view.

Scope is elected at the Trust Services Category level, which is how SOC 2 scope
is actually chosen. The criteria in scope are then *derived*, never stored: a
criterion is in scope if its category was elected, or if it is always in scope
(the Common Criteria). Deriving rather than copying means a scope change is one
column write and cannot leave a stale criterion list behind.

A framework with the ``applicability`` scope model (ISO 27001) works the other way
round: everything is in scope until the workspace excludes a requirement with a
written reason, and a requirement the framework marks always in scope cannot be
excluded. Every read here takes the framework it is measuring, SOC 2 by default, so
what existed before a second framework keeps answering exactly as it did.

Coverage answers two questions the Week 2 brief asks: which criteria in scope
have no control, and which controls have no evidence. The second is answered
honestly — the evidence module does not exist yet, so every control reports as
having none, and the response says so rather than implying zero is a finding.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.modules.audit.service import Actor, AuditService, audit_service
from verity.modules.compliance.models import (
    AUDIT_TYPES_BY_SCOPE_MODEL,
    CONTROL_STATUSES,
    DEFAULT_FRAMEWORK,
    Control,
    ControlRequirement,
    Engagement,
    Framework,
    FrameworkVersion,
    FrameworkVersionRequirement,
    Requirement,
    RequirementApplicability,
    TenantFramework,
    natural_key,
)
from verity.modules.compliance.readiness import BUILT_IN_SOURCE, control_ready, requirement_ready
from verity.shared.ids import uuid7

_ENGAGEMENT_SNAPSHOT = (
    "id",
    "name",
    "audit_type",
    "status",
    "window_start",
    "window_end",
    "categories_in_scope",
    "scope_statement",
    "certification_body",
    "audit_on",
    "as_of_date",
    "target_date",
    "driver",
    "live_date",
    "assessor_state",
    "assessor_accreditation_body",
    "assessor_contact",
    "assessor_engaged_on",
    "scope_statement_ai",
    "scope_statement_approved_at",
)

DETAIL_FIELDS: tuple[str, ...] = (
    "as_of_date",
    "target_date",
    "driver",
    "live_date",
    "assessor",
    "assessor_accreditation_body",
    "assessor_contact",
    "assessor_engaged_on",
    "scope_statement_ai",
)
"""Engagement fields a save leaves untouched unless it sends them (EN-2, EN-3)."""


@dataclass(frozen=True, slots=True)
class FrameworkContext:
    """The framework a read is about, and what the workspace has set up for it."""

    framework: Framework
    version: FrameworkVersion | None
    """The version scope is measured against. None until the scope is set."""
    engagement: Engagement | None
    scope_set: bool
    """An engagement for a category framework; the framework being added for the
    others, which need no engagement to be measured."""

    @property
    def scope_model(self) -> str:
        return self.framework.scope_model

    def group_of(self, requirement: Requirement) -> str:
        """The label a requirement is bucketed under: its Trust Services Category for
        SOC 2, its clause or Annex A section for a framework with no such categories."""
        if self.scope_model == "categories":
            return requirement.trust_services_category
        return requirement.category


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
    framework_code: str | None = None
    scope_model: str = "categories"
    controls_shared: int = 0
    """Controls here that also answer a requirement of another framework."""
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


@dataclass(frozen=True, slots=True)
class FrameworkFigures:
    """One framework's counts for Get Started. Separate figures, never one blended score."""

    code: str
    name: str
    scope_model: str
    scope_set: bool
    audit_type: str | None
    window_start: date | None
    window_end: date | None
    audit_on: date | None
    certification_body: str | None
    scope_statement_set: bool
    as_of_date: date | None
    target_date: date | None
    live_date: date | None
    assessor: str
    """``chosen``, ``undecided`` or ``unknown`` (Engagement.assessor)."""
    requirements_total: int
    requirements_supported: int
    """In scope requirements with at least one live control mapped."""
    requirements_met: int
    controls_total: int
    controls_owned: int
    controls_evidenced: int
    """Controls with evidence that still counts (not rejected, not past renewal)."""
    checks_passing: int
    checks_failing: int
    decisions_total: int
    """Applicability frameworks only: requirements a workspace may decide on."""
    decisions_reviewed: int
    scope_statement_approved: bool = False


@dataclass(frozen=True, slots=True)
class ProgramFigures:
    frameworks: list[FrameworkFigures]
    controls_total: int
    controls_owned: int
    controls_evidenced: int
    controls_started: int
    checks_failing: int


class EngagementService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service

    async def context(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        framework_code: str = DEFAULT_FRAMEWORK,
    ) -> FrameworkContext | None:
        """The framework, its version for this workspace and its engagement.

        None when the framework is not in the catalogue. That is an empty database for
        the default framework (nothing to measure yet), and an unknown code otherwise,
        which the caller turns into a not found.
        """
        framework = (
            await session.execute(select(Framework).where(Framework.code == framework_code))
        ).scalar_one_or_none()
        if framework is None:
            return None
        engagement = (
            await session.execute(
                select(Engagement)
                .join(FrameworkVersion, FrameworkVersion.id == Engagement.framework_version_id)
                .where(
                    Engagement.tenant_id == tenant_id,
                    FrameworkVersion.framework_id == framework.id,
                    Engagement.is_current.is_(True),
                )
                .order_by(Engagement.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if framework.scope_model == "applicability":
            added = (
                await session.execute(
                    select(TenantFramework).where(
                        TenantFramework.tenant_id == tenant_id,
                        TenantFramework.framework_id == framework.id,
                        TenantFramework.status == "active",
                    )
                )
            ).scalar_one_or_none()
            version = (
                await session.get(FrameworkVersion, added.framework_version_id) if added else None
            )
            return FrameworkContext(framework, version, engagement, scope_set=added is not None)
        version = (
            await session.get(FrameworkVersion, engagement.framework_version_id)
            if engagement
            else None
        )
        return FrameworkContext(framework, version, engagement, scope_set=engagement is not None)

    async def _context_or_404(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, framework_code: str
    ) -> FrameworkContext | None:
        ctx = await self.context(session, tenant_id=tenant_id, framework_code=framework_code)
        if ctx is None and framework_code != DEFAULT_FRAMEWORK:
            raise NotFound(
                "That framework is not available here.", detail=f"framework {framework_code!r}"
            )
        return ctx

    async def get(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        framework_code: str = DEFAULT_FRAMEWORK,
    ) -> Engagement | None:
        ctx = await self._context_or_404(
            session, tenant_id=tenant_id, framework_code=framework_code
        )
        return ctx.engagement if ctx else None

    async def upsert(  # noqa: PLR0912, PLR0913, PLR0915 — the engagement's own fields
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
        scope_statement: str | None = None,
        certification_body: str | None = None,
        audit_on: date | None = None,
        sent: set[str] | None = None,
        details: dict[str, object] | None = None,
    ) -> Engagement:
        version = await session.get(FrameworkVersion, framework_version_id)
        if version is None:
            raise NotFound(
                "That framework version is no longer available. "
                "Pick a version from the list and try again.",
                detail=f"framework version {framework_version_id}",
            )
        framework = await session.get(Framework, version.framework_id)
        assert framework is not None  # noqa: S101 — the version's foreign key guarantees it
        allowed = AUDIT_TYPES_BY_SCOPE_MODEL[framework.scope_model]
        if audit_type not in allowed:
            raise InvalidInput(
                f"{framework.name} does not have that kind of audit. "
                "Choose one of the audits offered for it.",
                detail=f"audit type {audit_type!r} for framework {framework.code}",
            )
        if framework.scope_model == "applicability":
            categories_in_scope = []
            if window_start is not None or window_end is not None:
                raise InvalidInput(
                    "A certification audit has no observation window. "
                    "Remove the start and end dates and give the audit date instead.",
                    detail="window dates on a certification engagement",
                )
            added = await self.context(session, tenant_id=tenant_id, framework_code=framework.code)
            if added is None or not added.scope_set:
                raise Conflict(
                    f"Add {framework.name} to your workspace before setting up its audit.",
                    detail=f"engagement for {framework.code} before it was added",
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

        existing = await self.get(session, tenant_id=tenant_id, framework_code=framework.code)
        before = AuditService.snapshot(existing, fields=_ENGAGEMENT_SNAPSHOT) if existing else None
        # A SOC 2 form written before SOC 2 could carry a scope statement and an audit firm
        # does not send them; not sending keeps what is stored (SC-1, EN-3).
        scope_statement, certification_body, audit_on = self._kept(
            existing, sent, scope_statement, certification_body, audit_on
        )
        details = self._check_details(
            details or {}, audit_type=audit_type, scope_model=framework.scope_model
        )

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
                scope_statement=(scope_statement or "").strip() or None,
                certification_body=(certification_body or "").strip() or None,
                audit_on=audit_on,
            )
            self._apply_details(engagement, details, audit_type=audit_type)
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
            new_statement = (scope_statement or "").strip() or None
            if new_statement != engagement.scope_statement:
                # New wording needs its own approval (EN-11); an AI mark is kept only when the
                # same save says the text came from a draft.
                engagement.scope_statement_approved_at = None
                engagement.scope_statement_approved_by_membership_id = None
                if "scope_statement_ai" not in details:
                    engagement.scope_statement_ai = False
            engagement.scope_statement = new_statement
            engagement.certification_body = (certification_body or "").strip() or None
            engagement.audit_on = audit_on
            self._apply_details(engagement, details, audit_type=audit_type)
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

    async def plan_from_certificate(  # noqa: PLR0913 — who, which framework, the two dates
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        framework_code: str,
        issued_on: date | None,
        expires_on: date | None,
    ) -> str | None:
        """Plan the next audit date from a certificate already held (guided onboarding EX-2):
        a surveillance audit about a year after issue, a recertification audit three months
        before expiry. Only fills an empty date; returns what it did, for the person to see."""
        engagement = await self.get(session, tenant_id=tenant_id, framework_code=framework_code)
        if engagement is None:
            return None
        if engagement.audit_type == "surveillance" and issued_on is not None:
            planned = issued_on + timedelta(days=365)
            label = "Surveillance audit"
        elif engagement.audit_type == "recertification" and expires_on is not None:
            planned = expires_on - timedelta(days=90)
            label = "Recertification audit"
        else:
            return (
                "Set this audit to surveillance or recertification to plan its date from the "
                "certificate."
            )
        if engagement.audit_on is not None:
            return f"{label} already planned for {engagement.audit_on.isoformat()}."
        before = AuditService.snapshot(engagement, fields=_ENGAGEMENT_SNAPSHOT)
        engagement.audit_on = planned
        await session.flush([engagement])
        await self._audit.record(
            session,
            action="update",
            object_type="engagement",
            object_id=engagement.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(engagement, fields=_ENGAGEMENT_SNAPSHOT),
        )
        return f"{label} planned for {planned.isoformat()} from the certificate."

    async def approve_scope_statement(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        membership_id: uuid.UUID,
        framework_code: str,
    ) -> Engagement:
        """A named member approves the scope statement as written (EN-11)."""
        engagement = await self.get(session, tenant_id=tenant_id, framework_code=framework_code)
        if engagement is None or not (engagement.scope_statement or "").strip():
            raise Conflict(
                "Write the scope statement first, then approve it.", detail="no scope statement"
            )
        before = AuditService.snapshot(engagement, fields=_ENGAGEMENT_SNAPSHOT)
        engagement.scope_statement_approved_at = datetime.now(UTC)
        engagement.scope_statement_approved_by_membership_id = membership_id
        await session.flush([engagement])
        await self._audit.record(
            session,
            action="approve",
            object_type="engagement",
            object_id=engagement.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(engagement, fields=_ENGAGEMENT_SNAPSHOT),
        )
        return engagement

    async def add_category(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor, category: str
    ) -> Engagement:
        """Add one Trust Services Category to the SOC 2 scope (guided onboarding SC-5)."""
        engagement = await self.get(session, tenant_id=tenant_id, framework_code="SOC2")
        if engagement is None:
            raise Conflict(
                "Set up your SOC 2 report first, then add categories to it.",
                detail="category added before the SOC 2 engagement exists",
            )
        if category in engagement.categories_in_scope:
            return engagement
        before = AuditService.snapshot(engagement, fields=_ENGAGEMENT_SNAPSHOT)
        engagement.categories_in_scope = [*engagement.categories_in_scope, category]
        await session.flush([engagement])
        await self._audit.record(
            session,
            action="update",
            object_type="engagement",
            object_id=engagement.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(engagement, fields=_ENGAGEMENT_SNAPSHOT),
        )
        return engagement

    @staticmethod
    def _kept(
        existing: Engagement | None,
        sent: set[str] | None,
        scope_statement: str | None,
        certification_body: str | None,
        audit_on: date | None,
    ) -> tuple[str | None, str | None, date | None]:
        """The three shared fields, with any the save did not send kept as stored."""
        if existing is None or sent is None:
            return scope_statement, certification_body, audit_on
        return (
            scope_statement if "scope_statement" in sent else existing.scope_statement,
            certification_body if "certification_body" in sent else existing.certification_body,
            audit_on if "audit_on" in sent else existing.audit_on,
        )

    @staticmethod
    def _check_details(
        details: dict[str, object], *, audit_type: str, scope_model: str
    ) -> dict[str, object]:
        """Refuse a date that does not belong to this kind of audit, in plain words."""
        if details.get("as_of_date") is not None and audit_type != "type_1":
            raise InvalidInput(
                "Only a Type 1 report has an as of date. Remove it, or choose Type 1.",
                detail=f"as_of_date on a {audit_type} engagement",
            )
        if details.get("live_date") is not None and scope_model != "applicability":
            raise InvalidInput(
                "A go live date belongs to a management system, not to this framework.",
                detail="live_date on a category framework",
            )
        cleaned = dict(details)
        for name in ("driver", "assessor_accreditation_body", "assessor_contact"):
            if name in cleaned:
                cleaned[name] = (str(cleaned[name] or "")).strip() or None
        return cleaned

    @staticmethod
    def _apply_details(
        engagement: Engagement, details: dict[str, object], *, audit_type: str
    ) -> None:
        for name, value in details.items():
            if name == "assessor":
                engagement.assessor_state = str(value) if value else "unknown"
            else:
                setattr(engagement, name, value)
        # Changing away from Type 1 drops its as of date rather than failing the CHECK.
        if audit_type != "type_1":
            engagement.as_of_date = None
        # Naming the firm is choosing it; clearing the name without saying "still deciding"
        # returns the state to not answered.
        if (engagement.certification_body or "").strip():
            # Naming the firm is choosing it, unless this save said otherwise in the same breath.
            if "assessor" not in details:
                engagement.assessor_state = "chosen"
        elif engagement.assessor_state == "chosen":
            engagement.assessor_state = "unknown"

    # -- scope -------------------------------------------------------------------

    async def criteria_in_scope(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        framework_code: str = DEFAULT_FRAMEWORK,
    ) -> list[Requirement]:
        """The criteria this tenant's engagement actually covers.

        No engagement yet means nothing has been elected, so nothing is in scope —
        never "everything", which would overstate what a tenant has committed to.
        A framework that works by applicability has its scope the moment it is added:
        every requirement, less the ones the workspace excluded with a reason.
        """
        ctx = await self._context_or_404(
            session, tenant_id=tenant_id, framework_code=framework_code
        )
        return await self._in_scope(session, tenant_id=tenant_id, ctx=ctx)

    async def _in_scope(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, ctx: FrameworkContext | None
    ) -> list[Requirement]:
        if ctx is None or ctx.version is None or not ctx.scope_set:
            return []
        rows = await session.execute(
            select(Requirement)
            .join(
                FrameworkVersionRequirement,
                FrameworkVersionRequirement.requirement_id == Requirement.id,
            )
            .where(FrameworkVersionRequirement.framework_version_id == ctx.version.id)
        )
        requirements = sorted(rows.scalars(), key=lambda r: natural_key(r.code))
        if ctx.scope_model == "applicability":
            excluded = set(
                (
                    await session.execute(
                        select(RequirementApplicability.requirement_id).where(
                            RequirementApplicability.tenant_id == tenant_id,
                            RequirementApplicability.applicable.is_(False),
                        )
                    )
                ).scalars()
            )
            return [r for r in requirements if r.is_always_in_scope or r.id not in excluded]
        assert ctx.engagement is not None  # noqa: S101 — scope_set means one exists
        elected = set(ctx.engagement.categories_in_scope)
        return [
            requirement
            for requirement in requirements
            if requirement.is_always_in_scope or requirement.trust_services_category in elected
        ]

    async def _control_frameworks(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, set[uuid.UUID]]:
        """For each control, the frameworks it answers a requirement of."""
        rows = await session.execute(
            select(ControlRequirement.control_id, Requirement.framework_id)
            .join(Requirement, Requirement.id == ControlRequirement.requirement_id)
            .where(ControlRequirement.tenant_id == tenant_id)
        )
        found: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
        for control_id, framework_id in rows:
            found[control_id].add(framework_id)
        return found

    @staticmethod
    def _is_relevant(
        control_id: uuid.UUID,
        framework_id: uuid.UUID,
        by_control: dict[uuid.UUID, set[uuid.UUID]],
    ) -> bool:
        """A control belongs in a framework's numbers unless it exists only for another.

        The library is one list. A control that answers nothing yet (a workspace's own)
        counts everywhere, as it always did; a control that answers a requirement of
        this framework counts here; one that answers only another framework's does not,
        so adding ISO 27001 does not move a SOC 2 percentage with controls SOC 2 never asked for.
        """
        linked = by_control.get(control_id)
        return not linked or framework_id in linked

    # -- coverage ----------------------------------------------------------------

    async def coverage(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        framework_code: str = DEFAULT_FRAMEWORK,
    ) -> CoverageReport:
        ctx = await self._context_or_404(
            session, tenant_id=tenant_id, framework_code=framework_code
        )
        in_scope = await self._in_scope(session, tenant_id=tenant_id, ctx=ctx)
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
                trust_services_category=(
                    ctx.group_of(requirement) if ctx else requirement.trust_services_category
                ),
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

        with_evidence = await evidence_service.control_ids_with_evidence(
            session, tenant_id, exclude_source=BUILT_IN_SOURCE
        )
        by_framework = await self._control_frameworks(session, tenant_id)
        in_framework = [
            control
            for control in controls
            if ctx is None or self._is_relevant(control.id, ctx.framework.id, by_framework)
        ]
        no_evidence = [
            ControlGap(
                control_id=control.id,
                code=control.code,
                name=control.name,
                reason="No evidence attached",
            )
            for control in in_framework
            if control.id not in with_evidence
        ]

        return CoverageReport(
            criteria_total=len(in_scope),
            criteria_covered=len(in_scope) - len(uncovered),
            criteria_uncovered=uncovered,
            controls_total=len(in_framework),
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
        framework_code: str = DEFAULT_FRAMEWORK,
    ) -> DashboardReport:
        """Everything the compliance dashboard shows, in one read.

        Point-in-time aggregates ignore the window; the timeline respects it.
        The window is clamped to [first control adoption, today] so a picker can
        never ask for a period the tenant did not exist for, or the future.
        """
        # The tenant's own controls and their criterion mappings — this module's
        # tables, so read directly. Everything else is derived from these rows in
        # Python; a library is ~120 rows, so one load beats a query per metric.
        ctx = await self._context_or_404(
            session, tenant_id=tenant_id, framework_code=framework_code
        )
        controls = list(
            (await session.execute(select(Control).where(Control.tenant_id == tenant_id))).scalars()
        )
        by_framework = await self._control_frameworks(session, tenant_id)
        if ctx is not None:
            controls = [
                c for c in controls if self._is_relevant(c.id, ctx.framework.id, by_framework)
            ]
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
            if control_id not in by_control:
                continue  # exists only for another framework
            controls_by_requirement.setdefault(requirement_id, []).append(control_id)
            mapped_control_ids.add(control_id)
        mapped_requirement_ids = set(controls_by_requirement)

        from verity.modules.connectors.service import connector_service  # noqa: PLC0415
        from verity.modules.evidence.service import evidence_service  # noqa: PLC0415

        with_evidence = await evidence_service.control_ids_with_evidence(
            session, tenant_id, exclude_source=BUILT_IN_SOURCE
        )
        # Readiness asks for evidence that still counts (not rejected, not past its
        # renewal date) and for no automated test saying otherwise.
        with_current = await evidence_service.control_ids_with_current_evidence(
            session, tenant_id, exclude_source=BUILT_IN_SOURCE
        )
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
        in_scope = await self._in_scope(session, tenant_id=tenant_id, ctx=ctx)
        by_category_map: dict[str, list[int]] = {}
        for requirement in in_scope:
            covered = 1 if requirement.id in mapped_requirement_ids else 0
            ready = 1 if _requirement_ready(requirement.id) else 0
            group = ctx.group_of(requirement) if ctx else requirement.trust_services_category
            bucket = by_category_map.setdefault(group, [0, 0, 0])
            bucket[0] += 1
            bucket[1] += covered
            bucket[2] += ready
        # Trust Services Categories read best alphabetically; clauses and Annex A
        # sections read in the standard's own order, which is the order met first.
        group_items = (
            sorted(by_category_map.items())
            if ctx is None or ctx.scope_model == "categories"
            else list(by_category_map.items())
        )
        by_category = [
            CategoryCoverage(category=name, in_scope=totals[0], covered=totals[1], ready=totals[2])
            for name, totals in group_items
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
        engagement = ctx.engagement if ctx else None
        framework_name: str | None = ctx.framework.name if ctx and ctx.scope_set else None

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
        # Earlier results a connector has since replaced are history, not evidence that is
        # stale or aging for anyone to act on.
        ev_views = [
            v
            for v in await evidence_service.list_evidence(session, tenant_id=tenant_id)
            if not v.superseded
        ]
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
            has_engagement=bool(ctx and ctx.scope_set),
            framework_name=framework_name,
            framework_code=ctx.framework.code if ctx else None,
            scope_model=ctx.scope_model if ctx else "categories",
            controls_shared=sum(1 for c in live if len(by_framework.get(c.id, ())) > 1),
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

    # -- the programme at a glance (Get Started) ---------------------------------

    async def program_figures(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, framework_codes: list[str]
    ) -> ProgramFigures:
        """The counts Get Started shows, for every framework the workspace runs, in one read.

        The same rules as the dashboard (readiness.py, ``_is_relevant``), but the controls,
        evidence and automation states are loaded once for all frameworks, so the cost
        does not grow with the number of controls or frameworks beyond one scope read each.
        """
        from verity.modules.connectors.service import connector_service  # noqa: PLC0415
        from verity.modules.evidence.service import evidence_service  # noqa: PLC0415

        controls = list(
            (await session.execute(select(Control).where(Control.tenant_id == tenant_id))).scalars()
        )
        live = [c for c in controls if c.disabled_at is None]
        by_framework = await self._control_frameworks(session, tenant_id)
        with_current = await evidence_service.control_ids_with_current_evidence(
            session, tenant_id, exclude_source=BUILT_IN_SOURCE
        )
        automation = await connector_service.automation_statuses(session, tenant_id=tenant_id)
        mapped_rows = (
            await session.execute(
                select(ControlRequirement.requirement_id, ControlRequirement.control_id)
                .join(Control, Control.id == ControlRequirement.control_id)
                .where(ControlRequirement.tenant_id == tenant_id, Control.disabled_at.is_(None))
            )
        ).all()

        def _ready(control: Control) -> bool:
            return control_ready(
                status=control.status,
                has_current_evidence=control.id in with_current,
                automation=automation.get(control.id),
            )

        out: list[FrameworkFigures] = []
        for code in framework_codes:
            ctx = await self.context(session, tenant_id=tenant_id, framework_code=code)
            if ctx is None:
                continue
            relevant = {
                c.id: c for c in live if self._is_relevant(c.id, ctx.framework.id, by_framework)
            }
            per_requirement: dict[uuid.UUID, list[Control]] = defaultdict(list)
            for requirement_id, control_id in mapped_rows:
                if control_id in relevant:
                    per_requirement[requirement_id].append(relevant[control_id])
            in_scope = await self._in_scope(session, tenant_id=tenant_id, ctx=ctx)
            decisions_total = decisions_reviewed = 0
            if ctx.scope_model == "applicability" and ctx.version is not None:
                decidable = {
                    r.id
                    for r in (
                        await session.execute(
                            select(Requirement)
                            .join(
                                FrameworkVersionRequirement,
                                FrameworkVersionRequirement.requirement_id == Requirement.id,
                            )
                            .where(
                                FrameworkVersionRequirement.framework_version_id == ctx.version.id
                            )
                        )
                    ).scalars()
                    if not r.is_always_in_scope
                }
                reviewed = set(
                    (
                        await session.execute(
                            select(RequirementApplicability.requirement_id).where(
                                RequirementApplicability.tenant_id == tenant_id,
                                RequirementApplicability.reviewed_at.is_not(None),
                            )
                        )
                    ).scalars()
                )
                decisions_total = len(decidable)
                decisions_reviewed = len(decidable & reviewed)
            states = [automation.get(cid) for cid in relevant]
            out.append(
                FrameworkFigures(
                    code=ctx.framework.code,
                    name=ctx.framework.name,
                    scope_model=ctx.scope_model,
                    scope_set=ctx.scope_set,
                    audit_type=ctx.engagement.audit_type if ctx.engagement else None,
                    window_start=ctx.engagement.window_start if ctx.engagement else None,
                    window_end=ctx.engagement.window_end if ctx.engagement else None,
                    audit_on=ctx.engagement.audit_on if ctx.engagement else None,
                    certification_body=(
                        ctx.engagement.certification_body if ctx.engagement else None
                    ),
                    as_of_date=ctx.engagement.as_of_date if ctx.engagement else None,
                    target_date=ctx.engagement.target_date if ctx.engagement else None,
                    live_date=ctx.engagement.live_date if ctx.engagement else None,
                    assessor=ctx.engagement.assessor if ctx.engagement else "unknown",
                    scope_statement_set=bool(
                        ctx.engagement and (ctx.engagement.scope_statement or "").strip()
                    ),
                    scope_statement_approved=bool(
                        ctx.engagement and ctx.engagement.scope_statement_approved_at
                    ),
                    requirements_total=len(in_scope),
                    requirements_supported=sum(1 for r in in_scope if per_requirement.get(r.id)),
                    requirements_met=sum(
                        1
                        for r in in_scope
                        if requirement_ready((c.status, _ready(c)) for c in per_requirement[r.id])
                    ),
                    controls_total=len(relevant),
                    controls_owned=sum(
                        1 for c in relevant.values() if c.owner_membership_id is not None
                    ),
                    controls_evidenced=sum(1 for cid in relevant if cid in with_current),
                    checks_passing=states.count("passing"),
                    checks_failing=states.count("failing"),
                    decisions_total=decisions_total,
                    decisions_reviewed=decisions_reviewed,
                )
            )
        live_ids = {c.id for c in live}
        return ProgramFigures(
            frameworks=out,
            controls_total=len(live),
            controls_owned=sum(1 for c in live if c.owner_membership_id is not None),
            controls_evidenced=sum(1 for c in live if c.id in with_current),
            controls_started=sum(1 for c in live if c.status != "not_started"),
            checks_failing=sum(
                1 for cid, state in automation.items() if cid in live_ids and state == "failing"
            ),
        )


engagement_service = EngagementService()
