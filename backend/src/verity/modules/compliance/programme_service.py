"""The programme around an audit: commitments, vendors that count, milestones, cycles, changes.

Guided onboarding phase 3 (requirements EN-1, EN-4, EN-5, FS-6, SC-3, SC-8, SC-9). Each write is
audited in the caller's transaction; nothing here is ever deleted (rows are retired or stamped).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.modules.audit.service import Actor, AuditService, audit_service
from verity.modules.compliance.engagement_service import engagement_service
from verity.modules.compliance.models import (
    COMMITMENT_SOURCES,
    Commitment,
    Control,
    ControlRequirement,
    ControlTemplate,
    Engagement,
    EngagementMilestone,
    EngagementVendor,
    FrameworkVersion,
    Requirement,
    ScopeDecision,
    ScopeItem,
    TenantFramework,
)
from verity.shared.ids import uuid7

# -- milestones ------------------------------------------------------------------------

_M = tuple[str, str, str | None]
"""(kind, label, engagement field the date lives on, or None when stored as a milestone)."""

MILESTONE_PLANS: Final[dict[str, tuple[_M, ...]]] = {
    "type_1": (
        ("policies_approved", "Policies approved", None),
        ("readiness_review", "Readiness review", None),
        ("as_of", "Report as of date", "as_of_date"),
        ("fieldwork", "Fieldwork", None),
        ("report_issued", "Report issued", None),
    ),
    "type_2": (
        ("policies_approved", "Policies approved", None),
        ("period_start", "Observation period starts", "window_start"),
        ("period_end", "Observation period ends", "window_end"),
        ("fieldwork", "Fieldwork", None),
        ("report_issued", "Report issued", None),
    ),
    "initial_certification": (
        ("policies_approved", "Policies approved", None),
        ("isms_live", "Management system live", "live_date"),
        ("internal_audit", "Internal audit", None),
        ("management_review", "Management review", None),
        ("stage_1", "Stage 1 audit", "audit_on"),
        ("stage_2", "Stage 2 audit", None),
        ("decision", "Certification decision", None),
    ),
    "surveillance": (
        ("internal_audit", "Internal audit", None),
        ("management_review", "Management review", None),
        ("surveillance_audit", "Surveillance audit", "audit_on"),
    ),
    "recertification": (
        ("internal_audit", "Internal audit", None),
        ("management_review", "Management review", None),
        ("recertification_audit", "Recertification audit", "audit_on"),
        ("decision", "Certification decision", None),
    ),
}

_SUGGEST_KIND: Final[dict[str, str]] = {
    "application": "system",
    "infrastructure": "system",
    "cloud": "system",
    "data": "data_type",
    "business_service": "service",
}


@dataclass(frozen=True, slots=True)
class MilestoneView:
    kind: str
    label: str
    planned_on: date | None
    actual_on: date | None
    from_engagement: bool
    """True when the date lives on the engagement and is edited in audit details."""


@dataclass(frozen=True, slots=True)
class CycleView:
    id: uuid.UUID
    name: str
    audit_type: str
    status: str
    is_current: bool
    window_start: date | None
    window_end: date | None
    as_of_date: date | None
    audit_on: date | None
    certification_body: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class EngagementVendorView:
    vendor_id: uuid.UUID
    name: str
    tier: str | None
    role: str
    method: str | None
    note: str | None


_CADENCE_DAYS: Final[dict[str, int]] = {"monthly": 31, "quarterly": 92, "annual": 365}


@dataclass(frozen=True, slots=True)
class PeriodicRow:
    control_id: uuid.UUID
    code: str
    name: str
    cadence: str
    needed: int
    found: int


@dataclass(frozen=True, slots=True)
class PeriodicView:
    start: date | None
    end: date | None
    label: str | None
    rows: list[PeriodicRow]


@dataclass(frozen=True, slots=True)
class ChangeView:
    occurred_at: datetime
    object_type: str
    action: str
    summary: str


@dataclass(frozen=True, slots=True)
class SuggestionView:
    ref_type: str
    ref_id: uuid.UUID
    name: str
    kind: str


def _text(value: str | None, *, limit: int, what: str, required: bool = False) -> str | None:
    cleaned = (value or "").strip()
    if required and not cleaned:
        raise InvalidInput(f"Add the {what}.", detail=f"empty {what}")
    if len(cleaned) > limit:
        raise InvalidInput(f"Keep the {what} under {limit} characters.", detail=f"{what} too long")
    return cleaned or None


class ProgrammeService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service

    async def _engagement(
        self, session: AsyncSession, tenant_id: uuid.UUID, framework_code: str
    ) -> Engagement:
        engagement = await engagement_service.get(
            session, tenant_id=tenant_id, framework_code=framework_code
        )
        if engagement is None:
            raise Conflict(
                "Set up this framework's audit first.",
                detail=f"no engagement for {framework_code}",
            )
        return engagement

    # -- milestones (EN-4) ------------------------------------------------------------

    async def milestones(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, framework_code: str
    ) -> list[MilestoneView]:
        engagement = await engagement_service.get(
            session, tenant_id=tenant_id, framework_code=framework_code
        )
        if engagement is None:
            return []
        stored = {
            m.kind: m
            for m in (
                await session.execute(
                    select(EngagementMilestone).where(
                        EngagementMilestone.tenant_id == tenant_id,
                        EngagementMilestone.engagement_id == engagement.id,
                    )
                )
            ).scalars()
        }
        out: list[MilestoneView] = []
        for kind, label, field in MILESTONE_PLANS.get(engagement.audit_type, ()):
            if field is not None:
                out.append(
                    MilestoneView(
                        kind, label, getattr(engagement, field), None, from_engagement=True
                    )
                )
                continue
            row = stored.get(kind)
            out.append(
                MilestoneView(
                    kind,
                    label,
                    row.planned_on if row else None,
                    row.actual_on if row else None,
                    from_engagement=False,
                )
            )
        return out

    async def save_milestones(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        framework_code: str,
        changes: list[tuple[str, date | None, date | None]],
    ) -> list[MilestoneView]:
        engagement = await self._engagement(session, tenant_id, framework_code)
        plan = {kind: field for kind, _, field in MILESTONE_PLANS.get(engagement.audit_type, ())}
        for kind, planned_on, actual_on in changes:
            if kind not in plan:
                raise InvalidInput(
                    "That milestone is not part of this audit.", detail=f"milestone {kind!r}"
                )
            if plan[kind] is not None:
                raise InvalidInput(
                    "Set this date in the audit details.", detail=f"milestone {kind!r} is a field"
                )
            row = (
                await session.execute(
                    select(EngagementMilestone).where(
                        EngagementMilestone.tenant_id == tenant_id,
                        EngagementMilestone.engagement_id == engagement.id,
                        EngagementMilestone.kind == kind,
                    )
                )
            ).scalar_one_or_none()
            before = (
                {"planned_on": str(row.planned_on), "actual_on": str(row.actual_on)}
                if row
                else None
            )
            if row is None:
                row = EngagementMilestone(
                    id=uuid7(), tenant_id=tenant_id, engagement_id=engagement.id, kind=kind
                )
                session.add(row)
            row.planned_on = planned_on
            row.actual_on = actual_on
            await session.flush([row])
            await self._audit.record(
                session,
                action="create" if before is None else "update",
                object_type="engagement_milestone",
                object_id=row.id,
                actor=actor,
                tenant_id=tenant_id,
                before=before,
                after={"kind": kind, "planned_on": str(planned_on), "actual_on": str(actual_on)},
            )
        return await self.milestones(session, tenant_id=tenant_id, framework_code=framework_code)

    # -- cycles (EN-1) --------------------------------------------------------------------

    async def cycles(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, framework_code: str
    ) -> list[CycleView]:
        ctx = await engagement_service.context(
            session, tenant_id=tenant_id, framework_code=framework_code
        )
        if ctx is None:
            return []
        rows = (
            await session.execute(
                select(Engagement)
                .join(FrameworkVersion, FrameworkVersion.id == Engagement.framework_version_id)
                .where(
                    Engagement.tenant_id == tenant_id,
                    FrameworkVersion.framework_id == ctx.framework.id,
                )
                .order_by(Engagement.created_at.desc())
            )
        ).scalars()
        return [
            CycleView(
                id=e.id,
                name=e.name,
                audit_type=e.audit_type,
                status=e.status,
                is_current=e.is_current,
                window_start=e.window_start,
                window_end=e.window_end,
                as_of_date=e.as_of_date,
                audit_on=e.audit_on,
                certification_body=e.certification_body,
                created_at=e.created_at,
            )
            for e in rows
        ]

    async def next_cycle(  # noqa: PLR0913 — who, which framework, and the new cycle
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        framework_code: str,
        name: str,
        audit_type: str,
    ) -> Engagement:
        """Close the current cycle and open the next one. The scope decisions and the vendors
        that count carry over; dates, the auditor's state and milestones start fresh."""
        current = await self._engagement(session, tenant_id, framework_code)
        cleaned = _text(name, limit=200, what="name", required=True)
        assert cleaned is not None  # noqa: S101 — required above
        if audit_type == "type_2" or audit_type not in {
            "type_1",
            "initial_certification",
            "surveillance",
            "recertification",
        }:
            raise InvalidInput(
                "Choose the kind of audit for the next cycle. A Type 2 needs its period dates: "
                "start it as Type 1 or set the dates in audit details after it opens.",
                detail=f"next cycle audit type {audit_type!r}",
            )
        current.is_current = False
        current.status = "closed"
        await session.flush([current])
        nxt = Engagement(
            id=uuid7(),
            tenant_id=tenant_id,
            name=cleaned,
            framework_version_id=current.framework_version_id,
            audit_type=audit_type,
            status="draft",
            categories_in_scope=list(current.categories_in_scope),
            scope_statement=current.scope_statement,
            certification_body=current.certification_body,
            assessor_state=current.assessor_state,
            assessor_accreditation_body=current.assessor_accreditation_body,
            assessor_contact=current.assessor_contact,
            is_current=True,
        )
        session.add(nxt)
        await session.flush([nxt])
        decisions = (
            await session.execute(
                select(ScopeDecision).where(
                    ScopeDecision.tenant_id == tenant_id,
                    ScopeDecision.engagement_id == current.id,
                )
            )
        ).scalars()
        now = datetime.now(UTC)
        for d in decisions:
            session.add(
                ScopeDecision(
                    id=uuid7(),
                    tenant_id=tenant_id,
                    scope_item_id=d.scope_item_id,
                    engagement_id=nxt.id,
                    in_scope=d.in_scope,
                    reason=d.reason,
                    decided_by_membership_id=d.decided_by_membership_id,
                    decided_at=now,
                )
            )
        vendors = (
            await session.execute(
                select(EngagementVendor).where(
                    EngagementVendor.tenant_id == tenant_id,
                    EngagementVendor.engagement_id == current.id,
                    EngagementVendor.removed_at.is_(None),
                )
            )
        ).scalars()
        for v in vendors:
            session.add(
                EngagementVendor(
                    id=uuid7(),
                    tenant_id=tenant_id,
                    engagement_id=nxt.id,
                    vendor_id=v.vendor_id,
                    role=v.role,
                    method=v.method,
                    note=v.note,
                )
            )
        await session.flush()
        await self._audit.record(
            session,
            action="transition",
            object_type="engagement",
            object_id=current.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"is_current": True, "status": "active"},
            after={"is_current": False, "status": "closed", "next": str(nxt.id)},
        )
        await self._audit.record(
            session,
            action="create",
            object_type="engagement",
            object_id=nxt.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"name": cleaned, "audit_type": audit_type, "previous": str(current.id)},
        )
        return nxt

    # -- changes in the period (EN-5) ----------------------------------------------------

    async def periodic(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, framework_code: str
    ) -> PeriodicView:
        """Annual, quarterly and monthly controls planned against the audit (EN-8): for a
        Type 2 the observation period, otherwise the year before the audit date. Each row says
        how many occurrences the period needs and how many dated pieces of evidence fall in it."""
        from verity.modules.evidence.service import evidence_service  # noqa: PLC0415

        engagement = await engagement_service.get(
            session, tenant_id=tenant_id, framework_code=framework_code
        )
        if engagement is None:
            return PeriodicView(None, None, None, [])
        end = engagement.window_end or engagement.as_of_date or engagement.audit_on
        start = engagement.window_start or (end - timedelta(days=365) if end else None)
        if start is None or end is None:
            return PeriodicView(None, None, "Set the audit dates first.", [])
        label = "observation period" if engagement.window_start else "year before the audit date"
        rows = (
            await session.execute(
                select(Control.id, Control.code, Control.name, ControlTemplate.evidence)
                .join(ControlTemplate, ControlTemplate.id == Control.template_id)
                .where(
                    Control.tenant_id == tenant_id,
                    Control.disabled_at.is_(None),
                    Control.status != "not_applicable",
                )
            )
        ).all()
        dated = await evidence_service.collected_by_control(session, tenant_id, start, end)
        days = max((end - start).days, 1)
        out: list[PeriodicRow] = []
        for control_id, code, name, items in rows:
            cadences = {i.get("cadence") for i in items or [] if i.get("assurance") == "operating"}
            cadence = next((c for c in ("monthly", "quarterly", "annual") if c in cadences), None)
            if cadence is None:
                continue
            needed = max(1, -(-days // _CADENCE_DAYS[cadence]))
            found = len(dated.get(control_id, []))
            out.append(PeriodicRow(control_id, code, name, cadence, needed, found))
        out.sort(key=lambda r: (r.found >= r.needed, r.code))
        return PeriodicView(start, end, label, out)

    async def changes_in_period(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, framework_code: str
    ) -> list[ChangeView]:
        """Scope changes recorded inside a SOC 2 Type 2 period, for the description's disclosure.
        Empty for any other audit or before the period starts."""
        engagement = await engagement_service.get(
            session, tenant_id=tenant_id, framework_code=framework_code
        )
        if (
            engagement is None
            or engagement.audit_type != "type_2"
            or engagement.window_start is None
            or engagement.window_end is None
        ):
            return []
        out: list[ChangeView] = []
        for object_type in ("scope_decision", "scope_item", "engagement"):
            entries, _ = await self._audit.list_page(
                session, tenant_id=tenant_id, limit=200, object_type=object_type
            )
            for e in entries:
                day = e.occurred_at.date()
                if not engagement.window_start <= day <= engagement.window_end:
                    continue
                after = e.after or {}
                if object_type == "scope_decision" and after.get("framework") not in {
                    framework_code,
                    None,
                }:
                    continue
                if object_type == "engagement" and e.object_id != engagement.id:
                    continue
                out.append(
                    ChangeView(
                        occurred_at=e.occurred_at,
                        object_type=object_type,
                        action=e.action,
                        summary=_summary(object_type, e.action, after),
                    )
                )
        return sorted(out, key=lambda c: c.occurred_at, reverse=True)

    # -- commitments (SC-8) ------------------------------------------------------------------

    async def commitments(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> list[Commitment]:
        return list(
            (
                await session.execute(
                    select(Commitment)
                    .where(Commitment.tenant_id == tenant_id, Commitment.retired_at.is_(None))
                    .order_by(Commitment.created_at)
                )
            ).scalars()
        )

    async def save_commitment(  # noqa: PLR0913 — the commitment's own fields
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        commitment_id: uuid.UUID | None,
        statement: str,
        source_kind: str,
        source_ref: str | None,
        points_at: list[str],
    ) -> Commitment:
        text = _text(statement, limit=1000, what="promise", required=True)
        if source_kind not in COMMITMENT_SOURCES:
            raise InvalidInput("Say where this promise is written.", detail="source kind")
        ref = _text(source_ref, limit=300, what="reference")
        points = [p.strip() for p in points_at if p.strip()][:20]
        if commitment_id is None:
            row = Commitment(
                id=uuid7(), tenant_id=tenant_id, statement=text, source_kind=source_kind
            )
            session.add(row)
            before = None
        else:
            found = await session.get(Commitment, commitment_id)
            if found is None or found.tenant_id != tenant_id or found.retired_at is not None:
                raise NotFound(
                    "That promise no longer exists.", detail=f"commitment {commitment_id}"
                )
            row = found
            before = {"statement": row.statement, "source_kind": row.source_kind}
        row.statement = text or ""
        row.source_kind = source_kind
        row.source_ref = ref
        row.points_at = points
        await session.flush([row])
        await self._audit.record(
            session,
            action="create" if before is None else "update",
            object_type="commitment",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after={"statement": row.statement, "source_kind": source_kind, "points_at": points},
        )
        return row

    async def retire_commitment(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        commitment_id: uuid.UUID,
        reason: str,
    ) -> None:
        row = await session.get(Commitment, commitment_id)
        if row is None or row.tenant_id != tenant_id or row.retired_at is not None:
            raise NotFound("That promise no longer exists.", detail=f"commitment {commitment_id}")
        row.retired_reason = _text(reason, limit=1000, what="reason", required=True)
        row.retired_at = datetime.now(UTC)
        await session.flush([row])
        await self._audit.record(
            session,
            action="update",
            object_type="commitment",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"retired_at": None},
            after={"retired_at": row.retired_at.isoformat(), "reason": row.retired_reason},
        )

    # -- vendors that count (SC-9) -------------------------------------------------------------

    async def engagement_vendors(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, framework_code: str
    ) -> list[EngagementVendorView]:
        from verity.modules.vendors.service import vendor_service  # noqa: PLC0415

        engagement = await engagement_service.get(
            session, tenant_id=tenant_id, framework_code=framework_code
        )
        if engagement is None:
            return []
        rows = list(
            (
                await session.execute(
                    select(EngagementVendor).where(
                        EngagementVendor.tenant_id == tenant_id,
                        EngagementVendor.engagement_id == engagement.id,
                        EngagementVendor.removed_at.is_(None),
                    )
                )
            ).scalars()
        )
        names = await vendor_service.names(
            session, tenant_id=tenant_id, vendor_ids=[r.vendor_id for r in rows]
        )
        return sorted(
            (
                EngagementVendorView(
                    vendor_id=r.vendor_id,
                    name=names.get(r.vendor_id, ("Removed vendor", None))[0],
                    tier=names.get(r.vendor_id, ("", None))[1],
                    role=r.role,
                    method=r.method,
                    note=r.note,
                )
                for r in rows
            ),
            key=lambda v: v.name.lower(),
        )

    async def set_engagement_vendor(  # noqa: PLR0913 — the link's own fields
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        framework_code: str,
        vendor_id: uuid.UUID,
        role: str,
        method: str | None,
        note: str | None,
    ) -> None:
        from verity.modules.vendors.service import vendor_service  # noqa: PLC0415

        engagement = await self._engagement(session, tenant_id, framework_code)
        if not await vendor_service.names(session, tenant_id=tenant_id, vendor_ids=[vendor_id]):
            raise NotFound("That vendor no longer exists.", detail=f"vendor {vendor_id}")
        if role not in {"subservice", "supplier"}:
            raise InvalidInput("Choose how this vendor counts.", detail=f"role {role!r}")
        if role == "subservice" and method not in {"carve_out", "included"}:
            raise InvalidInput(
                "Say whether this subservice organisation is carved out or included.",
                detail="subservice without a method",
            )
        if role == "supplier":
            method = None
        row = (
            await session.execute(
                select(EngagementVendor).where(
                    EngagementVendor.tenant_id == tenant_id,
                    EngagementVendor.engagement_id == engagement.id,
                    EngagementVendor.vendor_id == vendor_id,
                )
            )
        ).scalar_one_or_none()
        before = (
            {"role": row.role, "method": row.method, "removed": row.removed_at is not None}
            if row
            else None
        )
        if row is None:
            row = EngagementVendor(
                id=uuid7(),
                tenant_id=tenant_id,
                engagement_id=engagement.id,
                vendor_id=vendor_id,
                role=role,
            )
            session.add(row)
        row.role = role
        row.method = method
        row.note = _text(note, limit=500, what="note")
        row.removed_at = None
        row.removed_reason = None
        await session.flush([row])
        await self._audit.record(
            session,
            action="create" if before is None else "update",
            object_type="engagement_vendor",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after={"vendor_id": str(vendor_id), "role": role, "method": method},
        )

    async def remove_engagement_vendor(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        framework_code: str,
        vendor_id: uuid.UUID,
        reason: str,
    ) -> None:
        engagement = await self._engagement(session, tenant_id, framework_code)
        row = (
            await session.execute(
                select(EngagementVendor).where(
                    EngagementVendor.tenant_id == tenant_id,
                    EngagementVendor.engagement_id == engagement.id,
                    EngagementVendor.vendor_id == vendor_id,
                    EngagementVendor.removed_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFound(
                "That vendor is not marked for this audit.", detail=f"vendor {vendor_id}"
            )
        row.removed_reason = _text(reason, limit=500, what="reason", required=True)
        row.removed_at = datetime.now(UTC)
        await session.flush([row])
        await self._audit.record(
            session,
            action="update",
            object_type="engagement_vendor",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"removed": False},
            after={"removed": True, "reason": row.removed_reason},
        )

    # -- scope suggestions (SC-3) -------------------------------------------------------------

    async def scope_suggestions(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[SuggestionView]:
        """Assets and critical or high vendors not yet on the scope list. A person accepts them."""
        from verity.modules.assets.service import asset_service  # noqa: PLC0415
        from verity.modules.vendors.service import vendor_service  # noqa: PLC0415

        listed = {
            (row[0], row[1])
            for row in (
                await session.execute(
                    select(ScopeItem.ref_type, ScopeItem.ref_id).where(
                        ScopeItem.tenant_id == tenant_id, ScopeItem.ref_id.is_not(None)
                    )
                )
            ).all()
        }
        out: list[SuggestionView] = []
        for asset_id, name, asset_type in await asset_service.scope_candidates(
            session, tenant_id=tenant_id
        ):
            if ("asset", asset_id) not in listed:
                out.append(
                    SuggestionView("asset", asset_id, name, _SUGGEST_KIND.get(asset_type, "system"))
                )
        for vendor_id, name in await vendor_service.scope_candidates(session, tenant_id=tenant_id):
            if ("vendor", vendor_id) not in listed:
                out.append(SuggestionView("vendor", vendor_id, name, "vendor"))
        return out

    async def accept_suggestions(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        refs: list[tuple[str, uuid.UUID]],
    ) -> int:
        offered = {
            (s.ref_type, s.ref_id): s
            for s in await self.scope_suggestions(session, tenant_id=tenant_id)
        }
        added = 0
        for ref in refs:
            suggestion = offered.get(ref)
            if suggestion is None:
                continue
            item = ScopeItem(
                id=uuid7(),
                tenant_id=tenant_id,
                kind=suggestion.kind,
                name=suggestion.name[:200],
                ref_type=suggestion.ref_type,
                ref_id=suggestion.ref_id,
                origin="suggested",
            )
            session.add(item)
            await session.flush([item])
            await self._audit.record(
                session,
                action="create",
                object_type="scope_item",
                object_id=item.id,
                actor=actor,
                tenant_id=tenant_id,
                after={"kind": item.kind, "name": item.name, "from": suggestion.ref_type},
            )
            added += 1
        return added

    # -- turning a framework off (FS-6) ------------------------------------------------------

    async def deactivate_framework(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        membership_id: uuid.UUID,
        framework_id: uuid.UUID,
        reason: str,
    ) -> list[str]:
        """Turn a framework off with a reason. Returns the codes of controls no other active
        framework needs; none of them is changed (a person decides)."""
        row = (
            await session.execute(
                select(TenantFramework).where(
                    TenantFramework.tenant_id == tenant_id,
                    TenantFramework.framework_id == framework_id,
                    TenantFramework.status == "active",
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFound("That framework is not active here.", detail=f"framework {framework_id}")
        others = set(
            (
                await session.execute(
                    select(TenantFramework.framework_id).where(
                        TenantFramework.tenant_id == tenant_id,
                        TenantFramework.status == "active",
                        TenantFramework.framework_id != framework_id,
                    )
                )
            ).scalars()
        )
        if not others:
            raise Conflict(
                "Keep at least one framework. Add another before turning this one off.",
                detail="last active framework",
            )
        cleaned = _text(reason, limit=1000, what="reason", required=True)
        row.status = "inactive"
        row.deactivated_reason = cleaned
        row.deactivated_at = datetime.now(UTC)
        row.deactivated_by_membership_id = membership_id
        await session.flush([row])
        await self._audit.record(
            session,
            action="transition",
            object_type="tenant_framework",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"status": "active"},
            after={"status": "inactive", "reason": cleaned},
        )
        links = (
            await session.execute(
                select(Control.code, Requirement.framework_id)
                .join(ControlRequirement, ControlRequirement.control_id == Control.id)
                .join(Requirement, Requirement.id == ControlRequirement.requirement_id)
                .where(Control.tenant_id == tenant_id, Control.disabled_at.is_(None))
            )
        ).all()
        by_control: dict[str, set[uuid.UUID]] = {}
        for code, fw in links:
            by_control.setdefault(code, set()).add(fw)
        return sorted(
            code for code, fws in by_control.items() if framework_id in fws and not fws & others
        )


def _summary(object_type: str, action: str, after: dict[str, object]) -> str:
    if object_type == "scope_decision":
        state = "in scope" if after.get("in_scope") else "out of scope"
        return f"A scope item was marked {state}"
    if object_type == "scope_item":
        if after.get("retired_at"):
            return f"A scope item was removed: {after.get('retired_reason', '')}".strip()
        return f"Scope item added: {after.get('name', '')}".strip()
    return "The audit setup changed" if action == "update" else "The audit was set up"


programme_service = ProgrammeService()
