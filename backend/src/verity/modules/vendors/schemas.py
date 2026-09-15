"""Request/response contracts for the vendor module.

Response shapes mirror the frontend's `types.ts` so the mock -> real swap is a
one-file change on that side. Responses build from the service's View dataclasses
via ``from_attributes``.

The cached risk columns (``tier``, ``current_residual_score``, ``current_grade``,
``annual_contract_value``) appear on responses and on **no** request: they are
derived from the vendor's engagements, so a client that could write them could
make an unscored vendor look scored.
"""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from verity.modules.tenancy.schemas import UtcDateTime


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# -- requests -----------------------------------------------------------------


class EngagementWrite(_Request):
    """One use of the vendor. Tier and status are derived, so neither comes in."""

    name: str = Field(min_length=1, max_length=300)
    service_description: str = Field(default="", max_length=8000)
    business_unit: str | None = Field(default=None, max_length=300)
    internal_owner_membership_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None


class VendorWrite(_Request):
    """The create/edit payload for the organisation itself."""

    name: str = Field(min_length=1, max_length=300)
    vendor_type: str = "vendor"
    industry: str | None = Field(default=None, max_length=300)
    website: str | None = Field(default=None, max_length=2000)
    business_unit: str | None = Field(default=None, max_length=300)
    services_provided: str = Field(default="", max_length=8000)
    stores_pii: bool = False
    data_location: str | None = Field(default=None, max_length=300)
    data_types_in_scope: list[str] = Field(default_factory=list)
    systems_in_scope: list[str] = Field(default_factory=list, max_length=100)
    data_classification: str | None = None
    tags: list[str] = Field(default_factory=list)
    business_owner_membership_id: uuid.UUID | None = None
    security_owner_membership_id: uuid.UUID | None = None
    relationship_owner_membership_id: uuid.UUID | None = None


class VendorCreate(VendorWrite):
    """Create carries an optional first engagement.

    Omitting it creates the implicit default (V10), which is what keeps a small
    workspace from ever having to learn the word "engagement".
    """

    engagement: EngagementWrite | None = None


class ContactWrite(_Request):
    name: str = Field(min_length=1, max_length=300)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=64)
    contact_type: str = "commercial"


# -- responses ----------------------------------------------------------------


class OwnershipOut(_Response):
    business_owner_membership_id: uuid.UUID | None
    business_owner_name: str | None
    security_owner_membership_id: uuid.UUID | None
    security_owner_name: str | None
    relationship_owner_membership_id: uuid.UUID | None
    relationship_owner_name: str | None


class EngagementOut(_Response):
    id: uuid.UUID
    vendor_id: uuid.UUID
    name: str
    service_description: str
    business_unit: str | None
    internal_owner_membership_id: uuid.UUID | None
    internal_owner_name: str | None
    tier: str | None
    status: str
    start_date: date | None
    end_date: date | None
    created_at: UtcDateTime
    updated_at: UtcDateTime


class ContactOut(_Response):
    id: uuid.UUID
    vendor_id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    contact_type: str


class DuplicateMatchOut(_Response):
    id: uuid.UUID
    name: str
    reason: str


class VendorOut(_Response):
    id: uuid.UUID
    name: str
    vendor_type: str
    industry: str | None
    website: str | None
    business_unit: str | None
    services_provided: str
    stores_pii: bool
    data_location: str | None
    data_types_in_scope: list[str]
    systems_in_scope: list[str]
    data_classification: str | None
    lifecycle_status: str
    tier: str | None
    current_residual_score: float | None
    current_grade: str | None
    annual_contract_value: float | None
    ownership: OwnershipOut
    next_reassessment_on: date | None
    tags: list[str]
    source: str
    created_at: UtcDateTime
    updated_at: UtcDateTime
    engagement_count: int
    contact_count: int
    attention_code: str | None
    """What this vendor is waiting on. None means nothing is."""


# -- lifecycle and tiering (section 2) ----------------------------------------


class TieringAnswerIn(_Request):
    value: str | float | list[str] | None = None
    comment: str | None = Field(default=None, max_length=4000)


