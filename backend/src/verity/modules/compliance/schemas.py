"""Response models for the compliance module.

Read-only in Week 2 Stage 2: this module serves shipped global content
(frameworks, their requirements, and the control template library) and writes
nothing, so there are no request models and no audit rows yet.

Every field here is content the platform ships. Nothing on these responses is
derived from a tenant's own data — readiness, coverage and control counts per
tenant arrive with the tenant control library, and are deliberately absent
rather than stubbed with a zero that would read as a real measurement.
"""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from verity.modules.connectors.schemas import ControlChainOut
from verity.modules.tenancy.schemas import UtcDateTime


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class FrameworkVersionOut(_Response):
    id: uuid.UUID
    version: str
    published_at: UtcDateTime
    is_current: bool
    requirement_count: int


class FrameworkOut(_Response):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    built_in: bool
    versions: list[FrameworkVersionOut]
    # How scope is chosen: "categories" (SOC 2) or "applicability" (ISO 27001).
    scope_model: str = "categories"
    position: int = 100


class RequirementOut(_Response):
    id: uuid.UUID
    requirement_key: str
    code: str
    name: str
    description: str | None
    category: str
    trust_services_category: str
    is_always_in_scope: bool
    # How many shipped control templates claim to satisfy this criterion. A
    # criterion with zero is a genuine gap in the library, so the number is
    # counted, never defaulted.
    template_count: int


class ControlTemplateOut(_Response):
    id: uuid.UUID
    code: str
    canonical_key: str
    name: str
    description: str
    implementation_guidance: str | None
    category: str
    sub_category: str | None
    control_type: str | None
    control_sub_type: str | None
    importance: str
    built_in: bool


class ControlTemplateDetailOut(ControlTemplateOut):
    """One template plus the criteria it satisfies — the 'collect once, satisfy
    many' relationship made visible."""

    requirements: list[RequirementOut]


class ControlTemplatePage(_Response):
    items: list[ControlTemplateOut]
    total: int


# ---------------------------------------------------------------------------
# Tenant control library
# ---------------------------------------------------------------------------


class ControlOut(_Response):
    id: uuid.UUID
    code: str
    name: str
    description: str
    implementation_guidance: str | None
    category: str
    sub_category: str | None
    control_type: str | None
    control_sub_type: str | None
    status: str
    origin: str
    owner_membership_id: uuid.UUID | None
    owner_name: str | None
    disabled_at: UtcDateTime | None
    disabled_reason: str | None
    template_id: uuid.UUID | None
    # The criteria this control satisfies, as stable keys (e.g. "SOC2:CC6.2").
    requirement_keys: list[str]


class ControlCreate(_Request):
    # Optional: omit it and the platform assigns a GRC-NN code. A value is still
    # accepted (e.g. an imported control that carries its own).
    code: str | None = Field(default=None, max_length=100)
    name: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=4000)
    category: str = Field(min_length=1, max_length=100)
    sub_category: str | None = Field(default=None, max_length=100)
    control_type: str | None = Field(default=None, max_length=50)
    """Preventive / Detective / Corrective, for a tenant's own internal or custom
    control. Omitted for anything that mirrors framework content — the platform
    does not assert a design classification the framework never made."""

    control_sub_type: str | None = Field(default=None, max_length=50)
    implementation_guidance: str | None = Field(default=None, max_length=8000)
    owner_membership_id: uuid.UUID | None = None
    requirement_ids: list[uuid.UUID] = Field(default_factory=list)
    # Evidence to attach to the new control. None leaves it unlinked.
    evidence_ids: list[uuid.UUID] | None = None


class ControlUpdate(_Request):
    """Patch semantics: only fields present are written.

    ``clear_owner`` exists because a null ``owner_membership_id`` is
    indistinguishable from an absent one in a patch body, and un-assigning an
    owner has to be expressible.
    """

    name: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, min_length=1, max_length=4000)
    implementation_guidance: str | None = Field(default=None, max_length=8000)
    category: str | None = Field(default=None, max_length=100)
    sub_category: str | None = Field(default=None, max_length=100)
    control_type: str | None = Field(default=None, max_length=50)
    control_sub_type: str | None = Field(default=None, max_length=50)
    status: str | None = Field(default=None, max_length=50)
    owner_membership_id: uuid.UUID | None = None
    clear_owner: bool = False
    requirement_ids: list[uuid.UUID] | None = None
    # None leaves evidence links untouched; a list replaces them wholesale.
    evidence_ids: list[uuid.UUID] | None = None


