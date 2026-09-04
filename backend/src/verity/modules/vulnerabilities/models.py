"""Vulnerability management — the definition/instance model (Week 6, ADR-0010).

The spec (ER §3.9) is benchmarked against Tenable/Qualys/Nucleus. The core idea,
kept here: separate the asset-independent **definition** (one row per CVE/finding,
carrying CVSS and the threat-intel enrichment that lands once and every instance
inherits) from the per-asset **instance** (the stateful unit of work, unique on
asset + definition + locator, with an explicit stored state machine). Every state
change appends a ``vuln_transitions`` row (append-only, null actor = the scanner).

Enrichment columns (EPSS, KEV, public-exploit) are nullable and populated by
``enrichment.py`` — live at import and refreshed by the daily Celery job. A NULL
enrichment field renders as "unknown", never as 0.

``vuln_instances`` is Integratable (source/external_id/synced_at) so a Phase-2
scanner connector is a sync, not a migration (rule 9); the semantic dedup key is
(asset, definition, locator), and ``detected_by`` keeps every reporting source.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Final

from sqlalchemy import Float, ForeignKey, UniqueConstraint, func, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from verity.db.base import (
    Base,
    Integratable,
    TenantScoped,
    Timestamped,
    UUIDPrimaryKey,
    status_check,
    tenant_index,
)

SEVERITIES: Final[tuple[str, ...]] = ("critical", "high", "medium", "low", "info")

# The explicit stored state machine (ADR-0010). Open = still work; Closed = done.
INSTANCE_STATES: Final[tuple[str, ...]] = (
    "new",
    "active",
    "in_progress",
    "pending_retest",
    "fixed",
    "resurfaced",
    "accepted",
    "false_positive",
)
OPEN_STATES: Final[frozenset[str]] = frozenset(
    ("new", "active", "in_progress", "pending_retest", "resurfaced")
)
CLOSED_STATES: Final[frozenset[str]] = frozenset(("fixed", "accepted", "false_positive"))

REPORT_TYPES: Final[tuple[str, ...]] = (
    "vulnerability_scan",
    "penetration_test",
    "code_review",
    "configuration_audit",
)
REPORT_STATUSES: Final[tuple[str, ...]] = ("uploaded", "parsing", "parsed", "failed")

# Remediation plan (spec: "their remediation"). One plan per finding, walking an
# audited lifecycle. Closure still goes through the instance state machine (verify).
FIX_TYPES: Final[tuple[str, ...]] = ("patch", "config", "script", "mitigation")
PLAN_STATUSES: Final[tuple[str, ...]] = (
    "recommended",
    "approved",
    "applied",
    "verified",
    "failed",
    "cancelled",
)

_MEMBERSHIP_FK = "tenant_memberships.id"


class VulnDefinition(UUIDPrimaryKey, TenantScoped, Timestamped, Integratable, Base):
    """Asset-independent description of a vulnerability — one row per CVE (or, for
    a scanner finding with no CVE, per normalised finding). Carries CVSS and the
    threat-intel enrichment; every instance inherits it, so enrichment lands once."""

    __tablename__ = "vuln_definitions"

    # Semantic dedup key within a tenant: the CVE id, or "finding:<slug>" when the
    # finding has no CVE. Same key => same definition => shared enrichment.
    definition_key: Mapped[str]
    cve_id: Mapped[str | None] = mapped_column(default=None)
    title: Mapped[str]
    description: Mapped[str | None] = mapped_column(default=None)
    severity: Mapped[str] = mapped_column(default="medium", server_default=text("'medium'"))

    cvss_score: Mapped[float | None] = mapped_column(Float, default=None)
    cvss_vector: Mapped[str | None] = mapped_column(default=None)
    cvss_version: Mapped[str | None] = mapped_column(default=None)
    cwe_id: Mapped[str | None] = mapped_column(default=None)
    recommendation: Mapped[str | None] = mapped_column(default=None)

    # threat-intel enrichment (enrichment.py) — all nullable = "unknown"
    epss_score: Mapped[float | None] = mapped_column(Float, default=None)  # 0..1 probability
    epss_percentile: Mapped[float | None] = mapped_column(Float, default=None)  # 0..1 rank
    kev_flag: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    kev_ransomware: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    kev_added_at: Mapped[datetime | None] = mapped_column(default=None)
    #: The rest of what CISA publishes for a known-exploited CVE. Stored so a
    #: reader can check the claim rather than trust the badge. ``kev_due_at`` is
    #: CISA's own remediation deadline — displayed only; nothing computes
    #: against it, because a second clock beside sla_due_at would change what
    #: "overdue" means on the register.
    kev_vendor: Mapped[str | None] = mapped_column(default=None)
    kev_product: Mapped[str | None] = mapped_column(default=None)
    kev_required_action: Mapped[str | None] = mapped_column(default=None)
    kev_due_at: Mapped[datetime | None] = mapped_column(default=None)
    public_exploit_count: Mapped[int | None] = mapped_column(default=None)
    exploit_refs: Mapped[list[dict[str, object]]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    enriched_at: Mapped[datetime | None] = mapped_column(default=None)

    # vendor patch intelligence (enrichment.py) — nullable = "unknown".
    patch_available: Mapped[bool | None] = mapped_column(default=None)
    fixed_versions: Mapped[str | None] = mapped_column(default=None)
    advisory_url: Mapped[str | None] = mapped_column(default=None)
    patch_source: Mapped[str | None] = mapped_column(default=None)  # msrc, nvd, …
    patch_checked_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("vuln_definitions", "severity", SEVERITIES),
        UniqueConstraint(
            "tenant_id", "definition_key", name="uq_vuln_definitions__tenant_id_key"
        ),
        tenant_index("vuln_definitions", "cve_id"),
        tenant_index("vuln_definitions", "severity"),
    )


class VulnInstance(UUIDPrimaryKey, TenantScoped, Timestamped, Integratable, Base):
    """One occurrence of a definition on one asset at one locator — the stateful
    unit of work. The same CVE on two assets, or two ports, is two instances."""

    __tablename__ = "vuln_instances"

    definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vuln_definitions.id", ondelete="CASCADE")
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"))
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vuln_reports.id", ondelete="SET NULL"), default=None
    )

    # locator: the normalised "where on the asset" (host:port/component/url). Part
    # of the dedup key; "" means asset-wide. Display parts kept alongside.
    locator: Mapped[str] = mapped_column(default="", server_default=text("''"))
    component: Mapped[str | None] = mapped_column(default=None)
    port: Mapped[int | None] = mapped_column(default=None)
    affected_url: Mapped[str | None] = mapped_column(default=None)

    state: Mapped[str] = mapped_column(default="new", server_default=text("'new'"))
    # risk_score blends the definition (CVSS + exploit intel) with the asset
    # (criticality + exposure); stored so the register sorts without re-joining.
    risk_score: Mapped[float | None] = mapped_column(Float, default=None)
    risk_reason: Mapped[str | None] = mapped_column(default=None)

    # ownership inherited from the asset at detection, so triage starts assigned.
    owner_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )

    first_detected_at: Mapped[datetime | None] = mapped_column(default=None)
    last_seen_at: Mapped[datetime | None] = mapped_column(default=None)
    sla_due_at: Mapped[datetime | None] = mapped_column(default=None)
    # every scanner/source that has reported this instance (dedup keeps one row)
    detected_by: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )

    # closure — fixed is scanner-verified or formally approved, never just asserted
    fixed_at: Mapped[datetime | None] = mapped_column(default=None)
    fixed_verified: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    resurfaced_count: Mapped[int] = mapped_column(default=0, server_default=text("0"))

    # analyst content (spec 126) — per-occurrence, so it lives on the instance
    evidence: Mapped[str | None] = mapped_column(default=None)
    reproduction_steps: Mapped[str | None] = mapped_column(default=None)
    resolution_notes: Mapped[str | None] = mapped_column(default=None)

    # exception = the "accepted" state + its reason/expiry (the accepted risk waiver)
    accepted_reason: Mapped[str | None] = mapped_column(default=None)
    accepted_expires_at: Mapped[datetime | None] = mapped_column(default=None)
    accepted_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    # what offsets the accepted risk (spec 130) — free text / control references
    compensating_controls: Mapped[str | None] = mapped_column(default=None)
    false_positive_reason: Mapped[str | None] = mapped_column(default=None)

    # SLA escalation (spec 130) — bumped by the daily sweep when overdue.
    escalation_level: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    escalated_at: Mapped[datetime | None] = mapped_column(default=None)
    escalated_to_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )

    __table_args__ = (
        status_check("vuln_instances", "state", INSTANCE_STATES),
        UniqueConstraint(
            "tenant_id",
            "asset_id",
            "definition_id",
            "locator",
            name="uq_vuln_instances__asset_def_locator",
        ),
        tenant_index("vuln_instances", "asset_id"),
        tenant_index("vuln_instances", "state"),
        tenant_index("vuln_instances", "owner_membership_id"),
    )


class VulnTransition(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """Every state change on an instance, append-only (insert-only, enforced by a
    revoked grant + trigger). A null actor means the scanner did it. This is where
    time-to-remediate and throughput reporting come from."""

    __tablename__ = "vuln_transitions"

    instance_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vuln_instances.id", ondelete="CASCADE")
    )
    actor_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    from_state: Mapped[str | None] = mapped_column(default=None)
    to_state: Mapped[str]
    note: Mapped[str | None] = mapped_column(default=None)
    occurred_at: Mapped[datetime] = mapped_column()

    __table_args__ = (tenant_index("vuln_transitions", "instance_id"),)


class VulnReport(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """An uploaded scan or pen-test report. Every parsed instance references its
    source report, so an auditor can walk from a finding back to the report."""

    __tablename__ = "vuln_reports"

    name: Mapped[str]
    description: Mapped[str | None] = mapped_column(default=None)
    report_type: Mapped[str] = mapped_column(
        default="vulnerability_scan", server_default=text("'vulnerability_scan'")
    )
    scan_tool: Mapped[str | None] = mapped_column(default=None)
    scan_date: Mapped[datetime | None] = mapped_column(default=None)

    file_key: Mapped[str | None] = mapped_column(default=None)
    file_name: Mapped[str | None] = mapped_column(default=None)
    file_type: Mapped[str | None] = mapped_column(default=None)

    status: Mapped[str] = mapped_column(default="uploaded", server_default=text("'uploaded'"))
    parse_error: Mapped[str | None] = mapped_column(default=None)

    total_count: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    critical_count: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    high_count: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    medium_count: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    low_count: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    info_count: Mapped[int] = mapped_column(default=0, server_default=text("0"))

    uploaded_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )

    __table_args__ = (
        status_check("vuln_reports", "report_type", REPORT_TYPES),
        status_check("vuln_reports", "status", REPORT_STATUSES),
        tenant_index("vuln_reports", "status"),
    )


class VulnRemediationPlan(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A generated, approvable, verifiable fix plan for one finding. Stored (not
    regenerated on the fly) because an auditor asks who approved the fix, when it was
    applied, and what proved it worked — every answer is a column here. The executor
    is simulated: it walks the artifact, never touches a host (rule 11 for the AI
    draft path; closure is scanner/person-verified via the instance state machine)."""

    __tablename__ = "vuln_remediation_plans"

    instance_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vuln_instances.id", ondelete="CASCADE")
    )
    fix_type: Mapped[str] = mapped_column(default="patch", server_default=text("'patch'"))
    title: Mapped[str]
    summary: Mapped[str]
    fix_artifact: Mapped[str]  # the copy-pasteable steps
    rationale: Mapped[str]
    rollback_plan: Mapped[str | None] = mapped_column(default=None)
    source: Mapped[str] = mapped_column(default="heuristic", server_default=text("'heuristic'"))
    status: Mapped[str] = mapped_column(default="recommended", server_default=text("'recommended'"))

    # the red flags that justified acting, frozen at generation time
    triggers: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    risk_score_before: Mapped[float | None] = mapped_column(Float, default=None)
    risk_score_after: Mapped[float | None] = mapped_column(Float, default=None)

    change_window_start: Mapped[datetime | None] = mapped_column(default=None)
    change_window_end: Mapped[datetime | None] = mapped_column(default=None)

    approved_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    approved_at: Mapped[datetime | None] = mapped_column(default=None)
    applied_at: Mapped[datetime | None] = mapped_column(default=None)
    execution_log: Mapped[str | None] = mapped_column(default=None)
    verification_evidence: Mapped[str | None] = mapped_column(default=None)
    verified_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    verified_at: Mapped[datetime | None] = mapped_column(default=None)
    failure_reason: Mapped[str | None] = mapped_column(default=None)
    cancelled_reason: Mapped[str | None] = mapped_column(default=None)
    cancelled_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("vuln_remediation_plans", "fix_type", FIX_TYPES),
        status_check("vuln_remediation_plans", "status", PLAN_STATUSES),
        # One plan per finding — regenerating replaces the content in place.
        UniqueConstraint(
            "tenant_id", "instance_id", name="uq_vuln_remediation_plans__instance"
        ),
        tenant_index("vuln_remediation_plans", "instance_id"),
    )


