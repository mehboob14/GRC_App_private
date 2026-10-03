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


class EngagementPut(_Request):
    name: str = Field(min_length=1, max_length=200)
    framework_version_id: uuid.UUID
    audit_type: str = Field(pattern="^(type_1|type_2)$")
    categories_in_scope: list[str] = Field(default_factory=list)
    window_start: date | None = None
    window_end: date | None = None
    status: str | None = Field(default=None, pattern="^(draft|active|closed)$")


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