class TieringWrite(_Request):
    """Answers to a tiering questionnaire, plus an optional human override.

    ``answers`` (question id to answer) is what the interface sends, against
    ``questionnaire_id`` or the tenant's default. Without it, the five fixed factor
    fields are read instead, for API clients that still post them.

    The score and the tier are absent by design: they are computed. A client that
    could post a tier could set one the arithmetic never produced.
    """

    questionnaire_id: uuid.UUID | None = None
    answers: dict[str, TieringAnswerIn] | None = None
    data_sensitivity: int = Field(default=0, ge=0, le=4)
    business_criticality: int = Field(default=0, ge=0, le=4)
    system_access: int = Field(default=0, ge=0, le=4)
    regulatory_scope: int = Field(default=0, ge=0, le=4)
    fourth_party_reliance: int = Field(default=0, ge=0, le=4)
    override_tier: str | None = None
    override_justification: str | None = Field(default=None, max_length=4000)


class AdvanceWrite(_Request):
    note: str | None = Field(default=None, max_length=4000)


class SendBackWrite(_Request):
    to_stage: str
    reason: str = Field(min_length=1, max_length=4000)


class SkipWrite(_Request):
    reason: str = Field(min_length=1, max_length=4000)


class ExitCheckOut(_Response):
    code: str
    label: str
    satisfied: bool | None
    """Three-valued. ``null`` means the module that answers this is not built yet —
    render it as pending, never as a tick and never as a failure."""
    detail: str | None
    clears_with: str | None
    clears_id: uuid.UUID | None


class StageOut(_Response):
    id: uuid.UUID
    engagement_id: uuid.UUID
    cycle: int
    stage: str
    label: str
    status: str
    is_gate: bool
    is_required: bool
    entered_at: UtcDateTime | None
    exited_at: UtcDateTime | None
    skipped_reason: str | None
    skipped_by_policy: str | None
    checks: list[ExitCheckOut]
    blockers: list[ExitCheckOut]
    pending: list[ExitCheckOut]
    allowed_transitions: list[str]


class TieringFactorOut(_Response):
    key: str
    label: str
    answer: int
    clamped: int
    weight: float
    points: float
    max_points: float


class TieringQuestionOut(_Response):
    id: str
    prompt: str
    section: str
    answer_labels: list[str]
    comment: str | None
    points: float
    max_points: float
    floor_tier: str | None
    counted: bool


class TieringOut(_Response):
    id: uuid.UUID
    engagement_id: uuid.UUID
    cycle: int
    factors: list[TieringFactorOut]
    questionnaire_id: uuid.UUID | None
    questionnaire_name: str | None
    questions: list[TieringQuestionOut]
    answers: dict[str, object]
    floor_tier: str | None
    score: float
    computed_tier: str
    override_tier: str | None
    override_justification: str | None
    effective_tier: str
    thresholds: dict[str, float]
    points_to_higher_tier: float | None
    points_to_lower_tier: float | None
    assessed_by_name: str | None
    assessed_at: UtcDateTime | None


class AttentionCountOut(_Response):
    code: str
    label: str
    count: int


class ResidualVendorOut(_Response):
    id: uuid.UUID
    name: str
    tier: str | None
    residual_score: float
    grade: str | None


class SummaryOut(_Response):
    """The portfolio picture the overview reads, in one round trip."""

    total: int
    mine: int
    by_tier: dict[str, int]
    by_status: dict[str, int]
    attention: list[AttentionCountOut]
    coverage_in_scope: int
    coverage_current: int
    findings_by_severity: dict[str, int]
    findings_open: int
    findings_overdue: int
    intake_pending: int
    highest_residual: list[ResidualVendorOut]


class TransitionOut(_Response):
    """One movement of the review: advance, send-back or skip, with its reason."""

    id: uuid.UUID
    engagement_id: uuid.UUID
    cycle: int
    action: str
    from_stage: str | None
    to_stage: str | None
    reason: str | None
    actor: str | None
    occurred_at: UtcDateTime