class VulnSlaPolicy(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """Per-tenant remediation SLA: days-to-fix per severity. One row per severity;
    absent rows fall back to the code defaults. The full policy engine (scope
    conditions, escalation) is Phase 2 — this is the "set an SLA" of Week 6."""

    __tablename__ = "vuln_sla_policies"

    severity: Mapped[str]
    days: Mapped[int]

    __table_args__ = (
        status_check("vuln_sla_policies", "severity", SEVERITIES),
        UniqueConstraint("tenant_id", "severity", name="uq_vuln_sla_policies__tenant_id_severity"),
    )


ASSIGNMENT_TARGET_TYPES: Final[tuple[str, ...]] = ("user", "role", "group")


class VulnAssignmentTarget(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One thing a triager assigned a finding to: a named person, a role, or a
    group. ``target_name`` is a snapshot label so the row still reads sensibly
    if the role is later renamed or the person leaves — IAM stays the row of
    truth, this records what was asked for.

    The accountable owner remains ``VulnInstance.owner_membership_id``: SLA
    escalation, remediation-plan approval and notifications all key off that one
    person. These targets are the additive "who else is on this"."""

    __tablename__ = "vuln_assignment_targets"

    instance_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vuln_instances.id", ondelete="CASCADE")
    )
    target_type: Mapped[str]
    target_id: Mapped[uuid.UUID]
    target_name: Mapped[str]

    __table_args__ = (
        status_check("vuln_assignment_targets", "target_type", ASSIGNMENT_TARGET_TYPES),
        UniqueConstraint(
            "tenant_id",
            "instance_id",
            "target_type",
            "target_id",
            name="uq_vuln_assignment_targets__target",
        ),
        tenant_index("vuln_assignment_targets", "instance_id"),
    )


#: requested -> approved | rejected; approved -> expired | revoked. Terminal
#: states are kept, never deleted (rule 6) — a withdrawn waiver is part of the
#: record an auditor reads.
EXCEPTION_STATUSES: Final[tuple[str, ...]] = (
    "requested",
    "approved",
    "rejected",
    "expired",
    "revoked",
)


class VulnException(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A request to accept the risk on a finding, and the decision on it.

    Acceptance used to be one act: an approver typed a reason and an expiry.
    That records the outcome but not the case for it, and gives a reviewer
    nowhere to state how long it is needed for, why, or what could go wrong if
    it is granted. This row holds the argument; the decision is a second step by
    a different person (segregation of duties is enforced in the service).

    ``VulnInstance.accepted_*`` remains the denormalised current-waiver view —
    the register, the KPI counts and the daily expiry sweep read those, and
    approving an exception writes them, so nothing built on them changes.
    """

    __tablename__ = "vuln_exceptions"

    instance_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vuln_instances.id", ondelete="CASCADE")
    )

    # -- the request ---------------------------------------------------------
    requested_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )
    requested_at: Mapped[datetime] = mapped_column(server_default=func.now())
    #: What the requester asked for. The absolute date is derived on approval —
    #: a stored duration would mean a different date depending on when it was
    #: decided.
    duration_days: Mapped[int]
    rationale: Mapped[str]
    potential_risks: Mapped[str]
    compensating_controls: Mapped[str | None] = mapped_column(default=None)

    # -- the decision --------------------------------------------------------
    status: Mapped[str] = mapped_column(default="requested", server_default=text("'requested'"))
    decided_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )
    decided_at: Mapped[datetime | None] = mapped_column(default=None)
    decision_note: Mapped[str | None] = mapped_column(default=None)
    expires_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("vuln_exceptions", "status", EXCEPTION_STATUSES),
        tenant_index("vuln_exceptions", "instance_id"),
        tenant_index("vuln_exceptions", "status"),
    )