class ControlDisable(_Request):
    """Rule 6: a control is retired with a reason, never deleted."""

    reason: str = Field(min_length=1, max_length=2000)


class AdoptLibraryRequest(_Request):
    """Instantiate the shipped templates into this tenant.

    ``requirement_ids`` narrows adoption to the templates satisfying those
    criteria — the scoping path. Omit it to adopt the whole library.
    """

    requirement_ids: list[uuid.UUID] | None = None


class AdoptLibraryResponse(_Response):
    created: int
    already_present: int
    mappings_created: int


class ControlVocabularyOut(_Response):
    """The closed vocabularies the Controls UI offers. Served rather than
    duplicated in the frontend, so the two cannot drift out of step."""

    categories: list[str]
    # The Sub-types the shipped library uses, per Type (category). Suggestions for
    # the control form, not a closed list: a custom control may carry its own.
    sub_categories: dict[str, list[str]]
    control_types: list[str]
    control_sub_types: list[str]
    statuses: list[str]


# ---------------------------------------------------------------------------
# Engagement and coverage
# ---------------------------------------------------------------------------


class EngagementOut(_Response):
    id: uuid.UUID
    name: str
    framework_version_id: uuid.UUID
    audit_type: str
    status: str
    window_start: date | None
    window_end: date | None
    categories_in_scope: list[str]
    scope_statement: str | None = None
    certification_body: str | None = None
    audit_on: date | None = None
    as_of_date: date | None = None
    target_date: date | None = None
    driver: str | None = None
    live_date: date | None = None
    assessor: str = "unknown"
    assessor_accreditation_body: str | None = None
    assessor_contact: str | None = None
    assessor_engaged_on: date | None = None
    scope_statement_ai: bool = False
    scope_statement_approved_at: UtcDateTime | None = None
    scope_statement_approved_by_membership_id: uuid.UUID | None = None


class EngagementPut(_Request):
    name: str = Field(min_length=1, max_length=200)
    framework_version_id: uuid.UUID
    audit_type: str = Field(
        pattern="^(type_1|type_2|initial_certification|surveillance|recertification)$"
    )
    categories_in_scope: list[str] = Field(default_factory=list)
    window_start: date | None = None
    window_end: date | None = None
    status: str | None = Field(default=None, pattern="^(draft|active|closed)$")
    scope_statement: str | None = Field(default=None, max_length=8000)
    certification_body: str | None = Field(default=None, max_length=200)
    audit_on: date | None = None
    # Guided onboarding EN-2, EN-3. Each of these is left as it is when not sent, so a
    # form that does not know about them never clears them.
    as_of_date: date | None = None
    target_date: date | None = None
    driver: str | None = Field(default=None, max_length=300)
    live_date: date | None = None
    assessor: str | None = Field(default=None, pattern="^(undecided|chosen)$")
    assessor_accreditation_body: str | None = Field(default=None, max_length=200)
    assessor_contact: str | None = Field(default=None, max_length=300)
    assessor_engaged_on: date | None = None
    scope_statement_ai: bool | None = None
    """True when the scope statement text came from an AI draft (AI-2)."""


class ScopeOtherDecisionOut(_Response):
    framework_code: str
    in_scope: bool


class ScopeItemOut(_Response):
    id: uuid.UUID
    kind: str
    name: str
    origin: str
    in_scope: bool | None
    reason: str | None
    decided_at: UtcDateTime | None
    others: list[ScopeOtherDecisionOut]


class ScopeItemIn(_Request):
    kind: str = Field(
        pattern="^(service|legal_entity|site|environment|system|vendor|people_group|data_type)$"
    )
    name: str = Field(min_length=1, max_length=200)


