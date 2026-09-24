"""Vulnerability management service — the definition/instance logic (Week 6).

DB access lives here (no separate repository, matching evidence/documents).
Cross-module reads go through sibling *services* (rule 4): asset facts (name,
criticality, exposure, owner) via the assets service, member names via IAM,
fan-out via notifications. Enrichment (EPSS/KEV/public-exploit) comes from
``enrichment.py`` and prioritisation from ``scoring.py``. Every state change
appends a ``vuln_transitions`` row and writes an audit row (rules 5).
"""

from __future__ import annotations

import csv
import io
import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Final

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.core.storage import ObjectStore, get_object_store
from verity.modules.audit.service import Actor, AuditService, System, audit_service
from verity.modules.customfields.service import (
    FieldDefinition,
    FieldInput,
    custom_field_service,
)
from verity.modules.vulnerabilities import enrichment, remediation
from verity.modules.vulnerabilities.models import (
    ASSIGNMENT_TARGET_TYPES,
    CLOSED_STATES,
    OPEN_STATES,
    SEVERITIES,
    VulnAssignmentTarget,
    VulnDefinition,
    VulnException,
    VulnInstance,
    VulnRemediationPlan,
    VulnReport,
    VulnSlaPolicy,
    VulnTransition,
)
from verity.modules.vulnerabilities.references import Reference
from verity.modules.vulnerabilities.references import build as build_references
from verity.modules.vulnerabilities.scoring import (
    DEFAULT_SLA_DAYS,
    PRIORITY_BANDS,
    AssetRisk,
    RiskBreakdown,
    compute_breakdown,
    compute_risk,
    priority_band,
)
from verity.shared.ids import uuid7

if TYPE_CHECKING:
    from verity.modules.notifications.service import NotificationService

# Manual state machine: which target states a person may move an instance to from
# its current state. Closure to "fixed" is NOT a manual transition — it routes
# through pending_retest and the verify action (spec 130: fixed is verified, never
# just asserted). "resurfaced"/"new" are set by the scanner/import path; "accepted"
# is reached through accept_instance (reason + mandatory expiry).
_MANUAL_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
    "new": frozenset(("active", "in_progress", "false_positive")),
    "active": frozenset(("in_progress", "false_positive")),
    "in_progress": frozenset(("pending_retest", "active", "false_positive")),
    "pending_retest": frozenset(("active", "false_positive")),
    "resurfaced": frozenset(("in_progress", "active", "false_positive")),
    "fixed": frozenset(("active",)),
    "accepted": frozenset(("active",)),
    "false_positive": frozenset(("active",)),
}
# Only pending_retest may be verified into "fixed" — the formal closure step.
_VERIFIABLE_FROM: Final[frozenset[str]] = frozenset(("pending_retest",))
_INSTANCE_SNAPSHOT: Final = ("id", "state", "risk_score", "owner_membership_id", "sla_due_at")
#: What an exception audit row carries before/after (rule 5).
_EXCEPTION_SNAPSHOT: Final = (
    "id",
    "status",
    "duration_days",
    "decided_by_membership_id",
    "decided_at",
    "expires_at",
)
_SEVERITY_RANK: Final = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

# Reader-facing copy reused across several raises in this module.
_DEFINITION_GONE: Final = (
    "The details for this vulnerability are no longer available. It may have been "
    "deleted. Refresh the page and try again."
)
_INSTANCE_GONE: Final = "This vulnerability no longer exists. It may have been deleted."
_ASSET_GONE: Final = "That asset no longer exists. It may have been deleted. Pick another asset."
_REPORT_GONE: Final = "This scan report no longer exists. It may have been deleted."


# -- views -------------------------------------------------------------------


@dataclass(frozen=True)
class TransitionView:
    from_state: str | None
    to_state: str
    actor_name: str
    note: str | None
    occurred_at: datetime


@dataclass(frozen=True)
class InstanceView:
    id: uuid.UUID
    cve_id: str | None
    title: str
    severity: str
    cvss_score: float | None
    cvss_vector: str | None
    cwe_id: str | None
    state: str
    risk_score: float | None
    risk_reason: str | None
    priority_band: str
    kev_flag: bool
    epss_score: float | None
    epss_percentile: float | None
    public_exploit_count: int | None
    patch_available: bool | None
    asset_id: uuid.UUID
    asset_name: str
    asset_host: str | None
    locator: str
    owner_membership_id: uuid.UUID | None
    owner_name: str | None
    sla_due_at: datetime | None
    overdue: bool
    escalation_level: int
    first_detected_at: datetime | None
    last_seen_at: datetime | None
    detected_by: list[str]


@dataclass(frozen=True)
class AssignmentTargetView:
    """A person, role or group a finding is assigned to. ``name`` is the label
    captured when it was assigned, so a later rename cannot leave a stale row."""

    target_type: str
    target_id: uuid.UUID
    name: str


@dataclass(frozen=True)
class AffectedAssetView:
    """Another asset carrying the same definition (CVE/finding) — Verity's analogue
    of a finding linked to many assets, without a join table."""

    instance_id: uuid.UUID
    asset_id: uuid.UUID
    asset_name: str
    asset_host: str | None
    state: str
    risk_score: float | None
    priority_band: str


@dataclass(frozen=True)
class InstanceDetailView(InstanceView):
    # cvss_vector, cwe_id, epss_percentile and patch_available live on the base
    # InstanceView (the register needs them too) — do not redeclare them here.
    custom_fields: dict[str, Any]
    definition_id: uuid.UUID
    description: str | None
    recommendation: str | None
    kev_ransomware: bool
    exploit_refs: list[dict[str, object]]
    enriched_at: datetime | None
    fixed_versions: str | None
    advisory_url: str | None
    patch_source: str | None
    component: str | None
    port: int | None
    affected_url: str | None
    evidence: str | None
    reproduction_steps: str | None
    resolution_notes: str | None
    fixed_verified: bool
    resurfaced_count: int
    accepted_reason: str | None
    accepted_expires_at: datetime | None
    compensating_controls: str | None
    escalated_at: datetime | None
    false_positive_reason: str | None
    report_id: uuid.UUID | None
    #: When CISA added this CVE to the known-exploited catalogue. Stored since
    #: the first enrichment; a reader needs it to judge how long the clock has
    #: been running.
    kev_added_at: datetime | None = None
    kev_vendor: str | None = None
    kev_product: str | None = None
    kev_required_action: str | None = None
    #: CISA's own remediation deadline. Shown, never computed against — a
    #: second clock beside sla_due_at would change what "overdue" means.
    kev_due_at: datetime | None = None
    #: Primary sources behind the facts on this finding, so a reader can
    #: check the KEV badge, the EPSS score and the patch claim rather than
    #: take them on trust. Derived on read; nothing is stored.
    references: list[Reference] = field(default_factory=list)
    #: How the risk score was reached, recomputed on read from the same pure
    #: function that wrote it. Derived, never stored - a score whose derivation
    #: is stored can drift from the score itself.
    risk_breakdown: RiskBreakdown | None = None
    #: The linked asset's criticality inputs, so the asset step of the breakdown
    #: can name what it is weighing.
    asset_criticality: AssetCriticalityView | None = None
    #: The open request, or the decision that produced the current waiver. One
    #: at a time: a partial unique index allows only a single 'requested' row
    #: per finding.
    exception: ExceptionView | None = None
    transitions: list[TransitionView] = field(default_factory=list)
    affected_assets: list[AffectedAssetView] = field(default_factory=list)
    assignment_targets: list[AssignmentTargetView] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ExceptionRequest:
    """What a requester states. One value rather than four loose arguments."""

    duration_days: int
    rationale: str
    potential_risks: str
    compensating_controls: str | None = None


@dataclass(frozen=True, slots=True)
class ExceptionView:
    """A risk-acceptance request and the decision on it."""

    id: uuid.UUID
    status: str
    duration_days: int
    rationale: str
    potential_risks: str
    compensating_controls: str | None
    requested_by_membership_id: uuid.UUID | None
    requested_by_name: str | None
    requested_at: datetime
    decided_by_membership_id: uuid.UUID | None
    decided_by_name: str | None
    decided_at: datetime | None
    decision_note: str | None
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class AssetCriticalityView:
    """The linked asset's rating inputs. C/I/A are shown for context; only the
    collapsed ``tier`` and the two exposure flags actually weigh the score."""

    tier: str | None
    internet_facing: bool
    customer_facing: bool
    confidentiality: int | None
    integrity: int | None
    availability: int | None


@dataclass(frozen=True)
class KpiView:
    open_total: int
    open_by_severity: dict[str, int]
    open_by_priority: dict[str, int]
    sla_posture: dict[str, int]  # on_track / due_soon / overdue
    overdue: int
    kev_open: int
    accepted: int


@dataclass(frozen=True)
class ThroughputView:
    closed_30d: int
    opened_30d: int
    mttr_days_by_severity: dict[str, float | None]
    median_mttr_days: float | None


@dataclass(frozen=True)
class CveLookupView:
    matched: bool
    match_source: str  # "cve_id" | "title" | "none"
    cve_id: str | None = None
    cvss_score: float | None = None
    cvss_vector: str | None = None
    severity: str | None = None
    cwe_id: str | None = None
    description: str | None = None
    nvd_url: str | None = None


@dataclass(frozen=True)
class ImportResult:
    report_id: uuid.UUID
    created: int
    resurfaced: int
    updated: int
    unmatched: int
    definitions: int
    status: str = "parsed"
    parse_error: str | None = None


@dataclass(frozen=True)
class SlaPolicyView:
    severity: str
    days: int | None


@dataclass(frozen=True)
class RemediationPlanView:
    id: uuid.UUID | None  # None for a non-persisted preview
    instance_id: uuid.UUID
    fix_type: str
    title: str
    summary: str
    fix_artifact: str
    rationale: str
    rollback_plan: str | None
    source: str
    status: str  # incl. "preview" for a non-persisted draft
    triggers: list[str]
    risk_score_before: float | None
    risk_score_after: float | None
    change_window_start: datetime | None
    change_window_end: datetime | None
    approved_by_name: str | None
    approved_at: datetime | None
    applied_at: datetime | None
    execution_log: str | None
    verification_evidence: str | None
    verified_by_name: str | None
    verified_at: datetime | None
    failure_reason: str | None
    cancelled_reason: str | None
    cancelled_at: datetime | None


@dataclass(frozen=True)
class ReportView:
    id: uuid.UUID
    name: str
    report_type: str
    scan_tool: str | None
    status: str
    parse_error: str | None
    file_name: str | None
    has_file: bool
    total_count: int
    critical_count: int
    high_count: int
    uploaded_by_name: str | None
    created_at: datetime


# -- import row --------------------------------------------------------------


@dataclass(frozen=True)
class FindingRow:
    """One parsed finding from a manual add or a CSV row."""

    title: str
    severity: str
    asset_id: uuid.UUID | None = None
    asset_match: str | None = None  # name/hostname to resolve when no id
    cve_id: str | None = None
    description: str | None = None
    cvss_score: float | None = None
    cvss_vector: str | None = None
    cwe_id: str | None = None
    recommendation: str | None = None
    component: str | None = None
    port: int | None = None
    affected_url: str | None = None
    evidence: str | None = None
    reproduction_steps: str | None = None
    source: str = "manual"


