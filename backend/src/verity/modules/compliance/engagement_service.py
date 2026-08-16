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
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import InvalidInput, NotFound
from verity.modules.audit.service import Actor, AuditService, audit_service
from verity.modules.compliance.models import (
    Control,
    ControlRequirement,
    Engagement,
    FrameworkVersion,
    FrameworkVersionRequirement,
    Requirement,
)
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
    evidence_tracking_available: bool
    controls_unmapped: list[ControlGap]


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
            raise NotFound(detail=f"framework version {framework_version_id}")

        # Enforced here as well as by the CHECK so the client gets a typed
        # message instead of a constraint-violation surfaced as a 500.
        if audit_type == "type_2" and (window_start is None or window_end is None):
            raise InvalidInput(
                detail="a Type II engagement observes a period: both window dates are required"
            )
        if audit_type == "type_1" and (window_start is not None or window_end is not None):
            raise InvalidInput(
                detail="a Type I engagement is a point in time and takes no observation window"
            )
        if window_start and window_end and window_end < window_start:
            raise InvalidInput(detail="the observation window ends before it starts")

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

        return CoverageReport(
            criteria_total=len(in_scope),
            criteria_covered=len(in_scope) - len(uncovered),
            criteria_uncovered=uncovered,
            controls_total=len(controls),
            # The evidence module does not exist yet. Every control therefore has
            # no evidence, and the flag below tells the client that this is a
            # missing capability rather than a measured finding.
            controls_without_evidence=len(controls),
            evidence_tracking_available=False,
            controls_unmapped=unmapped,
        )


engagement_service = EngagementService()