class AssessmentSummaryOut(_Response):
    """A questionnaire as a list row — no responses, no findings."""

    id: uuid.UUID
    engagement_id: uuid.UUID
    cycle: int
    kind: str
    review_format: str
    status: str
    due_date: date | None
    residual_score: float | None
    grade: str | None
    question_count: int
    answered_count: int
    submitted_at: UtcDateTime | None
    created_at: UtcDateTime
    questionnaire_id: uuid.UUID | None
    questionnaire_name: str | None


class VendorDetailOut(VendorOut):
    engagements: list[EngagementOut]
    contacts: list[ContactOut]
    duplicates: list[DuplicateMatchOut]
    stages: list[StageOut]
    tierings: list[TieringOut]
    approvals: list[ApprovalOut] = Field(default_factory=list)
    documents: list[DocumentOut] = Field(default_factory=list)
    contracts: list[ContractOut] = Field(default_factory=list)
    soc_reviews: list[SocReviewOut] = Field(default_factory=list)
    subprocessors: list[SubprocessorOut] = Field(default_factory=list)
    assessments: list[AssessmentSummaryOut] = Field(default_factory=list)
    transitions: list[TransitionOut] = Field(default_factory=list)


class VendorPageOut(_Response):
    items: list[VendorOut]
    total: int


class VendorFacetsOut(_Response):
    vendor_types: list[str]
    statuses: list[str]
    tiers: list[str]
    classifications: list[str]
    contact_types: list[str]
    business_units: list[str]
    # The lifecycle vocabulary, served rather than duplicated in TypeScript.
    stages: list[dict[str, object]]
    skip_matrix_by_tier: dict[str, list[str]]
    tiering_factors: list[dict[str, object]]
    reviewer_roles_by_tier: dict[str, list[str]]
    tier_thresholds: dict[str, float]
    policy_is_customised: bool
    risk_domains: list[dict[str, str]]


class DuplicateCheckOut(_Response):
    matches: list[DuplicateMatchOut]


# -- the questionnaire and its findings (section 3) ---------------------------


class IssueQuestionnaireWrite(_Request):
    contact_id: uuid.UUID | None = None
    """Which contact to send to. Omitted, the vendor's ``portal`` contact is used."""
    due_date: date | None = None
    bank_code: str | None = None
    questionnaire_id: uuid.UUID | None = None
    """The questionnaire to send. Omitted, the one set as default for the tier."""


class IssuedQuestionnaireOut(_Response):
    """The response that carries the portal link.

    ``portal_url`` contains the only copy of the token that will ever exist: the
    database holds a hash, so this response cannot be reproduced afterwards.
    """

    assessment_id: uuid.UUID
    contact_email: str
    question_count: int
    due_date: date | None
    portal_url: str


class ResponseOut(_Response):
    id: uuid.UUID
    question_id: uuid.UUID
    question_code: str
    body: str
    domain: str
    domain_label: str
    scope_level: str
    answer_type: str
    weight: float
    critical_control: bool
    non_negotiable: bool
    evidence_required: bool
    framework_refs: list[str]
    answer: str | None
    implementation_notes: str | None
    na_justification: str | None
    evidence_id: uuid.UUID | None
    answered_at: UtcDateTime | None
    section: str
    help_text: str | None
    options: list[dict[str, object]]
    value: str | float | list[str] | None
    answer_labels: list[str]
    flagged: bool
    required: bool
    evidence: str
    visible: bool
    owes_evidence: bool


class FindingOut(_Response):
    id: uuid.UUID
    vendor_id: uuid.UUID
    vendor_name: str | None
    vendor_tier: str | None
    """Only the cross-vendor queue fills this in — see FindingView."""

    assessment_id: uuid.UUID | None
    question_id: uuid.UUID | None
    title: str
    detail: str
    finding_source: str
    severity: str
    status: str
    treatment: str
    is_blocking: bool
    sla_due: date | None
    owner_membership_id: uuid.UUID | None
    owner_name: str | None
    task_id: uuid.UUID | None
    accepted_until: date | None
    accepted_rationale: str | None
    closed_at: UtcDateTime | None
    promoted_risk_id: uuid.UUID | None
    """The seam to the risk register. Always null: `modules/risk` has no tables,
    so the column ships and the promotion action does not."""
    created_at: UtcDateTime