class ScopeDecisionIn(_Request):
    in_scope: bool
    reason: str | None = Field(default=None, max_length=1000)


class ScopeDecisionOut(_Response):
    item: ScopeItemOut
    notices: list[str]


class ScopeRetireIn(_Request):
    reason: str = Field(min_length=1, max_length=1000)


class ScopeRetireOut(_Response):
    notices: list[str]


class CriterionCoverageOut(_Response):
    requirement_id: uuid.UUID
    requirement_key: str
    code: str
    name: str
    trust_services_category: str
    in_scope: bool
    control_count: int


class ControlGapOut(_Response):
    control_id: uuid.UUID
    code: str
    name: str
    reason: str


class CoverageOut(_Response):
    criteria_total: int
    criteria_covered: int
    criteria_uncovered: list[CriterionCoverageOut]
    controls_total: int
    controls_without_evidence: int
    controls_no_evidence: list[ControlGapOut]
    # Always true since the evidence module shipped (2026-08-17). Kept so the
    # existing client contract does not break; new clients should ignore it.
    evidence_tracking_available: bool
    controls_unmapped: list[ControlGapOut]


class StatusCountOut(_Response):
    status: str
    count: int


class CategoryCoverageOut(_Response):
    category: str
    in_scope: int
    covered: int
    ready: int


class TimelinePointOut(_Response):
    on: date
    controls: int
    evidence: int


class ActivityItemOut(_Response):
    occurred_at: UtcDateTime
    action: str
    actor_name: str | None
    control_code: str | None
    control_name: str | None


class OwnerCountOut(_Response):
    membership_id: uuid.UUID | None
    name: str
    role: str | None
    count: int


class DisabledControlOut(_Response):
    control_id: uuid.UUID
    code: str
    name: str
    reason: str | None


class RecentEvidenceOut(_Response):
    title: str
    control_code: str | None
    collected_on: date
    freshness: str


class DashboardOut(_Response):
    """The compliance dashboard payload. Point-in-time figures plus one timeline
    and a recent-activity feed. ``checks_available`` is false until a connection
    has produced results; the automation counts are controls, rolled up from their
    tests (passing, failing, or could not be checked)."""

    has_engagement: bool
    framework_name: str | None
    framework_code: str | None = None
    scope_model: str = "categories"
    # Controls here that also answer a requirement of another framework.
    controls_shared: int = 0
    audit_type: str | None
    categories_in_scope: list[str]
    criteria_total: int
    criteria_covered: int
    criteria_uncovered: int
    controls_total: int
    controls_evidenced: int
    controls_no_evidence: int
    controls_owned: int
    controls_disabled: int
    controls_internal: int
    controls_unmapped: int
    controls_ready: int
    controls_in_progress: int
    by_status: list[StatusCountOut]
    by_category: list[CategoryCoverageOut]
    by_owner: list[OwnerCountOut]
    disabled: list[DisabledControlOut]
    evidence_total: int
    evidence_fresh: int
    evidence_aging: int
    evidence_stale: int
    evidence_recent: list[RecentEvidenceOut]
    tenant_created_on: date
    timeline_from: date
    timeline_to: date
    timeline: list[TimelinePointOut]
    checks_available: bool
    automation_passing: int
    automation_failing: int
    automation_error: int
    recent_activity: list[ActivityItemOut]


class ReportKpisOut(_Response):
    controls_total: int
    controls_disabled: int
    controls_evidenced: int
    controls_owned: int
    controls_ready: int
    criteria_mapped: int
    by_status: dict[str, int]
    controls_failing_automation: int = 0


class ReportRowOut(_Response):
    code: str
    name: str
    category: str
    sub_category: str | None
    control_type: str | None
    status: str
    status_label: str
    owner_name: str | None
    frameworks: list[str]
    criteria: list[str]
    evidence_count: int
    disabled_reason: str | None


class ControlReportOut(_Response):
    generated_at: UtcDateTime
    framework_label: str
    kpis: ReportKpisOut
    rows: list[ReportRowOut]


