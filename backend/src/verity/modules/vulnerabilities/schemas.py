"""Request/response contracts for the vulnerabilities module."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from verity.modules.tenancy.schemas import UtcDateTime
from verity.modules.vulnerabilities.models import INSTANCE_STATES, SEVERITIES


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class InstanceOut(_Response):
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
    sla_due_at: UtcDateTime | None
    overdue: bool
    escalation_level: int
    first_detected_at: UtcDateTime | None
    last_seen_at: UtcDateTime | None
    detected_by: list[str]


class TransitionOut(_Response):
    from_state: str | None
    to_state: str
    actor_name: str
    note: str | None
    occurred_at: UtcDateTime


class AffectedAssetOut(_Response):
    instance_id: uuid.UUID
    asset_id: uuid.UUID
    asset_name: str
    asset_host: str | None
    state: str
    risk_score: float | None
    priority_band: str


class AssignmentTargetIn(_Request):
    target_type: str = Field(pattern="^(user|role|group)$")
    target_id: uuid.UUID


class AssignmentTargetOut(_Response):
    target_type: str
    target_id: uuid.UUID
    name: str


class AssignRequest(_Request):
    """The accountable owner plus the additional people/roles/groups on a
    finding. Sending an empty ``targets`` list clears them."""

    owner_membership_id: uuid.UUID | None = None
    targets: list[AssignmentTargetIn] = Field(default_factory=list)


class RiskFactorOut(_Response):
    """One additive term of the base risk score."""

    key: str
    label: str
    detail: str
    points: float
    max_points: float


class RiskBreakdownOut(_Response):
    """How the risk score was reached. Not a flat sum: three threat terms make a
    base out of 100, the asset multiplies it, then the 100 cap and the KEV floor
    can bind. Every step travels so the arithmetic is checkable on screen."""

    score: float
    band: str
    reason: str
    factors: list[RiskFactorOut]
    base_score: float
    asset_multiplier: float
    asset_detail: str
    adjusted_score: float
    capped: bool
    kev_floor_applied: bool


class AssetCiaOut(_Response):
    """The linked asset's criticality inputs, for showing why it weighs the score."""

    tier: str | None
    internet_facing: bool
    customer_facing: bool
    confidentiality: int | None
    integrity: int | None
    availability: int | None


class ExceptionOut(_Response):
    """A risk-acceptance request and the decision on it."""

    id: uuid.UUID
    status: str
    duration_days: int
    rationale: str
    potential_risks: str
    compensating_controls: str | None
    requested_by_membership_id: uuid.UUID | None
    requested_by_name: str | None
    requested_at: UtcDateTime
    decided_by_membership_id: uuid.UUID | None
    decided_by_name: str | None
    decided_at: UtcDateTime | None
    decision_note: str | None
    expires_at: UtcDateTime | None


class ExceptionRequestIn(_Request):
    """Ask for the risk on a finding to be accepted for a fixed period.

    Duration rather than an absolute date: the requester is arguing for "90
    days", and the clock should start when the approver says yes, not when the
    form was filled in.
    """

    duration_days: int = Field(ge=1, le=365)
    rationale: str = Field(min_length=1, max_length=4000)
    potential_risks: str = Field(min_length=1, max_length=4000)
    compensating_controls: str | None = Field(default=None, max_length=4000)


class ExceptionDecisionIn(_Request):
    approve: bool
    #: Required on a rejection — enforced in the service, where the rule lives.
    note: str | None = Field(default=None, max_length=2000)


class ReferenceOut(_Response):
    """A primary source behind one of the facts on a finding."""

    backs: str
    label: str
    url: str
    detail: str


class InstanceDetailOut(InstanceOut):
    # cvss_vector / cwe_id / epss_percentile / patch_available are inherited
    # from InstanceOut — the register shows them too.
    definition_id: uuid.UUID
    description: str | None
    recommendation: str | None
    kev_ransomware: bool
    exploit_refs: list[dict[str, object]]
    enriched_at: UtcDateTime | None
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
    accepted_expires_at: UtcDateTime | None
    compensating_controls: str | None
    escalated_at: UtcDateTime | None
    false_positive_reason: str | None
    report_id: uuid.UUID | None
    kev_added_at: UtcDateTime | None = None
    kev_vendor: str | None = None
    kev_product: str | None = None
    kev_required_action: str | None = None
    kev_due_at: UtcDateTime | None = None
    references: list[ReferenceOut] = []
    risk_breakdown: RiskBreakdownOut | None = None
    asset_criticality: AssetCiaOut | None = None
    exception: ExceptionOut | None = None
    transitions: list[TransitionOut]
    affected_assets: list[AffectedAssetOut]
    assignment_targets: list[AssignmentTargetOut]