class FindingPageOut(_Response):
    items: list[FindingOut]
    total: int


class AssessmentOut(_Response):
    id: uuid.UUID
    vendor_id: uuid.UUID
    engagement_id: uuid.UUID
    cycle: int
    kind: str
    review_format: str
    assessment_domain: str
    status: str
    # No decision field: the approval row is authoritative (V3).
    due_date: date | None
    residual_score: float | None
    grade: str | None
    domain_scores: dict[str, object]
    score_steps: list[object]
    scope: dict[str, object]
    question_count: int
    answered_count: int
    unanswered_count: int
    missing_evidence_count: int
    submitted_at: UtcDateTime | None
    responses: list[ResponseOut]
    findings: list[FindingOut]
    portal_link_live: bool
    portal_link_expires_at: UtcDateTime | None
    created_at: UtcDateTime
    updated_at: UtcDateTime


class RemediateWrite(_Request):
    owner_membership_id: uuid.UUID | None = None


class AcceptFindingWrite(_Request):
    until: date
    rationale: str = Field(min_length=1, max_length=4000)


class CloseFindingWrite(_Request):
    note: str | None = Field(default=None, max_length=4000)


# -- the decision, the paperwork and the exit (section 4) ---------------------


class ConditionWrite(_Request):
    description: str = Field(min_length=1, max_length=2000)
    owner_membership_id: uuid.UUID | None = None
    due_date: date | None = None


class DecisionWrite(_Request):
    """The gate decision. Four-valued (V3), and the rationale is not optional."""

    decision: str
    rationale: str = Field(min_length=1, max_length=8000)
    conditions: list[ConditionWrite] = Field(default_factory=list)


class ConditionCloseWrite(_Request):
    status: str
    waived_reason: str | None = Field(default=None, max_length=4000)


class ConditionOut(_Response):
    id: uuid.UUID
    approval_id: uuid.UUID
    description: str
    owner_membership_id: uuid.UUID | None
    owner_name: str | None
    due_date: date | None
    status: str
    task_id: uuid.UUID | None
    waived_reason: str | None


class ApprovalOut(_Response):
    id: uuid.UUID
    engagement_id: uuid.UUID
    cycle: int
    stage_id: uuid.UUID | None
    decision: str
    rationale: str
    decided_by_membership_id: uuid.UUID | None
    decided_by_name: str | None
    excluded_membership_ids: list[str]
    decided_at: UtcDateTime
    conditions: list[ConditionOut]


class ApproverOut(_Response):
    membership_id: uuid.UUID
    name: str
    is_designated_approver: bool
    disqualified_reason: str | None
    """Why this person may not decide. Present so the picker can grey the name and
    explain, rather than refusing after a rationale has been written."""


class ApproverPageOut(_Response):
    items: list[ApproverOut]


class DocumentWrite(_Request):
    title: str = Field(min_length=1, max_length=300)
    doc_type: str = "soc_report"
    issue_date: date | None = None
    valid_until: date | None = None
    collection_status: str = "requested"
    evidence_id: uuid.UUID | None = None


class DocumentOut(_Response):
    id: uuid.UUID
    vendor_id: uuid.UUID
    doc_type: str
    title: str
    issue_date: date | None
    valid_until: date | None
    expires_in_days: int | None
    is_expired: bool
    collection_status: str
    review_notes: str | None
    reviewed_by_name: str | None
    reviewed_at: UtcDateTime | None
    evidence_id: uuid.UUID | None