class VulnerabilityService:
    def __init__(self, audit: AuditService | None = None, store: ObjectStore | None = None) -> None:
        self._audit = audit or audit_service
        self._store = store or get_object_store()

    # -- cross-module resolution (rule 4) ------------------------------------

    async def _asset_refs(
        self, session: AsyncSession, tenant_id: uuid.UUID, asset_ids: Sequence[uuid.UUID] | None
    ) -> dict[uuid.UUID, Any]:
        from verity.modules.assets.service import asset_service  # noqa: PLC0415

        return await asset_service.asset_refs(session, tenant_id=tenant_id, asset_ids=asset_ids)

    async def _member_names(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        from verity.modules.iam.service import iam_service  # noqa: PLC0415

        members = await iam_service.list_members(session, tenant_id=tenant_id)
        return {m.membership_id: m.full_name for m in members}

    def _notify(self) -> NotificationService:
        from verity.modules.notifications.service import notification_service  # noqa: PLC0415

        return notification_service

    # -- SLA policy ----------------------------------------------------------

    async def _sla_days(self, session: AsyncSession, tenant_id: uuid.UUID) -> dict[str, int | None]:
        rows = (
            await session.execute(select(VulnSlaPolicy).where(VulnSlaPolicy.tenant_id == tenant_id))
        ).scalars()
        days: dict[str, int | None] = dict(DEFAULT_SLA_DAYS)
        for r in rows:
            days[r.severity] = r.days
        return days

    async def sla_policy(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[SlaPolicyView]:
        days = await self._sla_days(session, tenant_id)
        return [SlaPolicyView(severity=s, days=days.get(s)) for s in SEVERITIES]

    async def set_sla_policy(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        severity: str,
        days: int | None,
    ) -> list[SlaPolicyView]:
        if severity not in SEVERITIES:
            raise InvalidInput(
                "Choose a severity of critical, high, medium, low or info to set an SLA for.",
                detail=f"unknown severity {severity!r}",
            )
        row = (
            await session.execute(
                select(VulnSlaPolicy).where(
                    VulnSlaPolicy.tenant_id == tenant_id, VulnSlaPolicy.severity == severity
                )
            )
        ).scalar_one_or_none()
        if days is None:
            if row is not None:
                await session.delete(row)
        elif row is None:
            session.add(
                VulnSlaPolicy(id=uuid7(), tenant_id=tenant_id, severity=severity, days=days)
            )
        else:
            row.days = days
        await session.flush()
        await self._audit.record(
            session,
            action="update",
            object_type="vuln_sla_policy",
            object_id=tenant_id,
            actor=actor,
            tenant_id=tenant_id,
            after={"severity": severity, "days": days},
        )
        return await self.sla_policy(session, tenant_id=tenant_id)

    def _sla_due(
        self, severity: str, days: dict[str, int | None], anchor: datetime
    ) -> datetime | None:
        d = days.get(severity)
        return anchor + timedelta(days=d) if d is not None else None

    # -- reads ---------------------------------------------------------------

    async def _definitions_by_id(
        self, session: AsyncSession, tenant_id: uuid.UUID, ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, VulnDefinition]:
        if not ids:
            return {}
        rows = (
            await session.execute(
                select(VulnDefinition).where(
                    VulnDefinition.tenant_id == tenant_id, VulnDefinition.id.in_(list(ids))
                )
            )
        ).scalars()
        return {d.id: d for d in rows}

    def _row(  # noqa: PLR0913, PLR0917
        self,
        inst: VulnInstance,
        defn: VulnDefinition,
        asset_name: str,
        asset_host: str | None,
        owner_name: str | None,
        now: datetime,
    ) -> InstanceView:
        overdue = bool(
            inst.state in OPEN_STATES and inst.sla_due_at is not None and inst.sla_due_at < now
        )
        return InstanceView(
            id=inst.id,
            cve_id=defn.cve_id,
            title=defn.title,
            severity=defn.severity,
            cvss_score=defn.cvss_score,
            cvss_vector=defn.cvss_vector,
            cwe_id=defn.cwe_id,
            state=inst.state,
            risk_score=inst.risk_score,
            risk_reason=inst.risk_reason,
            priority_band=priority_band(inst.risk_score),
            kev_flag=defn.kev_flag,
            epss_score=defn.epss_score,
            epss_percentile=defn.epss_percentile,
            public_exploit_count=defn.public_exploit_count,
            patch_available=defn.patch_available,
            asset_id=inst.asset_id,
            asset_name=asset_name,
            asset_host=asset_host,
            locator=inst.locator,
            owner_membership_id=inst.owner_membership_id,
            owner_name=owner_name,
            sla_due_at=inst.sla_due_at,
            overdue=overdue,
            escalation_level=inst.escalation_level,
            first_detected_at=inst.first_detected_at,
            last_seen_at=inst.last_seen_at,
            detected_by=list(inst.detected_by or []),
        )

    async def list_instances(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        state: str = "open",
        severity: str | None = None,
        asset_id: uuid.UUID | None = None,
        kev_only: bool = False,
        overdue_only: bool = False,
        search: str | None = None,
    ) -> list[InstanceView]:
        stmt = (
            select(VulnInstance, VulnDefinition)
            .join(VulnDefinition, VulnDefinition.id == VulnInstance.definition_id)
            .where(VulnInstance.tenant_id == tenant_id)
        )
        if state == "open":
            stmt = stmt.where(VulnInstance.state.in_(list(OPEN_STATES)))
        elif state == "closed":
            stmt = stmt.where(VulnInstance.state.in_(list(CLOSED_STATES)))
        elif state and state != "all":
            stmt = stmt.where(VulnInstance.state == state)
        if severity and severity != "all":
            stmt = stmt.where(VulnDefinition.severity == severity)
        if asset_id is not None:
            stmt = stmt.where(VulnInstance.asset_id == asset_id)
        if kev_only:
            stmt = stmt.where(VulnDefinition.kev_flag.is_(True))
        if search:
            like = f"%{search.lower()}%"
            stmt = stmt.where(
                func.lower(VulnDefinition.title).like(like)
                | func.lower(func.coalesce(VulnDefinition.cve_id, "")).like(like)
            )

        rows = list((await session.execute(stmt)).all())
        now = datetime.now(UTC)
        asset_ids = {inst.asset_id for inst, _ in rows}
        refs = await self._asset_refs(session, tenant_id, list(asset_ids))
        names = await self._member_names(session, tenant_id)

        views: list[InstanceView] = []
        for inst, defn in rows:
            ref = refs.get(inst.asset_id)
            view = self._row(
                inst,
                defn,
                ref.name if ref else "(unknown asset)",
                ref.host if ref else None,
                names.get(inst.owner_membership_id) if inst.owner_membership_id else None,
                now,
            )
            if overdue_only and not view.overdue:
                continue
            views.append(view)

        views.sort(key=self._sort_key)
        return views

    @staticmethod
    def _sort_key(v: InstanceView) -> tuple[float, int]:
        # risk desc first (None last), then severity rank.
        return (-(v.risk_score or -1.0), _SEVERITY_RANK.get(v.severity, 9))

    async def get_instance(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, instance_id: uuid.UUID
    ) -> InstanceDetailView:
        inst = await self._load_instance(session, tenant_id, instance_id)
        defn = await session.get(VulnDefinition, inst.definition_id)
        if defn is None:
            raise NotFound(_DEFINITION_GONE, detail=f"definition for instance {instance_id}")
        now = datetime.now(UTC)
        refs = await self._asset_refs(session, tenant_id, [inst.asset_id])
        names = await self._member_names(session, tenant_id)
        ref = refs.get(inst.asset_id)
        base = self._row(
            inst,
            defn,
            ref.name if ref else "(unknown asset)",
            ref.host if ref else None,
            names.get(inst.owner_membership_id) if inst.owner_membership_id else None,
            now,
        )
        trs = list(
            (
                await session.execute(
                    select(VulnTransition)
                    .where(
                        VulnTransition.tenant_id == tenant_id,
                        VulnTransition.instance_id == inst.id,
                    )
                    .order_by(VulnTransition.occurred_at.desc())
                )
            ).scalars()
        )
        transitions = [
            TransitionView(
                from_state=t.from_state,
                to_state=t.to_state,
                actor_name=(
                    names.get(t.actor_membership_id, "Unknown")
                    if t.actor_membership_id
                    else "Scanner"
                ),
                note=t.note,
                occurred_at=t.occurred_at,
            )
            for t in trs
        ]
        affected = await self._affected_assets(session, tenant_id, inst)
        targets = await self._assignment_targets(session, tenant_id, inst.id)
        return InstanceDetailView(
            **{f: getattr(base, f) for f in base.__dataclass_fields__},
            custom_fields=dict(inst.custom_fields or {}),
            definition_id=defn.id,
            description=defn.description,
            recommendation=defn.recommendation,
            kev_ransomware=defn.kev_ransomware,
            exploit_refs=list(defn.exploit_refs or []),
            enriched_at=defn.enriched_at,
            fixed_versions=defn.fixed_versions,
            advisory_url=defn.advisory_url,
            patch_source=defn.patch_source,
            component=inst.component,
            port=inst.port,
            affected_url=inst.affected_url,
            evidence=inst.evidence,
            reproduction_steps=inst.reproduction_steps,
            resolution_notes=inst.resolution_notes,
            fixed_verified=inst.fixed_verified,
            resurfaced_count=inst.resurfaced_count,
            accepted_reason=inst.accepted_reason,
            accepted_expires_at=inst.accepted_expires_at,
            compensating_controls=inst.compensating_controls,
            escalated_at=inst.escalated_at,
            false_positive_reason=inst.false_positive_reason,
            report_id=inst.report_id,
            kev_added_at=defn.kev_added_at,
            kev_vendor=defn.kev_vendor,
            kev_product=defn.kev_product,
            kev_required_action=defn.kev_required_action,
            kev_due_at=defn.kev_due_at,
            references=build_references(
                cve_id=defn.cve_id,
                kev_flag=defn.kev_flag,
                epss_score=defn.epss_score,
                public_exploit_count=defn.public_exploit_count,
                exploit_refs=list(defn.exploit_refs or []),
                advisory_url=defn.advisory_url,
                patch_source=defn.patch_source,
            ),
            risk_breakdown=compute_breakdown(
                severity=defn.severity,
                cvss_score=defn.cvss_score,
                epss_score=defn.epss_score,
                kev_flag=defn.kev_flag,
                public_exploit_count=defn.public_exploit_count,
                asset=AssetRisk(
                    tier=getattr(ref, "tier", None),
                    internet_facing=bool(getattr(ref, "internet_facing", False)),
                    customer_facing=bool(getattr(ref, "customer_facing", False)),
                ),
            ),
            exception=await self._current_exception(session, tenant_id, inst.id),
            asset_criticality=(
                AssetCriticalityView(
                    tier=ref.tier,
                    internet_facing=ref.internet_facing,
                    customer_facing=ref.customer_facing,
                    confidentiality=getattr(ref, "confidentiality", None),
                    integrity=getattr(ref, "integrity", None),
                    availability=getattr(ref, "availability", None),
                )
                if ref is not None
                else None
            ),
            transitions=transitions,
            affected_assets=affected,
            assignment_targets=targets,
        )

    async def _affected_assets(
        self, session: AsyncSession, tenant_id: uuid.UUID, inst: VulnInstance
    ) -> list[AffectedAssetView]:
        """The other assets carrying the same definition (CVE/finding)."""
        rows = list(
            (
                await session.execute(
                    select(VulnInstance)
                    .where(
                        VulnInstance.tenant_id == tenant_id,
                        VulnInstance.definition_id == inst.definition_id,
                        VulnInstance.id != inst.id,
                    )
                    .order_by(VulnInstance.risk_score.desc().nullslast())
                )
            ).scalars()
        )
        if not rows:
            return []
        refs = await self._asset_refs(session, tenant_id, [r.asset_id for r in rows])
        return [
            AffectedAssetView(
                instance_id=r.id,
                asset_id=r.asset_id,
                asset_name=refs[r.asset_id].name if r.asset_id in refs else "(unknown asset)",
                asset_host=refs[r.asset_id].host if r.asset_id in refs else None,
                state=r.state,
                risk_score=r.risk_score,
                priority_band=priority_band(r.risk_score),
            )
            for r in rows
        ]

    async def kpis(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> KpiView:
        rows = list(
            (
                await session.execute(
                    select(
                        VulnInstance.state,
                        VulnInstance.sla_due_at,
                        VulnInstance.risk_score,
                        VulnDefinition.severity,
                        VulnDefinition.kev_flag,
                    )
                    .join(VulnDefinition, VulnDefinition.id == VulnInstance.definition_id)
                    .where(VulnInstance.tenant_id == tenant_id)
                )
            ).all()
        )
        now = datetime.now(UTC)
        due_soon_cutoff = now + timedelta(days=7)
        by_sev = dict.fromkeys(SEVERITIES, 0)
        by_priority = dict.fromkeys(PRIORITY_BANDS, 0)
        posture = {"on_track": 0, "due_soon": 0, "overdue": 0}
        open_total = overdue = kev_open = accepted = 0
        for state, sla_due, risk, severity, kev in rows:
            if state == "accepted":
                accepted += 1
            if state in OPEN_STATES:
                open_total += 1
                by_sev[severity] = by_sev.get(severity, 0) + 1
                by_priority[priority_band(risk)] = by_priority.get(priority_band(risk), 0) + 1
                if sla_due is None:
                    posture["on_track"] += 1
                elif sla_due < now:
                    posture["overdue"] += 1
                    overdue += 1
                elif sla_due <= due_soon_cutoff:
                    posture["due_soon"] += 1
                else:
                    posture["on_track"] += 1
                if kev:
                    kev_open += 1
        return KpiView(
            open_total=open_total,
            open_by_severity=by_sev,
            open_by_priority=by_priority,
            sla_posture=posture,
            overdue=overdue,
            kev_open=kev_open,
            accepted=accepted,
        )

    async def throughput(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, window_days: int = 30
    ) -> ThroughputView:
        """Remediation throughput (spec 131): opened vs closed in the window, and
        mean time-to-remediate per severity from first_detected -> fixed_at."""
        now = datetime.now(UTC)
        since = now - timedelta(days=window_days)
        rows = list(
            (
                await session.execute(
                    select(
                        VulnInstance.state,
                        VulnInstance.first_detected_at,
                        VulnInstance.fixed_at,
                        VulnDefinition.severity,
                    )
                    .join(VulnDefinition, VulnDefinition.id == VulnInstance.definition_id)
                    .where(VulnInstance.tenant_id == tenant_id)
                )
            ).all()
        )
        opened = closed = 0
        ttr_by_sev: dict[str, list[float]] = {s: [] for s in SEVERITIES}
        for state, first_detected, fixed_at, severity in rows:
            if first_detected is not None and first_detected >= since:
                opened += 1
            if state == "fixed" and fixed_at is not None and fixed_at >= since:
                closed += 1
                if first_detected is not None:
                    ttr_by_sev[severity].append((fixed_at - first_detected).total_seconds() / 86400)
        mttr = {s: (round(_mean(v), 1) if v else None) for s, v in ttr_by_sev.items()}
        all_ttr = [d for v in ttr_by_sev.values() for d in v]
        return ThroughputView(
            closed_30d=closed,
            opened_30d=opened,
            mttr_days_by_severity=mttr,
            median_mttr_days=round(_median(all_ttr), 1) if all_ttr else None,
        )

    # -- writes: import + manual add -----------------------------------------

    async def import_findings(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        rows: Sequence[FindingRow],
        report_name: str,
        report_type: str = "vulnerability_scan",
        scan_tool: str | None = None,
    ) -> ImportResult:
        """Ingest already-parsed rows under a new report row (manual add / tests)."""
        report = VulnReport(
            id=uuid7(),
            tenant_id=tenant_id,
            name=report_name,
            report_type=report_type,
            scan_tool=scan_tool,
            status="parsing",
            uploaded_by_membership_id=_membership(actor),
        )
        session.add(report)
        await session.flush()
        result = await self._ingest(
            session, tenant_id=tenant_id, actor=actor, report=report, rows=rows
        )
        report.status = "parsed"
        await session.flush()
        return result

    async def import_file(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        file_data: bytes,
        file_name: str,
        report_name: str,
        report_type: str = "vulnerability_scan",
        scan_tool: str | None = None,
    ) -> ImportResult:
        """Store the uploaded report and parse it into findings. A parse failure is
        recorded on the report (status='failed', re-runnable), never a lost upload —
        the auditor requirement is to walk from a finding back to its source file."""
        stored = self._store.put(tenant_id, file_name, file_data)
        report = VulnReport(
            id=uuid7(),
            tenant_id=tenant_id,
            name=report_name,
            report_type=report_type,
            scan_tool=scan_tool,
            status="parsing",
            file_key=stored.key,
            file_name=file_name,
            file_type=_file_ext(file_name),
            uploaded_by_membership_id=_membership(actor),
        )
        session.add(report)
        await session.flush()
        try:
            rows = parse_file(file_name, file_data)
        except Exception as exc:
            report.status = "failed"
            report.parse_error = str(exc)[:1000]
            await session.flush()
            await self._audit.record(
                session,
                action="create",
                object_type="vuln_report",
                object_id=report.id,
                actor=actor,
                tenant_id=tenant_id,
                after={"name": report_name, "status": "failed"},
            )
            return ImportResult(
                report_id=report.id,
                created=0,
                resurfaced=0,
                updated=0,
                unmatched=0,
                definitions=0,
                status="failed",
                parse_error=report.parse_error,
            )
        result = await self._ingest(
            session, tenant_id=tenant_id, actor=actor, report=report, rows=rows
        )
        report.status = "parsed"
        await session.flush()
        return result

    async def _ingest(  # noqa: PLR0915
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        report: VulnReport,
        rows: Sequence[FindingRow],
    ) -> ImportResult:
        # Resolve asset matches once.
        refs_by_id = await self._asset_refs(session, tenant_id, None)
        by_name = {r.name.lower(): r for r in refs_by_id.values()}
        days = await self._sla_days(session, tenant_id)
        now = datetime.now(UTC)

        created = resurfaced = updated = unmatched = 0
        counts = dict.fromkeys(SEVERITIES, 0)
        touched_defs: dict[uuid.UUID, VulnDefinition] = {}
        touched_instances: list[tuple[VulnInstance, VulnDefinition, Any]] = []

        for row in rows:
            ref = None
            if row.asset_id is not None:
                ref = refs_by_id.get(row.asset_id)
            elif row.asset_match:
                ref = by_name.get(row.asset_match.strip().lower())
            if ref is None:
                unmatched += 1
                continue

            defn = await self._upsert_definition(session, tenant_id, row)
            touched_defs[defn.id] = defn
            counts[defn.severity] = counts.get(defn.severity, 0) + 1

            locator = _locator(row)
            inst = (
                await session.execute(
                    select(VulnInstance).where(
                        VulnInstance.tenant_id == tenant_id,
                        VulnInstance.asset_id == ref.id,
                        VulnInstance.definition_id == defn.id,
                        VulnInstance.locator == locator,
                    )
                )
            ).scalar_one_or_none()

            if inst is None:
                inst = VulnInstance(
                    id=uuid7(),
                    tenant_id=tenant_id,
                    definition_id=defn.id,
                    asset_id=ref.id,
                    report_id=report.id,
                    locator=locator,
                    component=row.component,
                    port=row.port,
                    affected_url=row.affected_url,
                    evidence=row.evidence,
                    reproduction_steps=row.reproduction_steps,
                    state="new",
                    owner_membership_id=ref.primary_owner_membership_id,
                    first_detected_at=now,
                    last_seen_at=now,
                    sla_due_at=self._sla_due(defn.severity, days, now),
                    detected_by=[row.source],
                    source=row.source,
                )
                session.add(inst)
                await session.flush()
                self._append_transition(session, tenant_id, inst.id, None, "new", None, now)
                created += 1
            else:
                inst.last_seen_at = now
                if row.source not in (inst.detected_by or []):
                    inst.detected_by = [*(inst.detected_by or []), row.source]
                if inst.state in CLOSED_STATES and inst.state == "fixed":
                    # Reappeared after a fix -> resurfaced, not a duplicate.
                    before = AuditService.snapshot(inst, fields=_INSTANCE_SNAPSHOT)
                    inst.state = "resurfaced"
                    inst.resurfaced_count += 1
                    inst.fixed_verified = False
                    inst.sla_due_at = self._sla_due(defn.severity, days, now)
                    self._append_transition(
                        session,
                        tenant_id,
                        inst.id,
                        "fixed",
                        "resurfaced",
                        "Scanner reported it again",
                        now,
                    )
                    await self._audit.record(
                        session,
                        action="transition",
                        object_type="vuln_instance",
                        object_id=inst.id,
                        actor=actor,
                        tenant_id=tenant_id,
                        before=before,
                        after=AuditService.snapshot(inst, fields=_INSTANCE_SNAPSHOT),
                    )
                    resurfaced += 1
                else:
                    updated += 1
            touched_instances.append((inst, defn, ref))

        # Enrich the definitions we touched (batch), then recompute risk on all
        # affected instances. Best-effort: enrichment failure leaves scores CVSS-only.
        await self._enrich_and_score(session, list(touched_defs.values()), touched_instances)

        report.total_count = created + resurfaced + updated
        report.critical_count = counts.get("critical", 0)
        report.high_count = counts.get("high", 0)
        report.medium_count = counts.get("medium", 0)
        report.low_count = counts.get("low", 0)
        report.info_count = counts.get("info", 0)
        await session.flush()

        await self._audit.record(
            session,
            action="create",
            object_type="vuln_report",
            object_id=report.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"name": report.name, "created": created, "resurfaced": resurfaced},
        )
        return ImportResult(
            report_id=report.id,
            created=created,
            resurfaced=resurfaced,
            updated=updated,
            unmatched=unmatched,
            definitions=len(touched_defs),
        )

    # -- the tenant's own fields ---------------------------------------------

    async def custom_fields(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, include_archived: bool = False
    ) -> list[FieldDefinition]:
        return await custom_field_service.definitions(
            session,
            tenant_id=tenant_id,
            object_type="vulnerability",
            include_archived=include_archived,
        )

    async def save_custom_field(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        field_id: uuid.UUID | None,
        data: FieldInput,
    ) -> FieldDefinition:
        """Define or reword an extra field. The audit row belongs to this module,
        not to the primitive that stores the definition."""
        if field_id is None:
            view = await custom_field_service.create(
                session, tenant_id=tenant_id, object_type="vulnerability", data=data
            )
        else:
            view = await custom_field_service.update(
                session, tenant_id=tenant_id, field_id=field_id, data=data
            )
        await self._audit.record(
            session,
            action="create" if field_id is None else "update",
            object_type="vulnerability_custom_field",
            object_id=view.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"key": view.key, "label": view.label, "field_type": view.field_type},
        )
        await session.flush()
        return view

    async def set_custom_field_archived(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        field_id: uuid.UUID,
        archived: bool,
    ) -> FieldDefinition:
        view = await custom_field_service.set_archived(
            session, tenant_id=tenant_id, field_id=field_id, archived=archived
        )
        await self._audit.record(
            session,
            action="update",
            object_type="vulnerability_custom_field",
            object_id=view.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"key": view.key, "archived": archived},
        )
        await session.flush()
        return view

    async def set_instance_custom_fields(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        instance_id: uuid.UUID,
        values: dict[str, Any],
    ) -> InstanceDetailView:
        """Write the tenant's own fields on one finding.

        Scanners fill the rest of a finding; these are what a person adds that no
        scanner can know — a change ticket, a business owner's sign-off date.
        """
        instance = await session.get(VulnInstance, instance_id, populate_existing=True)
        if instance is None or instance.tenant_id != tenant_id:
            raise NotFound("That finding no longer exists.", detail=f"vuln instance {instance_id}")
        before = dict(instance.custom_fields or {})
        instance.custom_fields = await custom_field_service.clean(
            session,
            tenant_id=tenant_id,
            object_type="vulnerability",
            values=values,
            previous=before,
        )
        await self._audit.record(
            session,
            action="update",
            object_type="vulnerability",
            object_id=instance.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"custom_fields": before},
            after={"custom_fields": instance.custom_fields},
        )
        await session.flush()
        return await self.get_instance(session, tenant_id=tenant_id, instance_id=instance.id)

    async def add_finding(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        row: FindingRow,
    ) -> InstanceDetailView:
        if row.asset_id is None:
            raise InvalidInput(
                "Choose the asset this finding affects before adding it.",
                detail="an asset is required",
            )
        result = await self.import_findings(
            session,
            tenant_id=tenant_id,
            actor=actor,
            rows=[row],
            report_name=f"Manual: {row.title}"[:200],
            report_type="penetration_test",
            scan_tool="manual",
        )
        if result.created == 0 and result.resurfaced == 0 and result.updated == 0:
            raise InvalidInput(
                "We could not match that asset, so the finding was not added. "
                "Pick the asset from the list and try again.",
                detail="the asset could not be matched",
            )
        # Return the instance just written (asset+definition+locator is unique).
        defn = (
            await session.execute(
                select(VulnDefinition).where(
                    VulnDefinition.tenant_id == tenant_id,
                    VulnDefinition.definition_key == _definition_key(row),
                )
            )
        ).scalar_one()
        inst = (
            await session.execute(
                select(VulnInstance).where(
                    VulnInstance.tenant_id == tenant_id,
                    VulnInstance.asset_id == row.asset_id,
                    VulnInstance.definition_id == defn.id,
                    VulnInstance.locator == _locator(row),
                )
            )
        ).scalar_one()
        return await self.get_instance(session, tenant_id=tenant_id, instance_id=inst.id)

    async def lookup_cve(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, title: str, cve_id: str | None = None
    ) -> CveLookupView:
        """Resolve a CVE from an explicit id or a CVE mentioned in the title, then
        pull its NVD record (CVSS, CWE, description) to autofill the manual-add form.
        Best-effort: a resolved CVE with no NVD data still returns matched=True."""
        cve: str | None = None
        source = "none"
        if enrichment.is_cve(cve_id):
            cve, source = cve_id.strip().upper(), "cve_id"  # type: ignore[union-attr]
        else:
            match = _CVE_IN_TITLE.search(title or "")
            if match:
                cve, source = match.group(0).upper(), "title"
        if cve is None:
            return CveLookupView(matched=False, match_source="none")
        url = f"https://nvd.nist.gov/vuln/detail/{cve}"
        # If we've already seen this CVE in the tenant, use its stored intel — no
        # NVD round trip (and no rate-limit exposure) for a known finding.
        known = (
            await session.execute(
                select(VulnDefinition).where(
                    VulnDefinition.tenant_id == tenant_id, VulnDefinition.cve_id == cve
                )
            )
        ).scalar_one_or_none()
        if known is not None:
            return CveLookupView(
                matched=True,
                match_source=source,
                cve_id=cve,
                cvss_score=known.cvss_score,
                cvss_vector=known.cvss_vector,
                severity=known.severity,
                cwe_id=known.cwe_id,
                description=known.description,
                nvd_url=known.advisory_url or url,
            )
        nvd = await enrichment.fetch_nvd(cve)
        if nvd is None:
            return CveLookupView(matched=True, match_source=source, cve_id=cve, nvd_url=url)
        return CveLookupView(
            matched=True,
            match_source=source,
            cve_id=cve,
            cvss_score=nvd.cvss_score,
            cvss_vector=nvd.cvss_vector,
            severity=_severity_from_cvss(nvd.cvss_score),
            cwe_id=nvd.cwe_id,
            description=nvd.description,
            nvd_url=url,
        )

    # -- reports (upload provenance + reparse) -------------------------------

    async def list_reports(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[ReportView]:
        rows = list(
            (
                await session.execute(
                    select(VulnReport)
                    .where(VulnReport.tenant_id == tenant_id)
                    .order_by(VulnReport.created_at.desc())
                )
            ).scalars()
        )
        names = await self._member_names(session, tenant_id)
        return [
            ReportView(
                id=r.id,
                name=r.name,
                report_type=r.report_type,
                scan_tool=r.scan_tool,
                status=r.status,
                parse_error=r.parse_error,
                file_name=r.file_name,
                has_file=r.file_key is not None,
                total_count=r.total_count,
                critical_count=r.critical_count,
                high_count=r.high_count,
                uploaded_by_name=(
                    names.get(r.uploaded_by_membership_id) if r.uploaded_by_membership_id else None
                ),
                created_at=r.created_at,
            )
            for r in rows
        ]

    async def report_file(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, report_id: uuid.UUID
    ) -> tuple[bytes, str, str]:
        """The stored report file (bytes, filename, content-type) for download."""
        report = await session.get(VulnReport, report_id)
        if report is None or report.tenant_id != tenant_id:
            raise NotFound(_REPORT_GONE, detail=f"report {report_id}")
        if report.file_key is None:
            raise NotFound(
                "There is no file saved for this report, so there is nothing to download.",
                detail="this report has no stored file",
            )
        data = self._store.open(tenant_id, report.file_key)
        return data, report.file_name or "report", _content_type(report.file_name)

    async def reparse_report(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor, report_id: uuid.UUID
    ) -> ImportResult:
        """Re-run parsing on a report's stored file (spec: a failed parse is
        re-runnable). Dedup makes a successful re-run idempotent."""
        report = await session.get(VulnReport, report_id)
        if report is None or report.tenant_id != tenant_id:
            raise NotFound(_REPORT_GONE, detail=f"report {report_id}")
        if report.file_key is None:
            raise InvalidInput(
                "There is no file saved for this report, so it cannot be re-run. "
                "Upload the scan file again.",
                detail="this report has no stored file to reparse",
            )
        data = self._store.open(tenant_id, report.file_key)
        report.status = "parsing"
        report.parse_error = None
        await session.flush()
        try:
            rows = parse_file(report.file_name or "report.csv", data)
        except Exception as exc:
            report.status = "failed"
            report.parse_error = str(exc)[:1000]
            await session.flush()
            await self._audit.record(
                session,
                action="update",
                object_type="vuln_report",
                object_id=report.id,
                actor=actor,
                tenant_id=tenant_id,
                after={"status": "failed", "reparse": True},
            )
            return ImportResult(
                report_id=report.id,
                created=0,
                resurfaced=0,
                updated=0,
                unmatched=0,
                definitions=0,
                status="failed",
                parse_error=report.parse_error,
            )
        result = await self._ingest(
            session, tenant_id=tenant_id, actor=actor, report=report, rows=rows
        )
        report.status = "parsed"
        await session.flush()
        return result

    # -- cross-module: asset linkage (spec 123, 134) -------------------------

    async def open_counts_by_asset(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, int]:
        """Open-instance count per asset — for the assets module's vuln_count."""
        rows = (
            await session.execute(
                select(VulnInstance.asset_id, func.count())
                .where(
                    VulnInstance.tenant_id == tenant_id,
                    VulnInstance.state.in_(list(OPEN_STATES)),
                )
                .group_by(VulnInstance.asset_id)
            )
        ).all()
        return {asset_id: count for asset_id, count in rows}  # noqa: C416 — Row unpack

    async def close_open_for_asset(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        asset_id: uuid.UUID,
        reason: str,
    ) -> int:
        """Close an asset's open findings when it is decommissioned (spec 123):
        retiring the host removes the exposure, so its open instances are verified
        fixed with a recorded reason. Returns how many were closed."""
        insts = list(
            (
                await session.execute(
                    select(VulnInstance).where(
                        VulnInstance.tenant_id == tenant_id,
                        VulnInstance.asset_id == asset_id,
                        VulnInstance.state.in_(list(OPEN_STATES)),
                    )
                )
            ).scalars()
        )
        now = datetime.now(UTC)
        note = f"Asset decommissioned: {reason}"[:500]
        for inst in insts:
            before = AuditService.snapshot(inst, fields=_INSTANCE_SNAPSHOT)
            from_state = inst.state
            inst.state = "fixed"
            inst.fixed_at = now
            inst.fixed_verified = True
            inst.resolution_notes = note
            self._append_transition(
                session,
                tenant_id,
                inst.id,
                from_state,
                "fixed",
                note,
                now,
                actor_membership_id=_membership(actor),
            )
            await self._audit.record(
                session,
                action="transition",
                object_type="vuln_instance",
                object_id=inst.id,
                actor=actor,
                tenant_id=tenant_id,
                before=before,
                after=AuditService.snapshot(inst, fields=_INSTANCE_SNAPSHOT),
            )
        await session.flush()
        return len(insts)

    # -- on-demand re-enrich + asset link/move (spec: prioritise on all params) ---

    async def reenrich_instance(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor, instance_id: uuid.UUID
    ) -> InstanceDetailView:
        """Refresh EPSS/KEV/exploit/patch for this finding's definition and re-score
        it on demand (GRC-Tenant's per-finding enrich). Every instance of the same
        definition inherits the refreshed intel."""
        inst = await self._load_instance(session, tenant_id, instance_id)
        defn = await session.get(VulnDefinition, inst.definition_id)
        if defn is None:
            raise NotFound(_DEFINITION_GONE, detail=f"definition for instance {instance_id}")
        rows = list(
            (
                await session.execute(
                    select(VulnInstance).where(
                        VulnInstance.tenant_id == tenant_id,
                        VulnInstance.definition_id == defn.id,
                    )
                )
            ).scalars()
        )
        refs = await self._asset_refs(session, tenant_id, [r.asset_id for r in rows])
        triples = [(r, defn, refs.get(r.asset_id)) for r in rows]
        await self._enrich_and_score(
            session, [defn], triples, include_github=True, include_patch=True
        )
        await self._audit.record(
            session,
            action="update",
            object_type="vuln_instance",
            object_id=inst.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"reenriched": True},
        )
        return await self.get_instance(session, tenant_id=tenant_id, instance_id=inst.id)

    async def link_asset(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        instance_id: uuid.UUID,
        asset_id: uuid.UUID,
    ) -> InstanceDetailView:
        """Record that the same finding also affects another asset — a new instance
        of the same definition on that asset (Verity's take on GRC-Tenant's
        link-asset). Idempotent: returns the existing instance if already linked."""
        src = await self._load_instance(session, tenant_id, instance_id)
        defn = await session.get(VulnDefinition, src.definition_id)
        if defn is None:
            raise NotFound(_DEFINITION_GONE, detail=f"definition for instance {instance_id}")
        refs = await self._asset_refs(session, tenant_id, [asset_id])
        ref = refs.get(asset_id)
        if ref is None:
            raise NotFound(_ASSET_GONE, detail=f"asset {asset_id}")
        existing = (
            await session.execute(
                select(VulnInstance).where(
                    VulnInstance.tenant_id == tenant_id,
                    VulnInstance.asset_id == asset_id,
                    VulnInstance.definition_id == defn.id,
                    VulnInstance.locator == src.locator,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return await self.get_instance(session, tenant_id=tenant_id, instance_id=existing.id)
        now = datetime.now(UTC)
        days = await self._sla_days(session, tenant_id)
        inst = VulnInstance(
            id=uuid7(),
            tenant_id=tenant_id,
            definition_id=defn.id,
            asset_id=asset_id,
            locator=src.locator,
            component=src.component,
            port=src.port,
            affected_url=src.affected_url,
            state="new",
            owner_membership_id=ref.primary_owner_membership_id,
            first_detected_at=now,
            last_seen_at=now,
            sla_due_at=self._sla_due(defn.severity, days, now),
            detected_by=["manual-link"],
            source="manual",
        )
        session.add(inst)
        await session.flush()
        self._score_instances([(inst, defn, ref)])
        self._append_transition(
            session,
            tenant_id,
            inst.id,
            None,
            "new",
            "Linked to asset",
            now,
            actor_membership_id=_membership(actor),
        )
        await session.flush()
        await self._audit.record(
            session,
            action="create",
            object_type="vuln_instance",
            object_id=inst.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"linked_asset": str(asset_id)},
        )
        return await self.get_instance(session, tenant_id=tenant_id, instance_id=inst.id)

    async def move_asset(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        instance_id: uuid.UUID,
        asset_id: uuid.UUID,
    ) -> InstanceDetailView:
        """Re-point a mis-attached finding to the correct asset (re-inherits owner,
        re-scores). Never a delete — the finding is preserved (rule 6)."""
        inst = await self._load_instance(session, tenant_id, instance_id)
        if inst.asset_id == asset_id:
            raise Conflict(
                "This finding is already recorded against that asset. "
                "Choose a different asset to move it to.",
                detail="already on that asset",
            )
        clash = (
            await session.execute(
                select(VulnInstance.id).where(
                    VulnInstance.tenant_id == tenant_id,
                    VulnInstance.asset_id == asset_id,
                    VulnInstance.definition_id == inst.definition_id,
                    VulnInstance.locator == inst.locator,
                    VulnInstance.id != inst.id,
                )
            )
        ).first()
        if clash is not None:
            raise Conflict(
                "That asset already has this finding, so it cannot be moved there. "
                "Close one of the two instead.",
                detail="that asset already has this finding",
            )
        refs = await self._asset_refs(session, tenant_id, [asset_id])
        ref = refs.get(asset_id)
        if ref is None:
            raise NotFound(_ASSET_GONE, detail=f"asset {asset_id}")
        defn = await session.get(VulnDefinition, inst.definition_id)
        if defn is None:
            raise NotFound(_DEFINITION_GONE, detail=f"definition for instance {instance_id}")
        before = AuditService.snapshot(inst, fields=_INSTANCE_SNAPSHOT)
        inst.asset_id = asset_id
        inst.owner_membership_id = ref.primary_owner_membership_id
        self._score_instances([(inst, defn, ref)])
        await session.flush()
        await self._audit.record(
            session,
            action="update",
            object_type="vuln_instance",
            object_id=inst.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after={
                **AuditService.snapshot(inst, fields=_INSTANCE_SNAPSHOT),
                "moved_to_asset": str(asset_id),
            },
        )
        return await self.get_instance(session, tenant_id=tenant_id, instance_id=inst.id)

    # -- remediation plans (spec: "their remediation") -----------------------

    async def _remediation_context(
        self, session: AsyncSession, tenant_id: uuid.UUID, inst: VulnInstance, defn: VulnDefinition
    ) -> remediation.RemediationContext:
        refs = await self._asset_refs(session, tenant_id, [inst.asset_id])
        ref = refs.get(inst.asset_id)
        now = datetime.now(UTC)
        overdue = bool(
            inst.state in OPEN_STATES and inst.sla_due_at is not None and inst.sla_due_at < now
        )
        return remediation.RemediationContext(
            cve_id=defn.cve_id,
            title=defn.title,
            severity=defn.severity,
            cvss_score=defn.cvss_score,
            recommendation=defn.recommendation,
            fixed_versions=defn.fixed_versions,
            patch_available=defn.patch_available,
            kev_flag=defn.kev_flag,
            epss_score=defn.epss_score,
            public_exploit_count=defn.public_exploit_count,
            risk_score=inst.risk_score,
            overdue=overdue,
            asset_name=ref.name if ref else "(unknown asset)",
            asset_tier=ref.tier if ref else None,
            internet_facing=ref.internet_facing if ref else False,
        )

    async def _get_plan(
        self, session: AsyncSession, tenant_id: uuid.UUID, instance_id: uuid.UUID
    ) -> VulnRemediationPlan | None:
        return (
            await session.execute(
                select(VulnRemediationPlan).where(
                    VulnRemediationPlan.tenant_id == tenant_id,
                    VulnRemediationPlan.instance_id == instance_id,
                )
            )
        ).scalar_one_or_none()

    async def _plan_view(
        self, session: AsyncSession, tenant_id: uuid.UUID, plan: VulnRemediationPlan
    ) -> RemediationPlanView:
        names = await self._member_names(session, tenant_id)
        return RemediationPlanView(
            id=plan.id,
            instance_id=plan.instance_id,
            fix_type=plan.fix_type,
            title=plan.title,
            summary=plan.summary,
            fix_artifact=plan.fix_artifact,
            rationale=plan.rationale,
            rollback_plan=plan.rollback_plan,
            source=plan.source,
            status=plan.status,
            triggers=list(plan.triggers or []),
            risk_score_before=plan.risk_score_before,
            risk_score_after=plan.risk_score_after,
            change_window_start=plan.change_window_start,
            change_window_end=plan.change_window_end,
            approved_by_name=_name_or(names, plan.approved_by_membership_id),
            approved_at=plan.approved_at,
            applied_at=plan.applied_at,
            execution_log=plan.execution_log,
            verification_evidence=plan.verification_evidence,
            verified_by_name=_name_or(names, plan.verified_by_membership_id),
            verified_at=plan.verified_at,
            failure_reason=plan.failure_reason,
            cancelled_reason=plan.cancelled_reason,
            cancelled_at=plan.cancelled_at,
        )

    async def remediation_plan(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, instance_id: uuid.UUID
    ) -> RemediationPlanView:
        """The stored plan, or a non-persisted heuristic PREVIEW (status='preview',
        id=None) when none has been generated yet. A read never writes."""
        inst = await self._load_instance(session, tenant_id, instance_id)
        plan = await self._get_plan(session, tenant_id, instance_id)
        if plan is not None:
            return await self._plan_view(session, tenant_id, plan)
        defn = await session.get(VulnDefinition, inst.definition_id)
        if defn is None:
            raise NotFound(_DEFINITION_GONE, detail=f"definition for instance {instance_id}")
        ctx = await self._remediation_context(session, tenant_id, inst, defn)
        draft = remediation.heuristic_plan(ctx)
        return RemediationPlanView(
            id=None,
            instance_id=inst.id,
            fix_type=draft.fix_type,
            title=draft.title,
            summary=draft.summary,
            fix_artifact=draft.fix_artifact,
            rationale=draft.rationale,
            rollback_plan=draft.rollback_plan,
            source=draft.source,
            status="preview",
            triggers=draft.triggers,
            risk_score_before=inst.risk_score,
            risk_score_after=None,
            change_window_start=None,
            change_window_end=None,
            approved_by_name=None,
            approved_at=None,
            applied_at=None,
            execution_log=None,
            verification_evidence=None,
            verified_by_name=None,
            verified_at=None,
            failure_reason=None,
            cancelled_reason=None,
            cancelled_at=None,
        )

    async def generate_remediation(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor, instance_id: uuid.UUID
    ) -> RemediationPlanView:
        """Generate (or regenerate) the plan — AI draft when keyed, else heuristic.
        Regenerating replaces the content and resets the lifecycle to recommended."""
        inst = await self._load_instance(session, tenant_id, instance_id)
        defn = await session.get(VulnDefinition, inst.definition_id)
        if defn is None:
            raise NotFound(_DEFINITION_GONE, detail=f"definition for instance {instance_id}")
        ctx = await self._remediation_context(session, tenant_id, inst, defn)
        draft = await remediation.generate_plan(ctx)
        plan = await self._get_plan(session, tenant_id, instance_id)
        if plan is None:
            plan = VulnRemediationPlan(id=uuid7(), tenant_id=tenant_id, instance_id=inst.id)
            session.add(plan)
        plan.fix_type = draft.fix_type
        plan.title = draft.title
        plan.summary = draft.summary
        plan.fix_artifact = draft.fix_artifact
        plan.rationale = draft.rationale
        plan.rollback_plan = draft.rollback_plan
        plan.source = draft.source
        plan.status = "recommended"
        plan.triggers = draft.triggers
        plan.risk_score_before = inst.risk_score
        plan.risk_score_after = None
        plan.approved_by_membership_id = None
        plan.approved_at = None
        plan.change_window_start = None
        plan.change_window_end = None
        plan.applied_at = None
        plan.execution_log = None
        plan.verified_by_membership_id = None
        plan.verified_at = None
        plan.verification_evidence = None
        plan.failure_reason = None
        plan.cancelled_reason = None
        plan.cancelled_at = None
        await session.flush()
        await self._audit.record(
            session,
            action="create",
            object_type="vuln_remediation_plan",
            object_id=plan.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"instance_id": str(inst.id), "source": draft.source},
        )
        return await self._plan_view(session, tenant_id, plan)

    async def _load_plan(
        self, session: AsyncSession, tenant_id: uuid.UUID, instance_id: uuid.UUID
    ) -> VulnRemediationPlan:
        plan = await self._get_plan(session, tenant_id, instance_id)
        if plan is None:
            raise NotFound(
                "There is no remediation plan for this finding yet. Generate one first.",
                detail="no remediation plan; generate one first",
            )
        return plan

    async def approve_remediation(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor, instance_id: uuid.UUID
    ) -> RemediationPlanView:
        inst = await self._load_instance(session, tenant_id, instance_id)
        plan = await self._load_plan(session, tenant_id, instance_id)
        if plan.status != "recommended":
            raise Conflict(
                f"This plan is already {plan.status}, so it cannot be approved again. "
                "Generate a new plan if you want to start over.",
                detail=f"a {plan.status} plan cannot be approved",
            )
        if inst.owner_membership_id is None:
            raise InvalidInput(
                "Assign an owner to this finding before you approve the remediation plan.",
                detail="assign an owner before approving the remediation",
            )
        now = datetime.now(UTC)
        plan.status = "approved"
        plan.approved_by_membership_id = _membership(actor)
        plan.approved_at = now
        plan.change_window_start = now
        plan.change_window_end = now + timedelta(days=1)
        await session.flush()
        await self._audit.record(
            session,
            action="approve",
            object_type="vuln_remediation_plan",
            object_id=plan.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"status": "approved"},
        )
        return await self._plan_view(session, tenant_id, plan)

    async def apply_remediation(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor, instance_id: uuid.UUID
    ) -> RemediationPlanView:
        inst = await self._load_instance(session, tenant_id, instance_id)
        plan = await self._load_plan(session, tenant_id, instance_id)
        if plan.status != "approved":
            raise Conflict(
                f"This plan is {plan.status}. Approve it before applying the fix.",
                detail="approve the plan before applying",
            )
        now = datetime.now(UTC)
        plan.status = "applied"
        plan.applied_at = now
        plan.execution_log = (
            "Applied in simulation. The executor walked the fix artifact; no host was "
            "modified. Confirm the fix out-of-band, then attest to close."
        )
        # Route closure through the state machine: move the finding to pending_retest.
        if inst.state in OPEN_STATES and inst.state != "pending_retest":
            before = AuditService.snapshot(inst, fields=_INSTANCE_SNAPSHOT)
            from_state = inst.state
            inst.state = "pending_retest"
            self._append_transition(
                session,
                tenant_id,
                inst.id,
                from_state,
                "pending_retest",
                "Remediation applied (simulated)",
                now,
                actor_membership_id=_membership(actor),
            )
            await self._audit.record(
                session,
                action="transition",
                object_type="vuln_instance",
                object_id=inst.id,
                actor=actor,
                tenant_id=tenant_id,
                before=before,
                after=AuditService.snapshot(inst, fields=_INSTANCE_SNAPSHOT),
            )
        await session.flush()
        await self._audit.record(
            session,
            action="update",
            object_type="vuln_remediation_plan",
            object_id=plan.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"status": "applied"},
        )
        return await self._plan_view(session, tenant_id, plan)

    async def verify_remediation(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        instance_id: uuid.UUID,
        evidence: str,
    ) -> RemediationPlanView:
        """Attest the fix worked and close the finding through the instance state
        machine (verify_instance: pending_retest -> fixed, fixed_verified=True)."""
        plan = await self._load_plan(session, tenant_id, instance_id)
        if plan.status != "applied":
            raise Conflict(
                f"This plan is {plan.status}. Apply the fix before confirming it worked.",
                detail="apply the plan before verifying",
            )
        await self.verify_instance(
            session,
            tenant_id=tenant_id,
            actor=actor,
            instance_id=instance_id,
            resolution_notes=evidence,
        )
        now = datetime.now(UTC)
        plan.status = "verified"
        plan.verified_by_membership_id = _membership(actor)
        plan.verified_at = now
        plan.verification_evidence = evidence
        plan.risk_score_after = 0.0  # remediated
        await session.flush()
        await self._audit.record(
            session,
            action="update",
            object_type="vuln_remediation_plan",
            object_id=plan.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"status": "verified"},
        )
        return await self._plan_view(session, tenant_id, plan)

    async def cancel_remediation(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        instance_id: uuid.UUID,
        reason: str,
    ) -> RemediationPlanView:
        plan = await self._load_plan(session, tenant_id, instance_id)
        if plan.status in ("verified", "cancelled"):
            raise Conflict(
                f"This plan is already {plan.status}, so it can no longer be cancelled.",
                detail=f"a {plan.status} plan cannot be cancelled",
            )
        plan.status = "cancelled"
        plan.cancelled_reason = reason
        plan.cancelled_at = datetime.now(UTC)
        await session.flush()
        await self._audit.record(
            session,
            action="update",
            object_type="vuln_remediation_plan",
            object_id=plan.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"status": "cancelled"},
        )
        return await self._plan_view(session, tenant_id, plan)

    async def _upsert_definition(
        self, session: AsyncSession, tenant_id: uuid.UUID, row: FindingRow
    ) -> VulnDefinition:
        key = _definition_key(row)
        defn = (
            await session.execute(
                select(VulnDefinition).where(
                    VulnDefinition.tenant_id == tenant_id, VulnDefinition.definition_key == key
                )
            )
        ).scalar_one_or_none()
        if defn is None:
            defn = VulnDefinition(
                id=uuid7(),
                tenant_id=tenant_id,
                definition_key=key,
                cve_id=row.cve_id,
                title=row.title,
                description=row.description,
                severity=row.severity if row.severity in SEVERITIES else "medium",
                cvss_score=row.cvss_score,
                cvss_vector=row.cvss_vector,
                cwe_id=row.cwe_id,
                recommendation=row.recommendation,
                source=row.source,
            )
            session.add(defn)
            await session.flush()
        else:
            # Keep the strongest signal we've seen (higher CVSS/severity wins).
            if row.cvss_score is not None and (defn.cvss_score or 0) < row.cvss_score:
                defn.cvss_score = row.cvss_score
                defn.cvss_vector = row.cvss_vector or defn.cvss_vector
            if _SEVERITY_RANK.get(row.severity, 9) < _SEVERITY_RANK.get(defn.severity, 9):
                defn.severity = row.severity
        return defn

    # -- enrichment + scoring ------------------------------------------------

    async def _enrich_and_score(
        self,
        session: AsyncSession,
        definitions: Sequence[VulnDefinition],
        instances: Sequence[tuple[VulnInstance, VulnDefinition, Any]],
        *,
        include_github: bool = False,
        include_patch: bool = False,
    ) -> None:
        cves = [c for d in definitions if (c := d.cve_id) and enrichment.is_cve(c)]
        results = await enrichment.enrich_cves(
            cves, include_github=include_github, include_patch=include_patch
        )
        now = datetime.now(UTC)
        for defn in definitions:
            e = results.get((defn.cve_id or "").upper())
            if e is not None:
                # Only overwrite a field when its source actually answered this run;
                # a transient outage must leave the stored KEV/EPSS/exploit intact.
                if e.epss_ok:
                    defn.epss_score = e.epss_score
                    defn.epss_percentile = e.epss_percentile
                if e.kev_ok:
                    defn.kev_flag = e.kev_flag
                    defn.kev_ransomware = e.kev_ransomware
                    defn.kev_added_at = e.kev_added_at
                    defn.kev_vendor = e.kev_vendor
                    defn.kev_product = e.kev_product
                    defn.kev_required_action = e.kev_required_action
                    defn.kev_due_at = e.kev_due_at
                if e.exploit_ok:
                    defn.public_exploit_count = e.public_exploit_count
                    defn.exploit_refs = e.exploit_refs
                defn.advisory_url = e.advisory_url
                if e.patch_available is not None:
                    defn.patch_available = e.patch_available
                    defn.fixed_versions = e.fixed_versions
                    defn.patch_source = e.patch_source
                    defn.patch_checked_at = now
                elif defn.patch_source is None:
                    defn.patch_source = e.patch_source  # nvd baseline link
                defn.enriched_at = now
        self._score_instances(instances)
        await session.flush()

    @staticmethod
    def _score_instances(instances: Sequence[tuple[VulnInstance, VulnDefinition, Any]]) -> None:
        """(Re)compute risk_score/reason from the definition's intel and the asset's
        criticality/exposure — no external calls, so it is cheap to run whenever any
        parameter moves (enrichment, a manual edit, or an asset reclassification)."""
        for inst, defn, ref in instances:
            score, reason = compute_risk(
                severity=defn.severity,
                cvss_score=defn.cvss_score,
                epss_score=defn.epss_score,
                kev_flag=defn.kev_flag,
                public_exploit_count=defn.public_exploit_count,
                asset=AssetRisk(
                    tier=ref.tier if ref else None,
                    internet_facing=ref.internet_facing if ref else False,
                    customer_facing=ref.customer_facing if ref else False,
                ),
            )
            inst.risk_score = score
            inst.risk_reason = reason

    async def rescore_for_asset(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, asset_id: uuid.UUID
    ) -> int:
        """Re-prioritise an asset's open findings after its criticality/exposure
        changed (spec: prioritisation updates on all parameters). Cross-module entry
        called by the assets service; no enrichment, so it is a pure local rescore."""
        rows = list(
            (
                await session.execute(
                    select(VulnInstance, VulnDefinition)
                    .join(VulnDefinition, VulnDefinition.id == VulnInstance.definition_id)
                    .where(
                        VulnInstance.tenant_id == tenant_id,
                        VulnInstance.asset_id == asset_id,
                        VulnInstance.state.in_(list(OPEN_STATES)),
                    )
                )
            ).all()
        )
        if not rows:
            return 0
        refs = await self._asset_refs(session, tenant_id, [asset_id])
        ref = refs.get(asset_id)
        self._score_instances([(inst, defn, ref) for inst, defn in rows])
        await session.flush()
        return len(rows)

    # -- writes: state machine + exceptions ----------------------------------

    async def transition_instance(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        instance_id: uuid.UUID,
        to_state: str,
        note: str | None = None,
    ) -> InstanceDetailView:
        inst = await self._load_instance(session, tenant_id, instance_id)
        allowed = _MANUAL_TRANSITIONS.get(inst.state, frozenset())
        if to_state == inst.state:
            raise Conflict(
                f"This finding is already {to_state.replace('_', ' ')}, so there is "
                "nothing to change.",
                detail=f"already {to_state}",
            )
        if to_state not in allowed:
            raise InvalidInput(
                f"A finding that is {inst.state.replace('_', ' ')} cannot move straight "
                f"to {to_state.replace('_', ' ')}. Pick one of the steps offered for its "
                "current status.",
                detail=f"cannot move a {inst.state} finding to {to_state}",
            )
        before = AuditService.snapshot(inst, fields=_INSTANCE_SNAPSHOT)
        from_state = inst.state
        now = datetime.now(UTC)
        inst.state = to_state
        if to_state == "false_positive":
            inst.false_positive_reason = note
        elif to_state == "active" and from_state in CLOSED_STATES:
            _clear_closure(inst)  # reopening drops the stale closure record
        self._append_transition(
            session,
            tenant_id,
            inst.id,
            from_state,
            to_state,
            note,
            now,
            actor_membership_id=_membership(actor),
        )
        await session.flush()
        await self._audit.record(
            session,
            action="transition",
            object_type="vuln_instance",
            object_id=inst.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(inst, fields=_INSTANCE_SNAPSHOT),
        )
        if inst.owner_membership_id:
            await self._notify().notify_many(
                session,
                tenant_id=tenant_id,
                recipients=[inst.owner_membership_id],
                kind="status",
                title=f"Vulnerability moved to {to_state.replace('_', ' ')}",
                body=note or "",
                object_type="vuln_instance",
                object_id=inst.id,
            )
        return await self.get_instance(session, tenant_id=tenant_id, instance_id=inst.id)

    async def verify_instance(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        instance_id: uuid.UUID,
        resolution_notes: str | None = None,
    ) -> InstanceDetailView:
        """Formal-verification closure (spec 130): a finding is Fixed only from
        pending_retest, and only after a person (or, later, a scanner) confirms the
        retest — never merely asserted. Sets fixed_verified=True."""
        inst = await self._load_instance(session, tenant_id, instance_id)
        if inst.state not in _VERIFIABLE_FROM:
            raise InvalidInput(
                f"This finding is {inst.state.replace('_', ' ')}. Move it to pending "
                "retest before confirming it is fixed.",
                detail="only a finding in retest can be verified fixed; move it to pending retest",
            )
        before = AuditService.snapshot(inst, fields=_INSTANCE_SNAPSHOT)
        now = datetime.now(UTC)
        from_state = inst.state
        inst.state = "fixed"
        inst.fixed_at = now
        inst.fixed_verified = True
        inst.resolution_notes = resolution_notes
        self._append_transition(
            session,
            tenant_id,
            inst.id,
            from_state,
            "fixed",
            resolution_notes or "Verified fixed",
            now,
            actor_membership_id=_membership(actor),
        )
        await session.flush()
        await self._audit.record(
            session,
            action="transition",
            object_type="vuln_instance",
            object_id=inst.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(inst, fields=_INSTANCE_SNAPSHOT),
        )
        if inst.owner_membership_id:
            await self._notify().notify_many(
                session,
                tenant_id=tenant_id,
                recipients=[inst.owner_membership_id],
                kind="status",
                title="Vulnerability verified fixed",
                body=resolution_notes or "",
                object_type="vuln_instance",
                object_id=inst.id,
            )
        return await self.get_instance(session, tenant_id=tenant_id, instance_id=inst.id)

    async def accept_instance(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        instance_id: uuid.UUID,
        reason: str,
        expires_at: datetime,
        compensating_controls: str | None = None,
    ) -> InstanceDetailView:
        inst = await self._load_instance(session, tenant_id, instance_id)
        if inst.state == "accepted":
            raise Conflict(
                "The risk on this finding has already been accepted. Reopen it first if "
                "you need to change the acceptance.",
                detail="already accepted",
            )
        if inst.state in ("fixed", "false_positive"):
            raise InvalidInput(
                f"This finding is closed as {inst.state.replace('_', ' ')}, so its risk "
                "cannot be accepted. Reopen it first.",
                detail="a closed finding cannot be accepted; reopen it first",
            )
        # Mandatory, future expiry (spec 130): an acceptance without an end date is
        # a silent permanent waiver, which is exactly what an auditor flags.
        if expires_at <= datetime.now(UTC):
            raise InvalidInput(
                "Pick a review date in the future. An accepted risk has to be revisited, "
                "so it cannot expire today or earlier.",
                detail="the acceptance expiry must be in the future",
            )
        # Segregation of duties: the finding's own owner cannot sign off their own
        # risk acceptance — someone else must approve it.
        if inst.owner_membership_id is not None and _membership(actor) == inst.owner_membership_id:
            raise InvalidInput(
                "You own this finding, so you cannot accept its risk yourself. "
                "Ask another approver to sign it off.",
                detail="the finding owner cannot accept their own risk; "
                "another approver must sign off",
            )
        before = AuditService.snapshot(inst, fields=_INSTANCE_SNAPSHOT)
        from_state = inst.state
        now = datetime.now(UTC)
        inst.state = "accepted"
        inst.accepted_reason = reason
        inst.accepted_expires_at = expires_at
        inst.accepted_by_membership_id = _membership(actor)
        inst.compensating_controls = compensating_controls
        self._append_transition(
            session,
            tenant_id,
            inst.id,
            from_state,
            "accepted",
            reason,
            now,
            actor_membership_id=_membership(actor),
        )
        await session.flush()
        await self._audit.record(
            session,
            action="approve",
            object_type="vuln_instance",
            object_id=inst.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(inst, fields=_INSTANCE_SNAPSHOT),
        )
        return await self.get_instance(session, tenant_id=tenant_id, instance_id=inst.id)

    # -- daily job entry: expiry sweep + re-enrichment -----------------------

    async def refresh_and_sweep(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> dict[str, int]:
        """Re-enrich open-instance definitions, recompute risk, and expire lapsed
        acceptances. Called by the daily Celery task. Returns a small summary."""
        open_rows = list(
            (
                await session.execute(
                    select(VulnInstance, VulnDefinition)
                    .join(VulnDefinition, VulnDefinition.id == VulnInstance.definition_id)
                    .where(
                        VulnInstance.tenant_id == tenant_id,
                        VulnInstance.state.in_(list(OPEN_STATES)),
                    )
                )
            ).all()
        )
        asset_ids = {inst.asset_id for inst, _ in open_rows}
        refs = await self._asset_refs(session, tenant_id, list(asset_ids))
        defs = {defn.id: defn for _, defn in open_rows}
        triples = [(inst, defn, refs.get(inst.asset_id)) for inst, defn in open_rows]
        await self._enrich_and_score(
            session, list(defs.values()), triples, include_github=True, include_patch=True
        )

        # Expire lapsed acceptances -> back to active (reopened), audited (rule 5).
        now = datetime.now(UTC)
        lapsed = list(
            (
                await session.execute(
                    select(VulnInstance).where(
                        VulnInstance.tenant_id == tenant_id,
                        VulnInstance.state == "accepted",
                        VulnInstance.accepted_expires_at.is_not(None),
                        VulnInstance.accepted_expires_at < now,
                    )
                )
            ).scalars()
        )
        for inst in lapsed:
            before = AuditService.snapshot(inst, fields=_INSTANCE_SNAPSHOT)
            inst.state = "active"
            _clear_closure(inst)  # the lapsed waiver is no longer in force
            self._append_transition(
                session, tenant_id, inst.id, "accepted", "active", "Acceptance expired", now
            )
            await self._audit.record(
                session,
                action="transition",
                object_type="vuln_instance",
                object_id=inst.id,
                actor=System(),
                tenant_id=tenant_id,
                before=before,
                after=AuditService.snapshot(inst, fields=_INSTANCE_SNAPSHOT),
            )

        # SLA escalation (spec 130): open + overdue + not yet escalated -> notify the
        # asset's escalation contact (or owner), record level/time/who, audited.
        escalated = 0
        for inst, _defn in open_rows:
            if inst.sla_due_at is None or inst.sla_due_at >= now or inst.escalation_level > 0:
                continue
            ref = refs.get(inst.asset_id)
            contact = (
                ref.escalation_contact_membership_id if ref else None
            ) or inst.owner_membership_id
            if contact is None:
                # No one to escalate to yet — leave the one-shot unspent so a later
                # owner/escalation-contact assignment triggers it on a future sweep.
                continue
            before = AuditService.snapshot(inst, fields=_INSTANCE_SNAPSHOT)
            inst.escalation_level = 1
            inst.escalated_at = now
            inst.escalated_to_membership_id = contact
            await self._audit.record(
                session,
                action="update",
                object_type="vuln_instance",
                object_id=inst.id,
                actor=System(),
                tenant_id=tenant_id,
                before=before,
                after={"escalation_level": 1, "escalated_to": str(contact)},
            )
            await self._notify().notify_once(
                session,
                tenant_id=tenant_id,
                recipient_membership_id=contact,
                kind="sla_breach",
                title="Vulnerability SLA breached",
                body="A vulnerability past its remediation SLA has been escalated to you.",
                object_type="vuln_instance",
                object_id=inst.id,
                email=True,
            )
            escalated += 1

        await session.flush()
        return {
            "enriched": len(defs),
            "rescored": len(triples),
            "expired": len(lapsed),
            "escalated": escalated,
        }

    # -- helpers -------------------------------------------------------------

    async def _load_instance(
        self, session: AsyncSession, tenant_id: uuid.UUID, instance_id: uuid.UUID
    ) -> VulnInstance:
        inst = await session.get(VulnInstance, instance_id)
        if inst is None or inst.tenant_id != tenant_id:
            raise NotFound(_INSTANCE_GONE, detail=f"vulnerability {instance_id}")
        return inst

    def _append_transition(  # noqa: PLR0913, PLR0917
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        instance_id: uuid.UUID,
        from_state: str | None,
        to_state: str,
        note: str | None,
        occurred_at: datetime,
        actor_membership_id: uuid.UUID | None = None,
    ) -> None:
        # A null actor means the scanner/import did it (ADR-0010).
        session.add(
            VulnTransition(
                id=uuid7(),
                tenant_id=tenant_id,
                instance_id=instance_id,
                actor_membership_id=actor_membership_id,
                from_state=from_state,
                to_state=to_state,
                note=note,
                occurred_at=occurred_at,
            )
        )

    async def _assignment_targets(
        self, session: AsyncSession, tenant_id: uuid.UUID, instance_id: uuid.UUID
    ) -> list[AssignmentTargetView]:
        rows = (
            (
                await session.execute(
                    select(VulnAssignmentTarget)
                    .where(
                        VulnAssignmentTarget.tenant_id == tenant_id,
                        VulnAssignmentTarget.instance_id == instance_id,
                    )
                    .order_by(VulnAssignmentTarget.target_type, VulnAssignmentTarget.target_name)
                )
            )
            .scalars()
            .all()
        )
        return [
            AssignmentTargetView(
                target_type=r.target_type, target_id=r.target_id, name=r.target_name
            )
            for r in rows
        ]

    async def assign_instance(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        instance_id: uuid.UUID,
        owner_membership_id: uuid.UUID | None,
        targets: Sequence[tuple[str, uuid.UUID]] = (),
    ) -> InstanceDetailView:
        """Set the accountable owner and replace the finding's assignment targets.

        The owner is what SLA escalation, remediation approval and notifications
        key off, so it stays a single membership. Targets are the additive
        "who else is on this" — people, roles or groups."""
        from verity.modules.iam.service import iam_service  # noqa: PLC0415

        inst = await self._load_instance(session, tenant_id, instance_id)
        before = audit_service.snapshot(inst, fields=_INSTANCE_SNAPSHOT)

        members = await iam_service.list_members(session, tenant_id=tenant_id)
        name_by_member = {m.membership_id: m.full_name for m in members}
        if owner_membership_id is not None and owner_membership_id not in name_by_member:
            raise InvalidInput(
                "That person is not a member of this workspace.",
                detail=f"membership {owner_membership_id}",
            )

        resolved: list[tuple[str, uuid.UUID, str]] = []
        if targets:
            role_rows = await iam_service.list_roles(session, tenant_id=tenant_id)
            roles = {r.id: r.name for r in role_rows}
            groups = {
                g.id: g.name for g in await iam_service.list_groups(session, tenant_id=tenant_id)
            }
            seen: set[tuple[str, uuid.UUID]] = set()
            for target_type, target_id in targets:
                if target_type not in ASSIGNMENT_TARGET_TYPES:
                    raise InvalidInput(
                        "An assignment must be a person, a role or a group.",
                        detail=f"target_type {target_type}",
                    )
                if (target_type, target_id) in seen:
                    continue
                seen.add((target_type, target_id))
                lookup = {
                    "user": name_by_member,
                    "role": roles,
                    "group": groups,
                }[target_type]
                name = lookup.get(target_id)
                if name is None:
                    raise InvalidInput(
                        "That assignee no longer exists in this workspace.",
                        detail=f"{target_type} {target_id}",
                    )
                resolved.append((target_type, target_id, name))

        existing = (
            (
                await session.execute(
                    select(VulnAssignmentTarget).where(
                        VulnAssignmentTarget.tenant_id == tenant_id,
                        VulnAssignmentTarget.instance_id == instance_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        for row in existing:
            await session.delete(row)
        for target_type, target_id, name in resolved:
            session.add(
                VulnAssignmentTarget(
                    id=uuid7(),
                    tenant_id=tenant_id,
                    instance_id=instance_id,
                    target_type=target_type,
                    target_id=target_id,
                    target_name=name,
                )
            )

        inst.owner_membership_id = owner_membership_id
        await session.flush()

        after = audit_service.snapshot(inst, fields=_INSTANCE_SNAPSHOT)
        after["assigned_to"] = [f"{t[0]}:{t[2]}" for t in resolved]
        await audit_service.record(
            session,
            tenant_id=tenant_id,
            actor=actor,
            action="update",
            object_type="vuln_instance",
            object_id=instance_id,
            before=before,
            after=after,
        )
        return await self.get_instance(session, tenant_id=tenant_id, instance_id=instance_id)

    # -- risk exceptions -----------------------------------------------------
    #
    # Two steps on purpose. The requester states the case (how long, why, what
    # could go wrong); a different person decides. Approving writes the
    # denormalised accepted_* columns on the instance, so the register, the KPI
    # counts and the daily expiry sweep keep working untouched.

    async def _exception_view(
        self, session: AsyncSession, tenant_id: uuid.UUID, row: VulnException
    ) -> ExceptionView:
        names = await self._member_names(session, tenant_id)
        return ExceptionView(
            id=row.id,
            status=row.status,
            duration_days=row.duration_days,
            rationale=row.rationale,
            potential_risks=row.potential_risks,
            compensating_controls=row.compensating_controls,
            requested_by_membership_id=row.requested_by_membership_id,
            requested_by_name=names.get(row.requested_by_membership_id)
            if row.requested_by_membership_id
            else None,
            requested_at=row.requested_at,
            decided_by_membership_id=row.decided_by_membership_id,
            decided_by_name=names.get(row.decided_by_membership_id)
            if row.decided_by_membership_id
            else None,
            decided_at=row.decided_at,
            decision_note=row.decision_note,
            expires_at=row.expires_at,
        )

    async def _current_exception(
        self, session: AsyncSession, tenant_id: uuid.UUID, instance_id: uuid.UUID
    ) -> ExceptionView | None:
        """The open request if there is one, else the most recent decision."""
        row = await session.scalar(
            select(VulnException)
            .where(
                VulnException.tenant_id == tenant_id,
                VulnException.instance_id == instance_id,
            )
            .order_by(
                # A pending request outranks any past decision.
                (VulnException.status != "requested"),
                VulnException.requested_at.desc(),
            )
            .limit(1)
        )
        return None if row is None else await self._exception_view(session, tenant_id, row)

    async def request_exception(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        instance_id: uuid.UUID,
        request: ExceptionRequest,
    ) -> InstanceDetailView:
        """Ask for the risk on this finding to be accepted for a fixed period."""
        inst = await self._load_instance(session, tenant_id, instance_id)
        if inst.state in ("fixed", "false_positive"):
            raise InvalidInput(
                f"This finding is closed as {inst.state.replace('_', ' ')}, so there is no "
                "risk to accept. Reopen it first.",
                detail="a closed finding cannot carry a risk exception",
            )
        if inst.state == "accepted":
            raise Conflict(
                "The risk on this finding is already accepted. Reopen it before asking "
                "for a new exception.",
                detail="already accepted",
            )
        open_request = await session.scalar(
            select(VulnException).where(
                VulnException.tenant_id == tenant_id,
                VulnException.instance_id == instance_id,
                VulnException.status == "requested",
            )
        )
        if open_request is not None:
            raise Conflict(
                "There is already an exception request waiting for a decision on this finding.",
                detail="one open exception request per finding",
            )

        row = VulnException(
            id=uuid7(),
            tenant_id=tenant_id,
            instance_id=instance_id,
            requested_by_membership_id=_membership(actor),
            duration_days=request.duration_days,
            rationale=request.rationale,
            potential_risks=request.potential_risks,
            compensating_controls=request.compensating_controls,
            status="requested",
        )
        session.add(row)
        await session.flush()
        await self._audit.record(
            session,
            action="create",
            object_type="vuln_exception",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after={
                "instance_id": str(instance_id),
                "status": "requested",
                "duration_days": request.duration_days,
            },
        )
        return await self.get_instance(session, tenant_id=tenant_id, instance_id=instance_id)

    async def decide_exception(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        instance_id: uuid.UUID,
        approve: bool,
        note: str | None = None,
    ) -> InstanceDetailView:
        """Approve or reject the open request. Approving accepts the risk."""
        inst = await self._load_instance(session, tenant_id, instance_id)
        row = await session.scalar(
            select(VulnException).where(
                VulnException.tenant_id == tenant_id,
                VulnException.instance_id == instance_id,
                VulnException.status == "requested",
            )
        )
        if row is None:
            raise NotFound(
                "There is no exception request waiting for a decision on this finding.",
                detail=f"no open exception for instance {instance_id}",
            )
        # Segregation of duties: whoever asked cannot also approve. The same rule
        # the one-step acceptance already applied to the finding's owner.
        decider = _membership(actor)
        if decider is not None and decider == row.requested_by_membership_id:
            raise InvalidInput(
                "You raised this exception, so you cannot decide it yourself. "
                "Ask another approver to review it.",
                detail="the requester cannot decide their own exception",
            )
        cleaned = (note or "").strip()
        if not approve and not cleaned:
            raise InvalidInput(
                "Say why the exception is being rejected, so the requester knows what "
                "would change the answer.",
                detail="a rejection must include a reason",
            )

        before = AuditService.snapshot(row, fields=_EXCEPTION_SNAPSHOT)
        now = datetime.now(UTC)
        row.status = "approved" if approve else "rejected"
        row.decided_by_membership_id = decider
        row.decided_at = now
        row.decision_note = cleaned or None

        if approve:
            row.expires_at = now + timedelta(days=row.duration_days)
            # The denormalised current-waiver view the register, the KPI counts
            # and the expiry sweep already read.
            inst_before = AuditService.snapshot(inst, fields=_INSTANCE_SNAPSHOT)
            from_state = inst.state
            inst.state = "accepted"
            inst.accepted_reason = row.rationale
            inst.accepted_expires_at = row.expires_at
            inst.accepted_by_membership_id = decider
            inst.compensating_controls = row.compensating_controls
            session.add(
                VulnTransition(
                    id=uuid7(),
                    tenant_id=tenant_id,
                    instance_id=inst.id,
                    from_state=from_state,
                    to_state="accepted",
                    actor_membership_id=decider,
                    note=f"Exception approved for {row.duration_days} days"
                    + (f": {cleaned}" if cleaned else ""),
                )
            )
            await self._audit.record(
                session,
                action="update",
                object_type="vuln_instance",
                object_id=inst.id,
                actor=actor,
                tenant_id=tenant_id,
                before=inst_before,
                after=AuditService.snapshot(inst, fields=_INSTANCE_SNAPSHOT),
            )

        await self._audit.record(
            session,
            action="update",
            object_type="vuln_exception",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(row, fields=_EXCEPTION_SNAPSHOT),
        )
        await session.flush()
        return await self.get_instance(session, tenant_id=tenant_id, instance_id=instance_id)


# -- module-level helpers ----------------------------------------------------
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_CVE_IN_TITLE = re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE)


def _severity_from_cvss(score: float | None) -> str | None:
    """CVSS v3 qualitative band."""
    if score is None:
        return None
    if score >= 9.0:  # noqa: PLR2004 — CVSS v3 band thresholds
        return "critical"
    if score >= 7.0:  # noqa: PLR2004
        return "high"
    if score >= 4.0:  # noqa: PLR2004
        return "medium"
    if score > 0.0:
        return "low"
    return "info"


def _definition_key(row: FindingRow) -> str:
    if enrichment.is_cve(row.cve_id):
        return row.cve_id.strip().upper()  # type: ignore[union-attr]
    slug = _SLUG_RE.sub("-", row.title.strip().lower()).strip("-")[:120]
    return f"finding:{slug}"


def _locator(row: FindingRow) -> str:
    parts = [p for p in (row.component, row.affected_url, str(row.port) if row.port else None) if p]
    return "/".join(parts)


def _membership(actor: Actor) -> uuid.UUID | None:
    return getattr(actor, "id", None)


def _name_or(names: dict[uuid.UUID, str], mid: uuid.UUID | None) -> str | None:
    return names.get(mid) if mid is not None else None


def _clear_closure(inst: VulnInstance) -> None:
    """Drop all closure metadata when a finding is reopened — otherwise an active
    finding keeps a stale 'accepted risk' waiver or a fixed-verified stamp, which
    the UI renders as a live sign-off and an auditor reads as a misstated posture."""
    inst.fixed_at = None
    inst.fixed_verified = False
    inst.accepted_reason = None
    inst.accepted_expires_at = None
    inst.accepted_by_membership_id = None
    inst.compensating_controls = None
    inst.false_positive_reason = None


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _median(values: list[float]) -> float:
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


_SEVERITY_WORDS: Final = {
    "0": "info",
    "1": "low",
    "2": "medium",
    "3": "high",
    "4": "critical",
    "informational": "info",
    "none": "info",
    "moderate": "medium",
}


def _norm_severity(value: str | None) -> str:
    v = (value or "medium").strip().lower()
    v = _SEVERITY_WORDS.get(v, v)
    return v if v in SEVERITIES else "medium"


def _row_to_finding(r: dict[str, str], *, source: str) -> FindingRow | None:
    """Map a case-insensitive column dict (from CSV/XLSX) to a FindingRow. The
    common scanner-export column aliases are accepted; a row with no title is
    skipped."""
    title = r.get("title") or r.get("name") or r.get("plugin_name")
    if not title:
        return None
    return FindingRow(
        title=title,
        severity=_norm_severity(r.get("severity") or r.get("risk")),
        asset_id=_as_uuid(r.get("asset_id")),
        asset_match=r.get("asset") or r.get("asset_name") or r.get("hostname") or r.get("host"),
        cve_id=(r.get("cve") or r.get("cve_id") or None),
        description=r.get("description") or r.get("synopsis") or None,
        cvss_score=_as_float(r.get("cvss") or r.get("cvss_score") or r.get("cvss3_base_score")),
        cvss_vector=r.get("cvss_vector") or None,
        cwe_id=r.get("cwe") or r.get("cwe_id") or None,
        recommendation=r.get("recommendation") or r.get("solution") or None,
        component=r.get("component") or r.get("plugin_family") or None,
        port=_as_int(r.get("port")),
        affected_url=r.get("url") or r.get("affected_url") or None,
        evidence=r.get("evidence") or r.get("plugin_output") or None,
        reproduction_steps=r.get("reproduction_steps") or r.get("steps") or None,
        source=r.get("source") or source,
    )


def parse_file(file_name: str, data: bytes) -> list[FindingRow]:
    """Dispatch to the right parser by file extension. CSV and Excel are
    deterministic; XML covers the common scanner exports (Nessus/generic). PDF and
    unknown types raise — the caller records the failure on the report row."""
    ext = _file_ext(file_name)
    if ext in ("csv", "txt", ""):
        return parse_csv(data)
    if ext in ("xlsx", "xlsm"):
        return parse_xlsx(data)
    if ext in ("xml", "nessus"):
        return parse_xml(data)
    raise InvalidInput(
        "We cannot read this file type. Upload a CSV, Excel or XML scan export, "
        "or add the findings manually.",
        detail=f"unsupported report format .{ext}; upload CSV, Excel or XML, "
        "or add findings manually",
    )


def parse_csv(data: bytes) -> list[FindingRow]:
    """Parse a scanner CSV export into finding rows. Column names are matched
    case-insensitively; ``asset_id`` (uuid) or ``asset``/``hostname`` (name) ties
    each finding to an asset. Unknown/blank rows are skipped by the importer."""
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    out: list[FindingRow] = []
    for raw in reader:
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        row = _row_to_finding(r, source="csv")
        if row is not None:
            out.append(row)
    return out


def parse_xlsx(data: bytes) -> list[FindingRow]:
    """Parse an Excel (.xlsx) scanner export. Row 1 is the header; the same column
    aliases as CSV apply. Reads the first worksheet only."""
    import openpyxl  # noqa: PLC0415 — heavy import, only on the Excel path

    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        return []
    rows_iter = ws.iter_rows(values_only=True)
    try:
        header = [str(c).strip().lower() if c is not None else "" for c in next(rows_iter)]
    except StopIteration:
        return []
    out: list[FindingRow] = []
    for values in rows_iter:
        r = {
            header[i]: (str(v).strip() if v is not None else "")
            for i, v in enumerate(values)
            if i < len(header)
        }
        row = _row_to_finding(r, source="xlsx")
        if row is not None:
            out.append(row)
    return out


def parse_xml(data: bytes) -> list[FindingRow]:
    """Parse a scanner XML export. Handles the Nessus ``ReportItem`` shape (the most
    common) and a generic fallback that reads finding-like elements. Uses defusedxml
    so a malicious upload cannot trigger entity-expansion or SSRF (rule 8)."""
    from defusedxml import ElementTree as DefusedET  # noqa: PLC0415

    root = DefusedET.fromstring(data)
    out: list[FindingRow] = []
    # Nessus: <ReportHost name="..."><ReportItem severity="" pluginName="" .../>
    for host in root.iter("ReportHost"):
        host_name = host.get("name")
        for item in host.iter("ReportItem"):
            r = _nessus_item_to_dict(item, host_name)
            row = _row_to_finding(r, source="nessus")
            if row is not None:
                out.append(row)
    if out:
        return out
    # Generic fallback: any element carrying a title/name + severity child/attr.
    for el in root.iter():
        r = {(child.tag or "").lower(): (child.text or "").strip() for child in el}
        r.update({(k or "").lower(): v for k, v in el.attrib.items()})
        if r.get("title") or r.get("name") or r.get("pluginname"):
            r.setdefault("name", r.get("pluginname", ""))
            row = _row_to_finding(r, source="xml")
            if row is not None:
                out.append(row)
    return out


def _nessus_item_to_dict(item: object, host_name: str | None) -> dict[str, str]:
    """Flatten a Nessus <ReportItem> (attributes + known child tags) to the common
    column dict."""
    get = item.get  # type: ignore[attr-defined]
    child = {(c.tag or "").lower(): (c.text or "").strip() for c in item}  # type: ignore[attr-defined]
    return {
        "name": get("pluginName", ""),
        "severity": get("severity", ""),
        "port": get("port", ""),
        "host": host_name or "",
        "cve": child.get("cve", ""),
        "cvss_score": child.get("cvss3_base_score") or child.get("cvss_base_score", ""),
        "cvss_vector": child.get("cvss3_vector") or child.get("cvss_vector", ""),
        "description": child.get("description") or child.get("synopsis", ""),
        "solution": child.get("solution", ""),
        "evidence": child.get("plugin_output", ""),
        "plugin_family": get("pluginFamily", ""),
    }


def _file_ext(file_name: str) -> str:
    _, _, ext = (file_name or "").rpartition(".")
    return ext.lower() if ext else ""


def _content_type(file_name: str | None) -> str:
    return {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xml": "application/xml",
        "nessus": "application/xml",
        "pdf": "application/pdf",
    }.get(_file_ext(file_name or ""), "application/octet-stream")


def _as_uuid(value: str | None) -> uuid.UUID | None:
    try:
        return uuid.UUID(value) if value else None
    except ValueError:
        return None


def _as_float(value: str | None) -> float | None:
    try:
        return float(value) if value else None
    except ValueError:
        return None


def _as_int(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None


vulnerability_service = VulnerabilityService()