class ScopeCriterionOut(_Response):
    id: uuid.UUID
    requirement_key: str
    code: str
    name: str
    trust_services_category: str
    is_always_in_scope: bool


class ChainRequirementOut(_Response):
    id: uuid.UUID
    requirement_key: str
    code: str
    name: str
    description: str | None
    category: str
    trust_services_category: str


class ChainControlOut(BaseModel):
    control_id: uuid.UUID
    code: str
    name: str
    status: str
    owner_name: str | None
    coverage: str | None
    rationale: str | None
    origin: str
    ready: bool
    chain: ControlChainOut | None


class RequirementChainOut(BaseModel):
    """A criterion, the controls that answer it, and what evidences each."""

    requirement: ChainRequirementOut
    state: str
    controls: list[ChainControlOut]


# ---------------------------------------------------------------------------
# Frameworks a workspace runs, the overlap preview, and the Statement of Applicability
# ---------------------------------------------------------------------------


class TenantFrameworkOut(_Response):
    """One framework in the catalogue, as this workspace sees it."""

    framework_id: uuid.UUID
    code: str
    name: str
    description: str | None
    scope_model: str
    position: int
    version_id: uuid.UUID | None
    version: str | None
    requirement_count: int
    added: bool
    added_at: UtcDateTime | None


class OverlapGroupOut(_Response):
    group: str
    total: int
    covered: int
    partly: int
    needs_new: int
    no_control: int


class OverlapControlOut(_Response):
    code: str
    name: str
    category: str


class OverlapOut(_Response):
    """What adding a framework would mean for this workspace, before it is added."""

    framework_id: uuid.UUID
    code: str
    name: str
    version: str
    added: bool
    requirements_total: int
    # A control the workspace already runs is the main route to the requirement.
    covered: int
    # Only controls that cover part of it are running.
    partly: int
    # No running control answers it; adding the framework brings the controls that do.
    needs_new: int
    # No control in the library answers it (a gap in the content, never expected).
    no_control: int
    controls_in_use: int
    controls_to_adopt: list[OverlapControlOut]
    groups: list[OverlapGroupOut]


class FrameworkAdd(_Request):
    framework_id: uuid.UUID


class FrameworkAddedOut(_Response):
    framework: TenantFrameworkOut
    controls_adopted: int
    links_created: int


class ApplicabilityControlOut(_Response):
    control_id: uuid.UUID
    code: str
    name: str
    status: str
    ready: bool
    coverage: str | None


class ApplicabilityRowOut(_Response):
    requirement_id: uuid.UUID
    requirement_key: str
    code: str
    name: str
    description: str | None
    category: str
    # A requirement that cannot be excluded (the management system clauses).
    locked: bool
    applicable: bool
    justification: str | None
    provided_by: str
    owner_membership_id: uuid.UUID | None
    owner_name: str | None
    reviewed_at: UtcDateTime | None
    # excluded, met, partly, not_started or no_controls
    state: str
    controls: list[ApplicabilityControlOut]


class ApplicabilitySummaryOut(_Response):
    total: int
    applicable: int
    excluded: int
    reviewed: int
    met: int
    partly: int
    not_started: int
    no_controls: int


class StatementOut(_Response):
    framework_id: uuid.UUID
    code: str
    name: str
    version: str
    scope_statement: str | None
    summary: ApplicabilitySummaryOut
    rows: list[ApplicabilityRowOut]


class ApplicabilityPut(_Request):
    applicable: bool
    justification: str | None = Field(default=None, max_length=4000)
    provided_by: str = Field(default="organization", pattern="^(organization|supplier)$")
    owner_membership_id: uuid.UUID | None = None
    # Stamp the row as reviewed now, so a decision shows who last confirmed it and when.
    reviewed: bool = False


class ApplicabilityVersionOut(_Response):
    id: uuid.UUID
    number: int
    framework_version: str
    note: str | None
    approved_by_membership_id: uuid.UUID | None
    created_at: UtcDateTime


class ApproveVersionIn(_Request):
    note: str | None = Field(default=None, max_length=1000)