class SocReviewWrite(_Request):
    report_kind: str = "soc2"
    report_type: str = "type_ii"
    document_id: uuid.UUID | None = None
    audit_period_start: date | None = None
    audit_period_end: date | None = None
    tsc_included: list[str] = Field(default_factory=list)
    opinion: str = "unqualified"
    bridge_letter_received: bool = False
    findings_material: bool = False
    cuec_reviewed: bool = False
    cuec_notes: str | None = Field(default=None, max_length=8000)
    subservice_orgs: str | None = Field(default=None, max_length=4000)
    cpa_firm: str | None = Field(default=None, max_length=300)


class SocReviewOut(_Response):
    id: uuid.UUID
    vendor_id: uuid.UUID
    document_id: uuid.UUID | None
    report_kind: str
    report_type: str
    audit_period_start: date | None
    audit_period_end: date | None
    tsc_included: list[str]
    opinion: str
    bridge_letter_received: bool
    findings_material: bool
    cuec_reviewed: bool
    cuec_notes: str | None
    subservice_orgs: str | None
    cpa_firm: str | None
    reviewed_at: UtcDateTime | None
    period_is_stale: bool
    needs_bridge_letter: bool


class ContractWrite(_Request):
    title: str = Field(min_length=1, max_length=300)
    contract_type: str = "master"
    engagement_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    renewal_date: date | None = None
    auto_renew: bool = False
    notice_period_days: int | None = Field(default=None, ge=0, le=1095)
    breach_notification_hours: int | None = Field(default=None, ge=0, le=8760)
    right_to_audit: bool = False
    subprocessor_terms: bool = False
    exit_data_return_clause: bool = False
    value: float | None = None
    status: str = "draft"


class ContractOut(_Response):
    id: uuid.UUID
    vendor_id: uuid.UUID
    engagement_id: uuid.UUID | None
    contract_type: str
    title: str
    start_date: date | None
    end_date: date | None
    renewal_date: date | None
    renews_in_days: int | None
    auto_renew: bool
    notice_period_days: int | None
    breach_notification_hours: int | None
    right_to_audit: bool
    subprocessor_terms: bool
    exit_data_return_clause: bool
    value: float | None
    status: str
    clauses_present: int
    notice_deadline: date | None


class SubprocessorWrite(_Request):
    name: str = Field(min_length=1, max_length=300)
    service: str = Field(default="", max_length=4000)
    data_location: str | None = Field(default=None, max_length=300)
    provenance: str = "vendor_declared"
    linked_vendor_id: uuid.UUID | None = None
    notification_obligation: str | None = Field(default=None, max_length=2000)


class SubprocessorOut(_Response):
    id: uuid.UUID
    vendor_id: uuid.UUID
    name: str
    service: str
    data_location: str | None
    provenance: str
    linked_vendor_id: uuid.UUID | None
    notification_obligation: str | None
    status: str
    also_used_by_vendors: int


class SubprocessorPageOut(_Response):
    items: list[SubprocessorOut]


class IntakeWrite(_Request):
    vendor_name: str = Field(min_length=1, max_length=300)
    department: str | None = Field(default=None, max_length=300)
    proposed_service: str = Field(default="", max_length=8000)
    data_types_shared: list[str] = Field(default_factory=list)
    urgency: str = "normal"


class IntakeDecisionWrite(_Request):
    approve: bool
    reason: str | None = Field(default=None, max_length=4000)


class IntakeOut(_Response):
    id: uuid.UUID
    vendor_name: str
    department: str | None
    proposed_service: str
    data_types_shared: list[str]
    urgency: str
    screening_status: str
    decision: str
    decision_reason: str | None
    requested_by_name: str | None
    decided_by_name: str | None
    decided_at: UtcDateTime | None
    created_vendor_id: uuid.UUID | None
    duplicates: list[DuplicateMatchOut]
    created_at: UtcDateTime


class IntakePageOut(_Response):
    items: list[IntakeOut]
    total: int


class RosterWrite(_Request):
    role: str
    membership_id: uuid.UUID


class RosterOut(_Response):
    roles: dict[str, list[uuid.UUID]]