class KpiOut(_Response):
    open_total: int
    open_by_severity: dict[str, int]
    open_by_priority: dict[str, int]
    sla_posture: dict[str, int]
    overdue: int
    kev_open: int
    accepted: int


class ThroughputOut(_Response):
    closed_30d: int
    opened_30d: int
    mttr_days_by_severity: dict[str, float | None]
    median_mttr_days: float | None


class ReportOut(_Response):
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
    created_at: UtcDateTime


class ImportResultOut(_Response):
    report_id: uuid.UUID
    created: int
    resurfaced: int
    updated: int
    unmatched: int
    definitions: int
    status: str
    parse_error: str | None


class SlaPolicyOut(_Response):
    severity: str
    days: int | None


class AddFindingRequest(_Request):
    asset_id: uuid.UUID
    title: str = Field(min_length=1, max_length=500)
    severity: str = Field(pattern=f"^({'|'.join(SEVERITIES)})$")
    cve_id: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=8000)
    cvss_score: float | None = Field(default=None, ge=0, le=10)
    cvss_vector: str | None = Field(default=None, max_length=120)
    cwe_id: str | None = Field(default=None, max_length=50)
    recommendation: str | None = Field(default=None, max_length=8000)
    component: str | None = Field(default=None, max_length=255)
    port: int | None = Field(default=None, ge=0, le=65535)
    affected_url: str | None = Field(default=None, max_length=1000)
    evidence: str | None = Field(default=None, max_length=8000)
    reproduction_steps: str | None = Field(default=None, max_length=8000)


class TransitionRequest(_Request):
    # "fixed" is reached only via the verify endpoint (formal closure), not here.
    to_state: str = Field(pattern=f"^({'|'.join(INSTANCE_STATES)})$")
    note: str | None = Field(default=None, max_length=2000)


class VerifyRequest(_Request):
    resolution_notes: str | None = Field(default=None, max_length=4000)


class AcceptRequest(_Request):
    reason: str = Field(min_length=1, max_length=2000)
    # Mandatory expiry (spec 130): no permanent silent waivers.
    expires_at: UtcDateTime
    compensating_controls: str | None = Field(default=None, max_length=4000)


class SlaPolicyUpdate(_Request):
    severity: str = Field(pattern=f"^({'|'.join(SEVERITIES)})$")
    days: int | None = Field(default=None, ge=0, le=3650)


class LinkAssetRequest(_Request):
    asset_id: uuid.UUID


class LookupCveRequest(_Request):
    title: str = Field(min_length=1, max_length=500)
    cve_id: str | None = Field(default=None, max_length=50)


class LookupCveOut(_Response):
    matched: bool
    match_source: str
    cve_id: str | None
    cvss_score: float | None
    cvss_vector: str | None
    severity: str | None
    cwe_id: str | None
    description: str | None
    nvd_url: str | None


class RemediationPlanOut(_Response):
    id: uuid.UUID | None
    instance_id: uuid.UUID
    fix_type: str
    title: str
    summary: str
    fix_artifact: str
    rationale: str
    rollback_plan: str | None
    source: str
    status: str
    triggers: list[str]
    risk_score_before: float | None
    risk_score_after: float | None
    change_window_start: UtcDateTime | None
    change_window_end: UtcDateTime | None
    approved_by_name: str | None
    approved_at: UtcDateTime | None
    applied_at: UtcDateTime | None
    execution_log: str | None
    verification_evidence: str | None
    verified_by_name: str | None
    verified_at: UtcDateTime | None
    failure_reason: str | None
    cancelled_reason: str | None
    cancelled_at: UtcDateTime | None


class VerifyRemediationRequest(_Request):
    evidence: str = Field(min_length=1, max_length=4000)


class CancelRemediationRequest(_Request):
    reason: str = Field(min_length=1, max_length=2000)