class OffboardWrite(_Request):
    reason: str = Field(min_length=1, max_length=4000)
    engagement_id: uuid.UUID | None = None
    """Omitted means the whole relationship. Ending one department's use of a
    vendor is not terminating the vendor."""


class OffboardingCompletionWrite(_Request):
    access_revoked: bool = False
    data_returned: bool = False
    contract_provisions_reviewed: bool = False
    final_payments_settled: bool = False
    certificate_evidence_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=8000)
    complete: bool = False


# -- questionnaires a tenant builds -------------------------------------------


class QuestionOptionIn(_Request):
    key: str = Field(default="", max_length=40)
    """Stable within the question. Blank on a new option; the service assigns one."""
    label: str = Field(min_length=1, max_length=200)
    score: float = Field(default=0, ge=0, le=100)
    flag: bool = False
    not_applicable: bool = False
    comment_required: bool = False
    min_tier: str | None = None


class QuestionConditionIn(_Request):
    question_id: uuid.UUID
    option_keys: list[str] = Field(min_length=1, max_length=50)


class QuestionWrite(_Request):
    prompt: str = Field(min_length=1, max_length=1000)
    answer_type: str
    section: str = Field(default="General", max_length=80)
    help_text: str | None = Field(default=None, max_length=2000)
    options: list[QuestionOptionIn] = Field(default_factory=list, max_length=50)
    required: bool = True
    evidence: str = "none"
    evidence_on: list[str] = Field(default_factory=list, max_length=50)
    weight: float = Field(default=1.0, ge=0, le=100)
    domain: str | None = None
    critical: bool = False
    blocking: bool = False
    condition: QuestionConditionIn | None = None


class QuestionCreateWrite(QuestionWrite):
    after_question_id: uuid.UUID | None = None
    """Insert after this question. Omitted, the question goes on the end."""


class QuestionnaireCreateWrite(_Request):
    purpose: str
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    library_code: str | None = Field(default=None, max_length=100)
    preset: str | None = Field(default=None, max_length=40)


class QuestionnaireWrite(_Request):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    default_tiers: list[str] = Field(default_factory=list, max_length=4)
    tier_thresholds: dict[str, float] = Field(default_factory=dict)
    is_default: bool = False


class QuestionnaireStatusWrite(_Request):
    status: str


class QuestionImportWrite(_Request):
    library_question_ids: list[uuid.UUID] = Field(min_length=1, max_length=300)


class QuestionOrderWrite(_Request):
    question_ids: list[uuid.UUID] = Field(min_length=1, max_length=300)


class QuestionOut(_Response):
    id: uuid.UUID
    position: int
    section: str
    prompt: str
    help_text: str | None
    answer_type: str
    options: list[dict[str, object]]
    required: bool
    evidence: str
    evidence_on: list[str]
    weight: float
    domain: str | None
    domain_label: str | None
    critical: bool
    blocking: bool
    condition: dict[str, object]
    framework_refs: list[str]
    library_code: str | None


class QuestionnaireSummaryOut(_Response):
    id: uuid.UUID
    purpose: str
    name: str
    description: str | None
    status: str
    is_default: bool
    default_tiers: list[str]
    question_count: int
    section_count: int
    library_code: str | None
    updated_at: UtcDateTime
    updated_by_name: str | None


class QuestionnaireOut(QuestionnaireSummaryOut):
    tier_thresholds: dict[str, float]
    questions: list[QuestionOut]


class LibraryQuestionOut(_Response):
    id: uuid.UUID
    code: str
    section: str
    prompt: str
    help_text: str | None
    answer_type: str
    options: list[dict[str, object]]
    required: bool
    evidence: str
    weight: float
    domain: str | None
    domain_label: str | None
    critical: bool
    blocking: bool
    scope_level: str
    framework_refs: list[str]
    condition_code: str | None


class LibraryPresetOut(_Response):
    key: str
    label: str
    question_count: int


class LibraryTemplateOut(_Response):
    code: str
    name: str
    description: str | None
    purpose: str
    version: str
    presets: list[LibraryPresetOut]
    questions: list[LibraryQuestionOut]
