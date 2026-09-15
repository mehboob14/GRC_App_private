"""Vendor register — reads, writes, and the implicit default engagement.

Section 1 of openspec/changes/week5-vendor-risk. The rules that live here rather
than in the database:

- **Every vendor has at least one engagement.** ``create_vendor`` writes the
  default in the same transaction (V10), so nothing downstream special-cases a
  vendor with no engagement.
- **Duplicate detection warns, it never blocks** (ER ¶90). Two real subsidiaries
  share a trading name; a unique constraint would refuse a legitimate record, so
  the near-matches come back on the created vendor and a person decides.
- **The vendor's tier / residual / grade / contract value are recomputed from its
  engagements**, never written directly. ``_recache`` is the only writer, and it
  takes the worst engagement so the register ranks on the worst case.

Nothing here advances a lifecycle: the twelve-stage machine is section 2, and a
vendor created now sits at ``requested`` until it lands.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any, Final

import structlog
from sqlalchemy import false as sa_false
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core import ratelimit
from verity.core.config import get_settings
from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.modules.audit.service import (
    Actor,
    AuditService,
    Membership,
    System,
    audit_service,
)
from verity.modules.vendors import lifecycle, scoring
from verity.modules.vendors.models import (
    APPROVAL_DECISIONS,
    BUNDLE_BY_TIER,
    CONDITION_STATUSES,
    CONTACT_TYPES,
    CONTRACT_STATUSES,
    CONTRACT_TYPES,
    DATA_CLASSIFICATIONS,
    DEFAULT_ENGAGEMENT_NAME,
    DOC_TYPES,
    FINDING_SEVERITIES,
    LIFECYCLE_STATUSES,
    OPEN_FINDING_STATUSES,
    RISK_DOMAIN_LABELS,
    ROSTER_ROLES,
    SOC_OPINIONS,
    SOC_REPORT_KINDS,
    SOC_REPORT_TYPES,
    SUBPROCESSOR_PROVENANCE,
    TIERS,
    URGENCIES,
    VENDOR_TYPES,
    QuestionnaireQuestion,
    QuestionnaireTemplate,
    Vendor,
    VendorApproval,
    VendorApprovalCondition,
    VendorAssessment,
    VendorAssessmentResponse,
    VendorContact,
    VendorContract,
    VendorDocument,
    VendorEngagement,
    VendorFinding,
    VendorIntakeRequest,
    VendorOffboarding,
    VendorPortalToken,
    VendorSla,
    VendorSocReportReview,
    VendorStage,
    VendorSubprocessor,
    VendorTeamRosterEntry,
    VendorTieringAssessment,
    VendorTieringPolicy,
    VendorTransition,
)
from verity.modules.vendors.questionnaires import (
    AskedQuestion,
    answer_labels,
    asked_from_bank,
    asked_from_snapshot,
    is_answered,
    normalize_answer,
    owes_evidence,
    picked_options,
    questionnaire_service,
    response_value,
    visible_keys,
)
from verity.shared.ids import uuid7

logger: Final = structlog.get_logger(__name__)

# -- shared rules (the client is served these; it never hardcodes them) -------

TIER_RANK: Final[dict[str, int]] = {tier: rank for rank, tier in enumerate(TIERS)}
"""Worst-first. ``critical`` is 0, so ``min`` over this picks the worst tier."""

_SNAPSHOT: Final[tuple[str, ...]] = (
    "name",
    "vendor_type",
    "lifecycle_status",
    "data_classification",
    "stores_pii",
    "business_owner_membership_id",
)

_ENGAGEMENT_SNAPSHOT: Final[tuple[str, ...]] = ("name", "status", "tier", "business_unit")

# Reader-facing copy reused across several raises in this module.
_VENDOR_GONE: Final = "This vendor no longer exists. It may have been deleted."
_ENGAGEMENT_GONE: Final = "This engagement no longer exists. It may have been deleted."
_STAGE_GONE: Final = (
    "This lifecycle stage no longer exists. The review may have moved on. "
    "Refresh the page to see where it is now."
)

_NOISE = re.compile(
    r"\b(inc|llc|ltd|limited|corp|corporation|gmbh|plc|co|sa|bv|ag|pty)\b|[^a-z0-9]+"
)


def _fingerprint(name: str) -> str:
    """A comparable form of a trading name: lowercased, legal suffixes dropped.

    "Acme, Inc." and "ACME Corporation" both become "acme", which is what makes
    the duplicate warning fire on the case it exists for.
    """
    return _NOISE.sub("", name.lower())


def _domain(website: str | None) -> str | None:
    """The registrable-looking part of a URL, for matching two spellings of one site."""
    if not website:
        return None
    host = website.strip().lower()
    host = re.sub(r"^[a-z]+://", "", host).split("/")[0].split("?")[0]
    return re.sub(r"^www\.", "", host) or None


# -- views (returned to the router; never ORM rows) ---------------------------


@dataclass(frozen=True, slots=True)
class EngagementView:
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
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ContactView:
    id: uuid.UUID
    vendor_id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    contact_type: str


@dataclass(frozen=True, slots=True)
class OwnershipView:
    business_owner_membership_id: uuid.UUID | None
    business_owner_name: str | None
    security_owner_membership_id: uuid.UUID | None
    security_owner_name: str | None
    relationship_owner_membership_id: uuid.UUID | None
    relationship_owner_name: str | None


@dataclass(frozen=True, slots=True)
class DuplicateMatch:
    """A vendor that looks like the one just saved. A warning, never a refusal."""

    id: uuid.UUID
    name: str
    reason: str


@dataclass(frozen=True)
class VendorView:
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
    ownership: OwnershipView
    next_reassessment_on: date | None
    tags: list[str]
    source: str
    created_at: datetime
    updated_at: datetime
    engagement_count: int
    contact_count: int
    attention_code: str | None = None
    """What this vendor is waiting on -- see ``ATTENTION_CODES``. None means
    nothing is outstanding, which the register renders as its healthy line."""


@dataclass(frozen=True, slots=True)
class ResidualVendor:
    """A vendor on the portfolio's highest residual risk list."""

    id: uuid.UUID
    name: str
    tier: str | None
    residual_score: float
    grade: str | None


@dataclass(frozen=True, slots=True)
class AttentionCount:
    """One thing the portfolio is waiting on, and how many vendors are on it."""

    code: str
    label: str
    count: int


@dataclass(frozen=True, slots=True)
class SummaryView:
    """The portfolio in one object. Every field is a count somebody acts on."""

    total: int
    mine: int
    by_tier: dict[str, int]
    by_status: dict[str, int]
    attention: list[AttentionCount]
    coverage_in_scope: int
    """Vendors a reassessment cadence applies to at all."""

    coverage_current: int
    """Of those, the ones inside their window."""

    findings_by_severity: dict[str, int]
    findings_open: int
    findings_overdue: int
    intake_pending: int
    highest_residual: list[ResidualVendor]
    """Live vendors with a scored assessment, worst residual score first, top five."""


@dataclass(frozen=True, slots=True)
class TransitionView:
    """One movement of the review, in the shape the trail renders.

    ``vendor_transitions`` has been written on every advance, send-back and skip
    since section 2 and read by exactly one thing: the gate's freshness check.
    The send-back dialog promises "whoever picks it up sees your reason" -- this
    is what makes that true.
    """

    id: uuid.UUID
    engagement_id: uuid.UUID
    cycle: int
    action: str
    from_stage: str | None
    to_stage: str | None
    reason: str | None
    actor: str | None
    """Resolved name, or None for a System write -- the interface says so."""

    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class AssessmentSummaryView:
    """Enough to list a questionnaire without loading its answers.

    The full ``AssessmentView`` carries every response and every finding, which
    is the right payload for one assessment and the wrong one for a list of
    them. This is what the assessments panel needs to draw a row; opening the
    row fetches the rest.
    """

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
    submitted_at: datetime | None
    created_at: datetime
    questionnaire_id: uuid.UUID | None
    questionnaire_name: str | None


@dataclass(frozen=True)
class VendorDetailView(VendorView):
    engagements: list[EngagementView] = field(default_factory=list)
    contacts: list[ContactView] = field(default_factory=list)
    duplicates: list[DuplicateMatch] = field(default_factory=list)
    # Flat lists carrying engagement_id, not nested under the engagement: the
    # rail and the tiering panel are separate screens and each wants its own
    # collection whole.
    stages: list[StageView] = field(default_factory=list)
    tierings: list[TieringView] = field(default_factory=list)
    approvals: list[ApprovalView] = field(default_factory=list)
    documents: list[DocumentView] = field(default_factory=list)
    contracts: list[ContractView] = field(default_factory=list)
    soc_reviews: list[SocReviewView] = field(default_factory=list)
    subprocessors: list[SubprocessorView] = field(default_factory=list)
    assessments: list[AssessmentSummaryView] = field(default_factory=list)
    transitions: list[TransitionView] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class VendorRef:
    """The lightweight vendor facts a sibling module needs (rule 4).

    Assets links a supplying third party and evidence names the vendor a document
    came from; neither should pay for ownership resolution or engagement loading.
    """

    id: uuid.UUID
    name: str
    tier: str | None
    lifecycle_status: str


@dataclass(frozen=True, slots=True)
class VendorFilters:
    search: str | None = None
    vendor_type: str | None = None
    statuses: tuple[str, ...] = ()
    tiers: tuple[str, ...] = ()
    classifications: tuple[str, ...] = ()
    business_units: tuple[str, ...] = ()
    owner: str | None = None  # membership_id, "me", or "unassigned"
    stores_pii: bool = False
    attention: tuple[str, ...] = ()
    """Attention codes -- see ``ATTENTION_CODES``. Applied after the scan rather
    than in SQL, because the codes are priority-ordered rules over several
    columns and reproducing that ordering as a WHERE clause would be a second
    implementation of it."""


@dataclass(frozen=True, slots=True)
class VendorInput:
    """The fields create/edit accept. The cached risk columns are derived, so the
    caller never supplies tier, residual score, grade or contract value."""

    name: str
    vendor_type: str = "vendor"
    industry: str | None = None
    website: str | None = None
    business_unit: str | None = None
    services_provided: str = ""
    stores_pii: bool = False
    data_location: str | None = None
    data_types_in_scope: tuple[str, ...] = ()
    systems_in_scope: tuple[str, ...] = ()
    data_classification: str | None = None
    tags: tuple[str, ...] = ()
    business_owner_membership_id: uuid.UUID | None = None
    security_owner_membership_id: uuid.UUID | None = None
    relationship_owner_membership_id: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class EngagementInput:
    name: str
    service_description: str = ""
    business_unit: str | None = None
    internal_owner_membership_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None


@dataclass(frozen=True, slots=True)
class ContactInput:
    name: str
    email: str | None = None
    phone: str | None = None
    contact_type: str = "commercial"


@dataclass(frozen=True, slots=True)
class ResolvedPolicy:
    """The tenant's tiering configuration, defaults already merged in."""

    weights: dict[str, float]
    thresholds: dict[str, float]
    skip_matrix: dict[str, tuple[str, ...]]
    reviewer_roles: dict[str, tuple[str, ...]]
    cadence_days: dict[str, int]
    is_customised: bool
    """False means every value here is a shipped default. The settings screen says
    so rather than presenting the defaults as choices somebody made."""


@dataclass(frozen=True, slots=True)
class TieringAnswers:
    """The five factor answers, plus an optional human override of the result."""

    data_sensitivity: int = 0
    business_criticality: int = 0
    system_access: int = 0
    regulatory_scope: int = 0
    fourth_party_reliance: int = 0
    override_tier: str | None = None
    override_justification: str | None = None

    def as_dict(self) -> dict[str, int]:
        return {key: getattr(self, key) for key in scoring.FACTOR_KEYS}


@dataclass(frozen=True, slots=True)
class QuestionnaireTieringInput:
    """Answers to a tiering questionnaire, plus an optional human override.

    ``answers`` maps a question id to ``{"value": ..., "comment": ...}``. Omitting
    ``questionnaire_id`` uses the tenant's default tiering questionnaire.
    """

    answers: dict[str, Any]
    questionnaire_id: uuid.UUID | None = None
    override_tier: str | None = None
    override_justification: str | None = None


@dataclass(frozen=True, slots=True)
class TieringQuestionView:
    """One question's line in a questionnaire tiering, as the panel draws it."""

    id: str
    prompt: str
    section: str
    answer_labels: list[str]
    comment: str | None
    points: float
    max_points: float
    floor_tier: str | None
    counted: bool


@dataclass(frozen=True, slots=True)
class TieringView:
    """One scored run with its arithmetic recomputed from the stored answers.

    The breakdown is derived on read from the answers and the run's own
    ``policy_snapshot``, never from today's policy — which is the whole reason
    that snapshot column exists.
    """

    id: uuid.UUID
    engagement_id: uuid.UUID
    cycle: int
    factors: list[scoring.TieringFactor]
    score: float
    computed_tier: str
    override_tier: str | None
    override_justification: str | None
    effective_tier: str
    thresholds: dict[str, float]
    points_to_higher_tier: float | None
    points_to_lower_tier: float | None
    assessed_by_name: str | None
    assessed_at: datetime | None
    questionnaire_id: uuid.UUID | None
    """Set on a questionnaire run. Its lines are in ``questions``; ``factors`` is empty."""
    questionnaire_name: str | None
    questions: list[TieringQuestionView]
    answers: dict[str, Any]
    """The stored answers, so a re-tier opens with them filled in."""
    floor_tier: str | None
    """The tier an option's minimum lifted this run to, when the score alone would not."""


@dataclass(frozen=True, slots=True)
class StageView:
    """One row of the stage rail, with its exit checks already evaluated."""

    id: uuid.UUID
    engagement_id: uuid.UUID
    cycle: int
    stage: str
    label: str
    status: str
    is_gate: bool
    is_required: bool
    entered_at: datetime | None
    exited_at: datetime | None
    skipped_reason: str | None
    skipped_by_policy: str | None
    checks: list[lifecycle.ExitCheck]
    blockers: list[lifecycle.ExitCheck]
    pending: list[lifecycle.ExitCheck]
    """Checks whose answering module is not built yet. Never blocking, never a
    tick either — the distinction rule 7 draws between error and fail."""
    allowed_transitions: list[str]
    """Served so the client never reimplements the machine in TypeScript."""


# -- the review (section 3) ---------------------------------------------------

_QUESTIONNAIRE_DUE_DAYS: Final = 21
_PORTAL_TOKEN_DAYS: Final = 30
"""The link outlives the due date by a little, so a vendor who is late can still
answer rather than having to ask for a new link — which is friction that produces
an unanswered questionnaire, not a more secure one."""

_FINDING_SLA_DAYS: Final[dict[str, int]] = {
    "critical": 7,
    "high": 30,
    "medium": 90,
    "low": 180,
}

_TASK_PRIORITY: Final[dict[str, str]] = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
}

_FINDING_SNAPSHOT: Final[tuple[str, ...]] = (
    "title",
    "severity",
    "status",
    "treatment",
    "is_blocking",
    "owner_membership_id",
    "task_id",
    "accepted_until",
)

_ASSESSMENT_GONE: Final = "This questionnaire no longer exists. It may have been deleted."
_FINDING_GONE: Final = "This finding no longer exists. It may have been closed and removed."


def _finding_severity(question: AskedQuestion) -> str:
    """How bad a ``no`` to this question is.

    Driven by what the question *is*, not by who answered it: a missing critical
    control is critical whoever the vendor is, and a nice-to-have is low however
    important the vendor.
    """
    if question.critical:
        return "critical"
    if question.weight >= _HIGH_WEIGHT:
        return "high"
    if question.weight >= _MEDIUM_WEIGHT:
        return "medium"
    return "low"


_HIGH_WEIGHT: Final = 2.0
_MEDIUM_WEIGHT: Final = 1.5


def _finding_title(question: AskedQuestion) -> str:
    """A title that names the gap, not the question.

    "Access control: MFA on privileged access" is something a reader can act on;
    the question text repeated back is something they have to translate first.
    A question a tenant wrote has no such code, so its own wording stands in.
    """
    name = question.code if question.from_bank else question.prompt
    return f"{RISK_DOMAIN_LABELS[question.domain]}: {name}"[:300]


def _portal_url(token: str) -> str:
    base = get_settings().frontend_base_url.rstrip("/")
    return f"{base}/vendor-portal/{token}"


@dataclass(frozen=True, slots=True)
class IssuedQuestionnaire:
    """What issuing returns. ``portal_url`` contains the only copy of the token."""

    assessment_id: uuid.UUID
    contact_email: str
    question_count: int
    due_date: date | None
    portal_url: str


@dataclass(frozen=True, slots=True)
class ResponseView:
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
    answered_at: datetime | None
    section: str
    help_text: str | None
    options: list[dict[str, Any]]
    value: Any
    answer_labels: list[str]
    flagged: bool
    """The answer picked an option marked as a gap."""
    required: bool
    evidence: str
    visible: bool
    """False for a question whose condition the answers did not meet: never asked."""
    owes_evidence: bool


@dataclass(frozen=True, slots=True)
class FindingView:
    id: uuid.UUID
    vendor_id: uuid.UUID
    vendor_name: str | None
    vendor_tier: str | None
    """Same nullability contract as ``vendor_name``: filled only by the
    cross-vendor queue. A medium finding at a critical vendor outranks a high one
    at a low-tier vendor, and the queue could not say which was which."""

    """Populated only by the cross-vendor queue, which is the one screen that
    cannot name the vendor from its own context. Everywhere else a finding is
    already shown under its vendor, so paying for the join would buy nothing."""

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
    closed_at: datetime | None
    promoted_risk_id: uuid.UUID | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AssessmentView:
    id: uuid.UUID
    vendor_id: uuid.UUID
    engagement_id: uuid.UUID
    cycle: int
    kind: str
    review_format: str
    assessment_domain: str
    status: str
    due_date: date | None
    residual_score: float | None
    grade: str | None
    domain_scores: dict[str, Any]
    score_steps: list[Any]
    """The adjustments in the order they applied, including the ones that did not
    fire — the same shape the tiering panel reads."""
    scope: dict[str, Any]
    question_count: int
    answered_count: int
    unanswered_count: int
    missing_evidence_count: int
    submitted_at: datetime | None
    responses: list[ResponseView]
    findings: list[FindingView]
    portal_link_live: bool
    portal_link_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


# -- the decision, the paperwork and the exit (section 4) ---------------------

_CONDITION_GONE: Final = "This condition no longer exists. The approval may have been superseded."
_INTAKE_GONE: Final = "This request no longer exists. It may already have been decided."
_OFFBOARDING_GONE: Final = "This offboarding record no longer exists."

_SOC_PERIOD_STALE_DAYS: Final = 365
"""A SOC report whose audit period ended more than a year ago no longer describes
the vendor you have today, whatever its opinion said."""
_SOC_BRIDGE_AFTER_DAYS: Final = 90
"""Past this gap, the accepted practice is a bridge letter covering the interval
between the period end and now."""

_DOCUMENT_SNAPSHOT: Final[tuple[str, ...]] = (
    "doc_type",
    "title",
    "valid_until",
    "collection_status",
)
_CONTRACT_SNAPSHOT: Final[tuple[str, ...]] = (
    "contract_type",
    "title",
    "status",
    "renewal_date",
    "right_to_audit",
    "exit_data_return_clause",
)


@dataclass(frozen=True, slots=True)
class ConditionInput:
    description: str
    owner_membership_id: uuid.UUID | None = None
    due_date: date | None = None


@dataclass(frozen=True, slots=True)
class ConditionView:
    id: uuid.UUID
    approval_id: uuid.UUID
    description: str
    owner_membership_id: uuid.UUID | None
    owner_name: str | None
    due_date: date | None
    status: str
    task_id: uuid.UUID | None
    waived_reason: str | None


@dataclass(frozen=True, slots=True)
class ApprovalView:
    id: uuid.UUID
    engagement_id: uuid.UUID
    cycle: int
    stage_id: uuid.UUID | None
    decision: str
    rationale: str
    decided_by_membership_id: uuid.UUID | None
    decided_by_name: str | None
    excluded_membership_ids: list[str]
    """Who was barred from deciding, frozen at decision time. The business owner
    can change afterwards, and "was segregation of duties applied here" has to stay
    answerable from the row."""
    decided_at: datetime
    conditions: list[ConditionView]


@dataclass(frozen=True, slots=True)
class ApproverView:
    """A candidate decider, with the reason if they are barred (V4).

    The reason travels with the name so the picker can grey it *and* explain. A
    rule enforced only on submit is learned as an obstacle, after the user has
    already written their rationale.
    """

    membership_id: uuid.UUID
    name: str
    is_designated_approver: bool
    disqualified_reason: str | None


@dataclass(frozen=True, slots=True)
class DocumentInput:
    title: str
    doc_type: str = "soc_report"
    issue_date: date | None = None
    valid_until: date | None = None
    collection_status: str = "requested"
    evidence_id: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class DocumentView:
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
    reviewed_at: datetime | None
    evidence_id: uuid.UUID | None


@dataclass(frozen=True, slots=True)
class SocReviewInput:
    report_kind: str = "soc2"
    report_type: str = "type_ii"
    document_id: uuid.UUID | None = None
    audit_period_start: date | None = None
    audit_period_end: date | None = None
    tsc_included: tuple[str, ...] = ()
    opinion: str = "unqualified"
    bridge_letter_received: bool = False
    findings_material: bool = False
    cuec_reviewed: bool = False
    cuec_notes: str | None = None
    subservice_orgs: str | None = None
    cpa_firm: str | None = None


@dataclass(frozen=True, slots=True)
class SocReviewView:
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
    reviewed_at: datetime | None
    period_is_stale: bool
    needs_bridge_letter: bool


@dataclass(frozen=True, slots=True)
class ContractInput:
    title: str
    contract_type: str = "master"
    engagement_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    renewal_date: date | None = None
    auto_renew: bool = False
    notice_period_days: int | None = None
    breach_notification_hours: int | None = None
    right_to_audit: bool = False
    subprocessor_terms: bool = False
    exit_data_return_clause: bool = False
    value: float | None = None
    status: str = "draft"


@dataclass(frozen=True, slots=True)
class ContractView:
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
    """The last day to give notice before an auto-renewing contract renews itself.
    Derived, because the date somebody actually needs is never the one on the page."""


@dataclass(frozen=True, slots=True)
class SubprocessorInput:
    name: str
    service: str = ""
    data_location: str | None = None
    provenance: str = "vendor_declared"
    linked_vendor_id: uuid.UUID | None = None
    notification_obligation: str | None = None


@dataclass(frozen=True, slots=True)
class SubprocessorView:
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
    """How many other vendors declare this same fourth party. The concentration
    number, and the reason the register links subprocessors to vendor rows."""


@dataclass(frozen=True, slots=True)
class IntakeInput:
    vendor_name: str
    department: str | None = None
    proposed_service: str = ""
    data_types_shared: tuple[str, ...] = ()
    urgency: str = "normal"


@dataclass(frozen=True, slots=True)
class IntakeView:
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
    decided_at: datetime | None
    created_vendor_id: uuid.UUID | None
    duplicates: list[DuplicateMatch]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class OffboardingCompletion:
    access_revoked: bool = False
    data_returned: bool = False
    contract_provisions_reviewed: bool = False
    final_payments_settled: bool = False
    certificate_evidence_id: uuid.UUID | None = None
    notes: str | None = None
    complete: bool = False


# -- service ------------------------------------------------------------------


_SOC_KIND_WORDS: Final[dict[str, str]] = {"soc1": "SOC 1", "soc2": "SOC 2", "soc3": "SOC 3"}
_SOC_TYPE_WORDS: Final[dict[str, str]] = {"type_i": "Type I", "type_ii": "Type II"}
_SOC_OPINION_WORDS: Final[dict[str, str]] = {
    "unqualified": "an unqualified (clean) opinion",
    "qualified": "a qualified opinion, meaning clean except for stated exceptions",
    "adverse": "an adverse opinion, meaning the controls were not operating effectively",
    "disclaimer": "a disclaimer, meaning the auditor could not form an opinion at all",
}


def _soc_finding_detail(data: SocReviewInput) -> str:
    """The finding's body, in words rather than codes.

    A finding is read by whoever has to act on it, which is often not the person
    who recorded the review. ``SOC2 type_ii ... opinion qualified`` is the shape
    of the row, not a sentence, and it reaches the cross-vendor queue where the
    reader has no other context.
    """
    kind = _SOC_KIND_WORDS.get(data.report_kind, data.report_kind.upper())
    report_type = _SOC_TYPE_WORDS.get(data.report_type, data.report_type)
    opinion = _SOC_OPINION_WORDS.get(data.opinion, f"an opinion recorded as {data.opinion}")
    period = (
        f" covering {data.audit_period_start} to {data.audit_period_end}"
        if data.audit_period_start and data.audit_period_end
        else ""
    )
    material = " The exceptions were judged material." if data.findings_material else ""
    return f"The {kind} {report_type}{period} carries {opinion}.{material}"


_VENDOR_OWNED_STATUSES: Final[frozenset[str]] = frozenset({"offboarding", "archived"})
"""The two the vendor row owns outright. Ending the relationship ends every use
of it, so neither is overridden by an engagement that still reads ``active``."""

_STATUS_RANK: Final[dict[str, int]] = {
    "flagged": 0,
    "on_hold": 1,
    "offboarding": 2,
    "terminated": 3,
    "requested": 4,
    "under_review": 5,
    "approved": 6,
    "active": 7,
    "archived": 8,
}
"""Worst first, so a vendor with one flagged engagement reads flagged. Ordered by
what needs attention rather than by lifecycle position: ``requested`` sits above
the two trouble states because an unreviewed vendor is a gap, not an incident."""


_COVERED_TIERS: Final[frozenset[str]] = frozenset({"critical", "high"})
"""The tiers assessment coverage is measured over. Medium and low have cadences
too, but "are our most exposed vendors current" is the question an auditor asks
and the one a single number can honestly answer."""

_CLOSED_STATUSES: Final[frozenset[str]] = frozenset({"terminated", "archived"})


_UNTIERED_RANK: Final = 0.5
"""Between critical (0) and high (1). A vendor with no tier is not the least
urgent thing in the register, it is an unanswered question."""

_SORT_KEYS: Final[dict[str, Callable[[VendorView], Any]]] = {
    "name": lambda v: v.name.lower(),
    "tier": lambda v: TIER_RANK.get(v.tier or "", _UNTIERED_RANK),
    "grade": lambda v: v.current_grade or "ZZ",
    "owner": lambda v: (v.ownership.business_owner_name or "").lower(),
    "reassessment": lambda v: v.next_reassessment_on or date.max,
    "value": lambda v: v.annual_contract_value if v.annual_contract_value is not None else -1.0,
    "status": lambda v: _STATUS_RANK.get(v.lifecycle_status, 9),
}
"""What the register can be ordered by. Absent values sort last in the ascending
direction on purpose -- flipping a column should never fill the first screen
with blanks."""


ATTENTION_CODES: Final[tuple[tuple[str, str], ...]] = (
    ("flagged", "Flagged for review"),
    ("reassessment_overdue", "Reassessment overdue"),
    ("not_tiered", "Not tiered"),
    ("awaiting_gate", "In review"),
    ("on_hold", "On hold"),
    ("weak_grade", "Weak residual grade"),
    ("unowned", "No business owner"),
    ("reassessment_due", "Reassessment due soon"),
    ("offboarding", "Offboarding in progress"),
)
"""What a vendor can be waiting on, worst first, with the words the interface
uses. One vendor gets at most one code -- the first that matches -- because a
work queue that lists a vendor three times is not a queue.

Served rather than reimplemented in TypeScript, for the same reason ``stages``
and ``skip_matrix_by_tier`` are: the moment an overview counts these and the
register labels them, two implementations of one rule set drift."""

_REASSESSMENT_SOON_DAYS: Final = 30
"""Chosen, not derived. There is no "due soon" in the model; this is the window
the interface treats as close enough to plan around."""


def _attention_code(vendor: Vendor, today: date) -> str | None:  # noqa: PLR0911
    """The one thing this vendor is waiting on, or None if nothing is.

    Reads only columns on the vendor row, so it is answerable for a whole
    portfolio in the scan the register already performs. One return per rule,
    in priority order: collapsing them into a lookup would hide the ordering,
    which is the only thing about this function that is a judgement.
    """
    if vendor.lifecycle_status == "flagged":
        return "flagged"
    due = vendor.next_reassessment_on
    if due is not None and due < today:
        return "reassessment_overdue"
    if vendor.tier is None:
        return "not_tiered"
    if vendor.lifecycle_status in {"requested", "under_review"}:
        return "awaiting_gate"
    if vendor.lifecycle_status == "on_hold":
        return "on_hold"
    if vendor.current_grade in {"D", "F"}:
        return "weak_grade"
    if vendor.business_owner_membership_id is None:
        return "unowned"
    if due is not None and (due - today).days <= _REASSESSMENT_SOON_DAYS:
        return "reassessment_due"
    if vendor.lifecycle_status == "offboarding":
        return "offboarding"
    return None


class VendorService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service

    # -- cross-module resolution (rule 4) -------------------------------------

    async def _member_names(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        from verity.modules.iam.service import iam_service  # noqa: PLC0415

        members = await iam_service.list_members(session, tenant_id=tenant_id)
        return {m.membership_id: m.full_name for m in members}

    # -- helpers ---------------------------------------------------------------

    async def _load(
        self, session: AsyncSession, tenant_id: uuid.UUID, vendor_id: uuid.UUID
    ) -> Vendor:
        # populate_existing forces a fresh row so a mutating method that re-renders
        # through here does not read an expired server-computed column.
        vendor = await session.get(Vendor, vendor_id, populate_existing=True)
        if vendor is None or vendor.tenant_id != tenant_id:
            raise NotFound(_VENDOR_GONE, detail=f"vendor {vendor_id}")
        return vendor

    async def _load_engagement(
        self, session: AsyncSession, tenant_id: uuid.UUID, engagement_id: uuid.UUID
    ) -> VendorEngagement:
        engagement = await session.get(VendorEngagement, engagement_id, populate_existing=True)
        if engagement is None or engagement.tenant_id != tenant_id:
            raise NotFound(_ENGAGEMENT_GONE, detail=f"vendor engagement {engagement_id}")
        return engagement

    @staticmethod
    def _clean(value: str | None) -> str | None:
        cleaned = (value or "").strip()
        return cleaned or None

    @staticmethod
    def _require_name(name: str, *, what: str) -> str:
        cleaned = name.strip()
        if not cleaned:
            raise InvalidInput(
                f"Give this {what} a name before saving it.",
                detail=f"a {what} needs a name",
            )
        return cleaned

    @staticmethod
    def _check_vocabulary(value: str | None, allowed: tuple[str, ...], *, field_name: str) -> None:
        """Reject an unknown value here so the caller gets 422 and a readable line.

        The database CHECK is the wall and would raise too, but as an opaque
        integrity error with the constraint name in it.
        """
        if value is not None and value not in allowed:
            raise InvalidInput(
                f"That {field_name.replace('_', ' ')} is not one we recognise. "
                f"Pick one of: {', '.join(allowed)}.",
                detail=f"{field_name}={value!r} is not in {allowed}",
            )

    def _assign(self, vendor: Vendor, data: VendorInput) -> None:
        self._check_vocabulary(data.vendor_type, VENDOR_TYPES, field_name="vendor_type")
        self._check_vocabulary(
            data.data_classification, DATA_CLASSIFICATIONS, field_name="data_classification"
        )
        vendor.name = self._require_name(data.name, what="vendor")
        vendor.vendor_type = data.vendor_type
        vendor.industry = self._clean(data.industry)
        vendor.website = self._clean(data.website)
        vendor.business_unit = self._clean(data.business_unit)
        vendor.services_provided = data.services_provided.strip()
        vendor.stores_pii = data.stores_pii
        vendor.data_location = self._clean(data.data_location)
        vendor.data_types_in_scope = list(data.data_types_in_scope)
        # Trimmed, blanks dropped, first spelling kept: "AWS" and "aws " are one system.
        systems: dict[str, str] = {}
        for system in data.systems_in_scope:
            if system.strip():
                systems.setdefault(system.strip().lower(), system.strip())
        vendor.systems_in_scope = list(systems.values())
        vendor.data_classification = data.data_classification
        vendor.tags = list(data.tags)
        vendor.business_owner_membership_id = data.business_owner_membership_id
        vendor.security_owner_membership_id = data.security_owner_membership_id
        vendor.relationship_owner_membership_id = data.relationship_owner_membership_id

    async def _engagements_of(
        self, session: AsyncSession, tenant_id: uuid.UUID, *vendor_ids: uuid.UUID
    ) -> dict[uuid.UUID, list[VendorEngagement]]:
        if not vendor_ids:
            return {}
        stmt = (
            select(VendorEngagement)
            .where(VendorEngagement.tenant_id == tenant_id)
            .where(VendorEngagement.vendor_id.in_(list(vendor_ids)))
            .order_by(VendorEngagement.created_at)
        )
        grouped: dict[uuid.UUID, list[VendorEngagement]] = {}
        for row in (await session.execute(stmt)).scalars():
            grouped.setdefault(row.vendor_id, []).append(row)
        return grouped

    async def _contacts_of(
        self, session: AsyncSession, tenant_id: uuid.UUID, *vendor_ids: uuid.UUID
    ) -> dict[uuid.UUID, list[VendorContact]]:
        if not vendor_ids:
            return {}
        stmt = (
            select(VendorContact)
            .where(VendorContact.tenant_id == tenant_id)
            .where(VendorContact.vendor_id.in_(list(vendor_ids)))
            .order_by(VendorContact.name)
        )
        grouped: dict[uuid.UUID, list[VendorContact]] = {}
        for row in (await session.execute(stmt)).scalars():
            grouped.setdefault(row.vendor_id, []).append(row)
        return grouped

    async def _counts(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> tuple[dict[uuid.UUID, int], dict[uuid.UUID, int]]:
        """Engagement and contact counts per vendor, two grouped counts not an N+1."""

        async def tally(
            model: type[VendorEngagement] | type[VendorContact],
        ) -> dict[uuid.UUID, int]:
            stmt = (
                select(model.vendor_id, func.count())
                .where(model.tenant_id == tenant_id)
                .group_by(model.vendor_id)
            )
            return {row[0]: row[1] for row in (await session.execute(stmt)).all()}

        return await tally(VendorEngagement), await tally(VendorContact)

    # -- the cached read-model columns (V10) -----------------------------------

    @staticmethod
    def _worst_tier(engagements: list[VendorEngagement]) -> str | None:
        tiers = [e.tier for e in engagements if e.tier in TIER_RANK]
        if not tiers:
            return None
        return min(tiers, key=lambda t: TIER_RANK[str(t)])

    async def _recache(self, session: AsyncSession, tenant_id: uuid.UUID, vendor: Vendor) -> None:
        """Refresh the vendor's cached worst-engagement columns.

        The only writer of ``vendor.tier`` and ``vendor.lifecycle_status``.
        Residual score, grade and contract value stay untouched here: the engines
        that produce them are sections 3 and 4, and writing a placeholder now
        would make an unscored vendor look scored.
        """
        engagements = (await self._engagements_of(session, tenant_id, vendor.id)).get(vendor.id, [])
        vendor.tier = self._worst_tier(engagements)
        vendor.lifecycle_status = self._rolled_up_status(vendor, engagements)

    @staticmethod
    def _rolled_up_status(vendor: Vendor, engagements: list[VendorEngagement]) -> str:
        """Where the relationship as a whole stands, from its engagements.

        The gate writes ``engagement.status``; nothing wrote the vendor's, so a
        tiered, assessed, approved vendor read "Requested" forever and the
        register's Status filter was filtering on a column that only ever held
        three values. This makes it the same kind of derived cache ``tier``
        already is -- never authoritative, never the value an action is taken on,
        and recomputed from the engagements on every write.

        Worst-first, with one exception: the two states the vendor itself owns
        are terminal and outrank anything an engagement says, because ending the
        relationship ends every use of it.
        """
        if vendor.lifecycle_status in _VENDOR_OWNED_STATUSES:
            return str(vendor.lifecycle_status)
        statuses = [str(e.status) for e in engagements if e.status in _STATUS_RANK]
        if not statuses:
            return "requested"
        return min(statuses, key=lambda status: _STATUS_RANK[status])

    # -- views -----------------------------------------------------------------

    def _ownership(self, vendor: Vendor, names: dict[uuid.UUID, str]) -> OwnershipView:
        def named(member_id: uuid.UUID | None) -> str | None:
            return names.get(member_id) if member_id else None

        return OwnershipView(
            business_owner_membership_id=vendor.business_owner_membership_id,
            business_owner_name=named(vendor.business_owner_membership_id),
            security_owner_membership_id=vendor.security_owner_membership_id,
            security_owner_name=named(vendor.security_owner_membership_id),
            relationship_owner_membership_id=vendor.relationship_owner_membership_id,
            relationship_owner_name=named(vendor.relationship_owner_membership_id),
        )

    def _to_view(
        self,
        vendor: Vendor,
        names: dict[uuid.UUID, str],
        engagement_count: int,
        contact_count: int,
    ) -> VendorView:
        return VendorView(
            id=vendor.id,
            name=vendor.name,
            vendor_type=vendor.vendor_type,
            industry=vendor.industry,
            website=vendor.website,
            business_unit=vendor.business_unit,
            services_provided=vendor.services_provided,
            stores_pii=vendor.stores_pii,
            data_location=vendor.data_location,
            data_types_in_scope=list(vendor.data_types_in_scope or []),
            systems_in_scope=list(vendor.systems_in_scope or []),
            data_classification=vendor.data_classification,
            lifecycle_status=vendor.lifecycle_status,
            tier=vendor.tier,
            current_residual_score=vendor.current_residual_score,
            current_grade=vendor.current_grade,
            annual_contract_value=vendor.annual_contract_value,
            ownership=self._ownership(vendor, names),
            next_reassessment_on=vendor.next_reassessment_on,
            tags=list(vendor.tags or []),
            source=vendor.source,
            created_at=vendor.created_at,
            updated_at=vendor.updated_at,
            engagement_count=engagement_count,
            contact_count=contact_count,
            attention_code=_attention_code(vendor, datetime.now(UTC).date()),
        )

    @staticmethod
    def _engagement_view(
        engagement: VendorEngagement, names: dict[uuid.UUID, str]
    ) -> EngagementView:
        owner = engagement.internal_owner_membership_id
        return EngagementView(
            id=engagement.id,
            vendor_id=engagement.vendor_id,
            name=engagement.name,
            service_description=engagement.service_description,
            business_unit=engagement.business_unit,
            internal_owner_membership_id=owner,
            internal_owner_name=names.get(owner) if owner else None,
            tier=engagement.tier,
            status=engagement.status,
            start_date=engagement.start_date,
            end_date=engagement.end_date,
            created_at=engagement.created_at,
            updated_at=engagement.updated_at,
        )

    @staticmethod
    def _contact_view(contact: VendorContact) -> ContactView:
        return ContactView(
            id=contact.id,
            vendor_id=contact.vendor_id,
            name=contact.name,
            email=contact.email,
            phone=contact.phone,
            contact_type=contact.contact_type,
        )

    # -- duplicate detection (ER ¶90) — warns, never blocks --------------------

    async def find_duplicates(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        name: str,
        website: str | None = None,
        exclude_id: uuid.UUID | None = None,
    ) -> list[DuplicateMatch]:
        """Vendors that look like this one. Called on save and by the create form.

        Deliberately not a unique constraint: two genuinely different subsidiaries
        share a trading name, and a hard constraint would refuse a legitimate
        record rather than let a person judge.
        """
        target_name = _fingerprint(name)
        target_domain = _domain(website)
        if not target_name and not target_domain:
            return []

        stmt = select(Vendor).where(Vendor.tenant_id == tenant_id)
        if exclude_id is not None:
            stmt = stmt.where(Vendor.id != exclude_id)
        matches: list[DuplicateMatch] = []
        for other in (await session.execute(stmt)).scalars():
            if target_name and _fingerprint(other.name) == target_name:
                matches.append(DuplicateMatch(id=other.id, name=other.name, reason="same_name"))
            elif target_domain and _domain(other.website) == target_domain:
                matches.append(DuplicateMatch(id=other.id, name=other.name, reason="same_website"))
        return matches

    # -- reads -----------------------------------------------------------------

    async def list_vendors(  # noqa: PLR0912, PLR0913 — one branch per filter
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        filters: VendorFilters,
        page: int = 1,
        page_size: int = 25,
        caller_membership_id: uuid.UUID | None = None,
        sort: str | None = None,
        direction: str = "asc",
    ) -> tuple[list[VendorView], int]:
        stmt = select(Vendor).where(Vendor.tenant_id == tenant_id)
        if filters.vendor_type and filters.vendor_type != "all":
            stmt = stmt.where(Vendor.vendor_type == filters.vendor_type)
        if filters.statuses:
            stmt = stmt.where(Vendor.lifecycle_status.in_(list(filters.statuses)))
        if filters.tiers:
            stmt = stmt.where(Vendor.tier.in_(list(filters.tiers)))
        if filters.classifications:
            stmt = stmt.where(Vendor.data_classification.in_(list(filters.classifications)))
        if filters.business_units:
            stmt = stmt.where(Vendor.business_unit.in_(list(filters.business_units)))
        if filters.stores_pii:
            stmt = stmt.where(Vendor.stores_pii.is_(True))
        if filters.owner == "unassigned":
            stmt = stmt.where(Vendor.business_owner_membership_id.is_(None))
        elif filters.owner == "me" and caller_membership_id is not None:
            stmt = stmt.where(Vendor.business_owner_membership_id == caller_membership_id)
        elif filters.owner:
            # Reachable by hand-editing a link, so a bare uuid.UUID() here is a
            # 500 on a malformed query string. An owner nobody matches is an
            # empty register, which is the honest answer to an unknown id.
            try:
                owner_id = uuid.UUID(filters.owner)
            except ValueError:
                stmt = stmt.where(sa_false())
            else:
                stmt = stmt.where(Vendor.business_owner_membership_id == owner_id)
        if filters.search:
            like = f"%{filters.search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Vendor.name).like(like),
                    func.lower(func.coalesce(Vendor.website, "")).like(like),
                    func.lower(func.coalesce(Vendor.industry, "")).like(like),
                    func.lower(func.coalesce(Vendor.business_unit, "")).like(like),
                    func.lower(Vendor.services_provided).like(like),
                )
            )

        vendors = list((await session.execute(stmt)).scalars())
        names = await self._member_names(session, tenant_id)
        engagement_counts, contact_counts = await self._counts(session, tenant_id)
        views = [
            self._to_view(v, names, engagement_counts.get(v.id, 0), contact_counts.get(v.id, 0))
            for v in vendors
        ]
        if filters.attention:
            wanted = set(filters.attention)
            views = [v for v in views if v.attention_code in wanted]
        self._sort_register(views, sort, direction)
        total = len(views)
        start = (page - 1) * page_size
        return views[start : start + page_size], total

    @staticmethod
    def _sort_register(views: list[VendorView], sort: str | None, direction: str) -> None:
        """Order the page in place. ``sort=None`` keeps the risk ranking."""
        if sort is None or sort not in _SORT_KEYS:
            views.sort(key=VendorService._register_sort_key)
            return
        key = _SORT_KEYS[sort]
        # Stable two-pass: name ascending underneath, so rows that tie on the
        # chosen column stay in a predictable order rather than the scan's.
        views.sort(key=lambda v: v.name.lower())
        views.sort(key=key, reverse=direction == "desc")

    @staticmethod
    def _register_sort_key(v: VendorView) -> tuple[float, int, str]:
        """Worst tier first, then unowned, then alphabetical.

        Untiered ranks immediately after critical, not last. A vendor with no
        risk decision at all is the one the register most needs to surface, and
        ranking it below every low-tier vendor buried exactly the rows the
        attention column exists to flag.

        Unowned sorts up for the same reason: a vendor nobody owns is the one
        nobody will notice.
        """
        tier_rank = TIER_RANK.get(v.tier or "", _UNTIERED_RANK)
        unowned = 0 if v.ownership.business_owner_membership_id is None else 1
        return tier_rank, unowned, v.name.lower()

    async def summary(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        caller_membership_id: uuid.UUID | None = None,
    ) -> SummaryView:
        """The portfolio picture, in one round trip.

        The register answers "what vendors exist"; this answers "what needs
        somebody today", which is the question the module is opened with. Every
        count comes from the same scan the register already performs plus two
        grouped aggregates over findings, so it is cheaper than one register
        page, not more expensive.
        """
        today = datetime.now(UTC).date()
        vendors = list(
            (await session.execute(select(Vendor).where(Vendor.tenant_id == tenant_id))).scalars()
        )

        by_tier: dict[str, int] = dict.fromkeys(TIERS, 0)
        by_tier["untiered"] = 0
        by_status: dict[str, int] = {}
        attention: dict[str, int] = {}
        mine = 0
        in_cadence = 0
        needs_cadence = 0
        for vendor in vendors:
            by_tier[vendor.tier or "untiered"] = by_tier.get(vendor.tier or "untiered", 0) + 1
            by_status[vendor.lifecycle_status] = by_status.get(vendor.lifecycle_status, 0) + 1
            code = _attention_code(vendor, today)
            if code is not None:
                attention[code] = attention.get(code, 0) + 1
            if (
                caller_membership_id is not None
                and vendor.business_owner_membership_id == caller_membership_id
            ):
                mine += 1
            # Coverage is asked of the vendors a cadence actually applies to.
            # A low-tier vendor with no schedule is not a gap in coverage, and
            # folding it into "current" would flatter the number.
            if vendor.tier in _COVERED_TIERS and vendor.lifecycle_status not in _CLOSED_STATUSES:
                needs_cadence += 1
                if vendor.next_reassessment_on is not None and vendor.next_reassessment_on >= today:
                    in_cadence += 1

        findings = list(
            (
                await session.execute(
                    select(VendorFinding).where(VendorFinding.tenant_id == tenant_id)
                )
            ).scalars()
        )
        open_findings = [f for f in findings if f.status in OPEN_FINDING_STATUSES]
        by_severity: dict[str, int] = dict.fromkeys(FINDING_SEVERITIES, 0)
        overdue = 0
        for finding in open_findings:
            by_severity[finding.severity] = by_severity.get(finding.severity, 0) + 1
            if finding.sla_due is not None and finding.sla_due < today:
                overdue += 1

        intake_pending = (
            await session.execute(
                select(func.count())
                .select_from(VendorIntakeRequest)
                .where(VendorIntakeRequest.tenant_id == tenant_id)
                .where(VendorIntakeRequest.decision == "pending")
            )
        ).scalar_one()

        return SummaryView(
            total=len(vendors),
            mine=mine,
            by_tier=by_tier,
            by_status=by_status,
            attention=[
                AttentionCount(code=code, label=label, count=attention.get(code, 0))
                for code, label in ATTENTION_CODES
                if attention.get(code, 0) > 0
            ],
            coverage_in_scope=needs_cadence,
            coverage_current=in_cadence,
            findings_by_severity=by_severity,
            findings_open=len(open_findings),
            findings_overdue=overdue,
            intake_pending=int(intake_pending),
            highest_residual=[
                ResidualVendor(
                    id=vendor.id,
                    name=vendor.name,
                    tier=vendor.tier,
                    residual_score=vendor.current_residual_score or 0.0,
                    grade=vendor.current_grade,
                )
                for vendor in sorted(
                    (
                        v
                        for v in vendors
                        if v.current_residual_score is not None
                        and v.lifecycle_status not in _CLOSED_STATUSES
                    ),
                    key=lambda v: v.current_residual_score or 0.0,
                    reverse=True,
                )[:5]
            ],
        )

    async def get_vendor(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, vendor_id: uuid.UUID
    ) -> VendorDetailView:
        vendor = await self._load(session, tenant_id, vendor_id)
        names = await self._member_names(session, tenant_id)
        engagements = (await self._engagements_of(session, tenant_id, vendor.id)).get(vendor.id, [])
        contacts = (await self._contacts_of(session, tenant_id, vendor.id)).get(vendor.id, [])
        base = self._to_view(vendor, names, len(engagements), len(contacts))
        stages: list[StageView] = []
        tierings: list[TieringView] = []
        for engagement in engagements:
            cycle = await self._current_cycle(session, tenant_id, engagement.id)
            stages.extend(await self._stage_views(session, tenant_id, vendor, engagement, cycle))
            latest = await self._latest_tiering(session, tenant_id, engagement.id, cycle)
            if latest is not None:
                tierings.append(self._tiering_view(latest, names))
        return VendorDetailView(
            **{f: getattr(base, f) for f in base.__dataclass_fields__},
            engagements=[self._engagement_view(e, names) for e in engagements],
            contacts=[self._contact_view(c) for c in contacts],
            duplicates=await self.find_duplicates(
                session,
                tenant_id=tenant_id,
                name=vendor.name,
                website=vendor.website,
                exclude_id=vendor.id,
            ),
            stages=stages,
            tierings=tierings,
            approvals=await self._approvals_for(session, tenant_id, vendor.id),
            documents=[
                self._document_view(d, names)
                for d in (
                    await session.execute(
                        select(VendorDocument)
                        .where(VendorDocument.tenant_id == tenant_id)
                        .where(VendorDocument.vendor_id == vendor.id)
                        .order_by(VendorDocument.valid_until)
                    )
                ).scalars()
            ],
            contracts=[
                self._contract_view(c)
                for c in (
                    await session.execute(
                        select(VendorContract)
                        .where(VendorContract.tenant_id == tenant_id)
                        .where(VendorContract.vendor_id == vendor.id)
                        .order_by(VendorContract.renewal_date)
                    )
                ).scalars()
            ],
            soc_reviews=[
                self._soc_view(r)
                for r in (
                    await session.execute(
                        select(VendorSocReportReview)
                        .where(VendorSocReportReview.tenant_id == tenant_id)
                        .where(VendorSocReportReview.vendor_id == vendor.id)
                        .order_by(VendorSocReportReview.audit_period_end.desc())
                    )
                ).scalars()
            ],
            subprocessors=await self.subprocessors(
                session, tenant_id=tenant_id, vendor_id=vendor.id
            ),
            assessments=await self._assessment_summaries(session, tenant_id, vendor.id),
            transitions=await self._transitions(session, tenant_id, vendor.id, names),
        )

    async def _transitions(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        vendor_id: uuid.UUID,
        names: dict[uuid.UUID, str],
    ) -> list[TransitionView]:
        """Newest first. Shipped inline rather than behind a route because the
        volume is tens of rows and every write already returns the whole detail
        view, so the trail stays correct with no refetch."""
        rows = (
            await session.execute(
                select(VendorTransition)
                .where(VendorTransition.tenant_id == tenant_id)
                .where(VendorTransition.vendor_id == vendor_id)
                .order_by(VendorTransition.occurred_at.desc())
            )
        ).scalars()
        return [
            TransitionView(
                id=row.id,
                engagement_id=row.engagement_id,
                cycle=row.cycle,
                action=row.action,
                from_stage=row.from_stage,
                to_stage=row.to_stage,
                reason=row.reason,
                actor=names.get(row.actor_membership_id) if row.actor_membership_id else None,
                occurred_at=row.occurred_at,
            )
            for row in rows
        ]

    async def _assessment_summaries(
        self, session: AsyncSession, tenant_id: uuid.UUID, vendor_id: uuid.UUID
    ) -> list[AssessmentSummaryView]:
        rows = list(
            (
                await session.execute(
                    select(VendorAssessment)
                    .where(VendorAssessment.tenant_id == tenant_id)
                    .where(VendorAssessment.vendor_id == vendor_id)
                    .order_by(VendorAssessment.cycle.desc(), VendorAssessment.created_at.desc())
                )
            ).scalars()
        )
        if not rows:
            return []
        # One grouped count for the whole list rather than one query per row.
        counted = (
            await session.execute(
                select(
                    VendorAssessmentResponse.assessment_id,
                    func.count().filter(
                        or_(
                            VendorAssessmentResponse.answer.isnot(None),
                            VendorAssessmentResponse.answered_at.isnot(None),
                        )
                    ),
                )
                .where(VendorAssessmentResponse.tenant_id == tenant_id)
                .where(VendorAssessmentResponse.assessment_id.in_([r.id for r in rows]))
                .group_by(VendorAssessmentResponse.assessment_id)
            )
        ).all()
        answered: dict[uuid.UUID, int] = {row[0]: row[1] for row in counted}
        return [
            AssessmentSummaryView(
                id=row.id,
                engagement_id=row.engagement_id,
                cycle=row.cycle,
                kind=row.kind,
                review_format=row.review_format,
                status=row.status,
                due_date=row.due_date,
                residual_score=row.residual_score,
                grade=row.grade,
                # The scope snapshot already records how many questions were in
                # scope when it was issued, so the count needs no second query.
                question_count=int((row.scope or {}).get("question_count", 0)),
                answered_count=int(answered.get(row.id, 0)),
                submitted_at=row.submitted_at,
                created_at=row.created_at,
                questionnaire_id=row.questionnaire_id,
                questionnaire_name=(row.scope or {}).get("questionnaire_name"),
            )
            for row in rows
        ]

    @staticmethod
    def _tiering_view(row: VendorTieringAssessment, names: dict[uuid.UUID, str]) -> TieringView:
        """Recompute the arithmetic from the answers and the run's own snapshot.

        Deliberately not from today's policy or today's questionnaire: an
        assessment has to keep meaning what it meant when it was made, or "why is
        this vendor critical" becomes unanswerable the moment somebody retunes it.
        """
        owner = row.assessed_by_membership_id
        common: dict[str, Any] = {
            "id": row.id,
            "engagement_id": row.engagement_id,
            "cycle": row.cycle,
            "score": row.inherent_score,
            "computed_tier": row.computed_tier,
            "override_tier": row.override_tier,
            "override_justification": row.override_justification,
            "effective_tier": row.override_tier or row.computed_tier,
            "assessed_by_name": names.get(owner) if owner else None,
            "assessed_at": row.assessed_at,
        }
        snapshot = row.questionnaire_snapshot or {}
        if snapshot.get("questions"):
            asked = [asked_from_snapshot(q) for q in snapshot["questions"]]
            stored = row.answers or {}
            values = {key: (entry or {}).get("value") for key, entry in stored.items()}
            breakdown = scoring.compute_questionnaire_tier(
                [q.rule() for q in asked],
                values,
                thresholds=(row.policy_snapshot or {}).get("thresholds"),
            )
            return TieringView(
                **common,
                factors=[],
                thresholds=breakdown.thresholds,
                points_to_higher_tier=breakdown.points_to_higher_tier,
                points_to_lower_tier=breakdown.points_to_lower_tier,
                questionnaire_id=row.questionnaire_id,
                questionnaire_name=str(snapshot.get("name") or "") or None,
                questions=[
                    TieringQuestionView(
                        id=line.id,
                        prompt=line.prompt,
                        section=line.section,
                        answer_labels=list(line.answer_labels)
                        or (
                            [str(values[line.id])]
                            if values.get(line.id) not in (None, "", [])
                            else []
                        ),
                        comment=(stored.get(line.id) or {}).get("comment"),
                        points=line.points,
                        max_points=line.max_points,
                        floor_tier=line.floor_tier,
                        counted=line.counted,
                    )
                    for line in breakdown.questions
                ],
                answers=dict(stored),
                floor_tier=breakdown.floor_tier,
            )

        policy = row.policy_snapshot or {}
        legacy = scoring.compute_tier(
            {key: getattr(row, key) or 0 for key in scoring.FACTOR_KEYS},
            weights=policy.get("weights"),
            thresholds=policy.get("thresholds"),
        )
        return TieringView(
            **common,
            factors=list(legacy.factors),
            thresholds=legacy.thresholds,
            points_to_higher_tier=legacy.points_to_higher_tier,
            points_to_lower_tier=legacy.points_to_lower_tier,
            questionnaire_id=None,
            questionnaire_name=None,
            questions=[],
            answers={},
            floor_tier=None,
        )

    async def get_ref(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, vendor_id: uuid.UUID
    ) -> VendorRef:
        """The cross-module read (rule 4). Siblings call this, never ``get_vendor``."""
        vendor = await self._load(session, tenant_id, vendor_id)
        return VendorRef(
            id=vendor.id,
            name=vendor.name,
            tier=vendor.tier,
            lifecycle_status=vendor.lifecycle_status,
        )

    async def owner_of(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, vendor_id: uuid.UUID
    ) -> uuid.UUID | None:
        """The vendor's business owner, or nothing.

        Nothing is a real answer, and the scheduled jobs treat it as one: an
        unowned vendor gets no notification rather than one sent to everybody. The
        register already surfaces unowned rows by sorting them to the top.
        """
        return (
            await session.execute(
                select(Vendor.business_owner_membership_id)
                .where(Vendor.tenant_id == tenant_id)
                .where(Vendor.id == vendor_id)
            )
        ).scalar_one_or_none()

    async def facets(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> dict[str, Any]:
        """The register's filter vocabularies, served rather than hardcoded."""
        units = (
            await session.execute(
                select(Vendor.business_unit)
                .where(Vendor.tenant_id == tenant_id)
                .where(Vendor.business_unit.is_not(None))
                .distinct()
                .order_by(Vendor.business_unit)
            )
        ).scalars()
        policy = await self._resolved_policy(session, tenant_id)
        return {
            "vendor_types": list(VENDOR_TYPES),
            "statuses": list(LIFECYCLE_STATUSES),
            "tiers": list(TIERS),
            "classifications": list(DATA_CLASSIFICATIONS),
            "contact_types": list(CONTACT_TYPES),
            "business_units": [u for u in units if u],
            # The lifecycle vocabulary, served rather than reimplemented in
            # TypeScript — which is how the two drift and the interface offers a
            # move the API then refuses.
            "stages": [
                {
                    "stage": stage,
                    "label": lifecycle.STAGE_LABELS[stage],
                    "is_gate": stage in lifecycle.GATES,
                    "is_required": stage in lifecycle.REQUIRED_STAGES,
                }
                for stage in lifecycle.STAGES
            ],
            "skip_matrix_by_tier": {
                tier: sorted(lifecycle.skips_for(tier, policy.skip_matrix)) for tier in TIERS
            },
            "tiering_factors": [
                {
                    "key": key,
                    "label": scoring.FACTOR_LABELS[key],
                    "weight": policy.weights.get(key, 0.0),
                    "scale_max": scoring.FACTOR_SCALE_MAX,
                }
                for key in scoring.FACTOR_KEYS
            ],
            # Who a stage waits on, by tier. Roles, not people — the roster
            # resolves a role to a person. Served here for the same reason as
            # the stage list: so the interface names the right next actor
            # instead of a second copy of the policy drifting in TypeScript.
            # The tenant's resolved policy, not the shipped defaults -- mirroring
            # tier_thresholds below. A tenant that customised its reviewer roles
            # was being told the defaults, so the roster captions and the gate
            # handoff both named the wrong people.
            "reviewer_roles_by_tier": {
                tier: list(roles) for tier, roles in policy.reviewer_roles.items()
            },
            "tier_thresholds": policy.thresholds,
            "policy_is_customised": policy.is_customised,
            # The builder's domain picker, served for the same reason as stages.
            "risk_domains": [
                {"key": key, "label": label} for key, label in RISK_DOMAIN_LABELS.items()
            ],
        }

    # -- writes ----------------------------------------------------------------

    async def create_vendor(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        data: VendorInput,
        engagement: EngagementInput | None = None,
    ) -> VendorDetailView:
        """Create the vendor and its first engagement in one transaction (V10).

        ``engagement`` names the first use explicitly; omitting it creates the
        implicit default, which is what keeps a small workspace from ever having
        to learn the word "engagement".
        """
        vendor = Vendor(id=uuid7(), tenant_id=tenant_id, lifecycle_status="requested")
        self._assign(vendor, data)
        session.add(vendor)
        await session.flush([vendor])

        first = engagement or EngagementInput(
            name=DEFAULT_ENGAGEMENT_NAME,
            service_description=vendor.services_provided,
            business_unit=vendor.business_unit,
        )
        await self._add_engagement(session, tenant_id, vendor, first, actor, audit=False)

        await self._audit.record(
            session,
            action="create",
            object_type="vendor",
            object_id=vendor.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after=AuditService.snapshot(vendor, fields=_SNAPSHOT),
        )
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=vendor.id)

    async def update_vendor(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        data: VendorInput,
    ) -> VendorDetailView:
        vendor = await self._load(session, tenant_id, vendor_id)
        before = AuditService.snapshot(vendor, fields=_SNAPSHOT)
        self._assign(vendor, data)
        after = AuditService.snapshot(vendor, fields=_SNAPSHOT)
        if before != after:
            await self._audit.record(
                session,
                action="update",
                object_type="vendor",
                object_id=vendor.id,
                actor=actor,
                tenant_id=tenant_id,
                before=before,
                after=after,
            )
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=vendor.id)

    async def _add_engagement(  # noqa: PLR0913
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        vendor: Vendor,
        data: EngagementInput,
        actor: Actor,
        *,
        audit: bool,
    ) -> VendorEngagement:
        if data.start_date and data.end_date and data.end_date < data.start_date:
            raise InvalidInput(
                "The end date falls before the start date. Check the dates and try again.",
                detail=f"end_date {data.end_date} precedes start_date {data.start_date}",
            )
        engagement = VendorEngagement(
            id=uuid7(),
            tenant_id=tenant_id,
            vendor_id=vendor.id,
            name=self._require_name(data.name, what="engagement"),
            service_description=data.service_description.strip(),
            business_unit=self._clean(data.business_unit),
            internal_owner_membership_id=data.internal_owner_membership_id,
            status=vendor.lifecycle_status,
            start_date=data.start_date,
            end_date=data.end_date,
        )
        session.add(engagement)
        await session.flush([engagement])
        if audit:
            await self._audit.record(
                session,
                action="create",
                object_type="vendor_engagement",
                object_id=engagement.id,
                actor=actor,
                tenant_id=tenant_id,
                before=None,
                after=AuditService.snapshot(engagement, fields=_ENGAGEMENT_SNAPSHOT),
            )
        return engagement

    async def add_engagement(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        data: EngagementInput,
    ) -> VendorDetailView:
        vendor = await self._load(session, tenant_id, vendor_id)
        await self._add_engagement(session, tenant_id, vendor, data, actor, audit=True)
        await self._recache(session, tenant_id, vendor)
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=vendor_id)

    async def update_engagement(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        engagement_id: uuid.UUID,
        data: EngagementInput,
    ) -> VendorDetailView:
        engagement = await self._load_engagement(session, tenant_id, engagement_id)
        if engagement.vendor_id != vendor_id:
            # The path says which vendor this engagement belongs to. Disagreeing
            # with the record is a stale link or a guess, not an edit.
            raise NotFound(
                _ENGAGEMENT_GONE, detail=f"engagement {engagement_id} is not on vendor {vendor_id}"
            )
        if data.start_date and data.end_date and data.end_date < data.start_date:
            raise InvalidInput(
                "The end date falls before the start date. Check the dates and try again.",
                detail=f"end_date {data.end_date} precedes start_date {data.start_date}",
            )
        before = AuditService.snapshot(engagement, fields=_ENGAGEMENT_SNAPSHOT)
        engagement.name = self._require_name(data.name, what="engagement")
        engagement.service_description = data.service_description.strip()
        engagement.business_unit = self._clean(data.business_unit)
        engagement.internal_owner_membership_id = data.internal_owner_membership_id
        engagement.start_date = data.start_date
        engagement.end_date = data.end_date
        after = AuditService.snapshot(engagement, fields=_ENGAGEMENT_SNAPSHOT)
        if before != after:
            await self._audit.record(
                session,
                action="update",
                object_type="vendor_engagement",
                object_id=engagement.id,
                actor=actor,
                tenant_id=tenant_id,
                before=before,
                after=after,
            )
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=engagement.vendor_id)

    async def add_contact(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        data: ContactInput,
    ) -> VendorDetailView:
        vendor = await self._load(session, tenant_id, vendor_id)
        self._check_vocabulary(data.contact_type, CONTACT_TYPES, field_name="contact_type")
        email = self._clean(data.email)
        if data.contact_type == "portal" and not email:
            raise InvalidInput(
                "A portal contact needs an email address, because the "
                "questionnaire link is sent there.",
                detail="portal contact without an email",
            )
        contact = VendorContact(
            id=uuid7(),
            tenant_id=tenant_id,
            vendor_id=vendor.id,
            name=self._require_name(data.name, what="contact"),
            email=email,
            phone=self._clean(data.phone),
            contact_type=data.contact_type,
        )
        session.add(contact)
        await session.flush([contact])
        await self._audit.record(
            session,
            action="create",
            object_type="vendor_contact",
            object_id=contact.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after={"name": contact.name, "contact_type": contact.contact_type},
        )
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=vendor_id)

    # -- tiering and the lifecycle (section 2) ---------------------------------

    async def _policy(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> VendorTieringPolicy | None:
        return (
            await session.execute(
                select(VendorTieringPolicy).where(VendorTieringPolicy.tenant_id == tenant_id)
            )
        ).scalar_one_or_none()

    async def _resolved_policy(self, session: AsyncSession, tenant_id: uuid.UUID) -> ResolvedPolicy:
        """The tenant's tuning, falling back to the shipped defaults field by field.

        Field by field, not row or nothing: a tenant that overrode only the cadence
        should not silently lose the default weights with it.
        """
        row = await self._policy(session, tenant_id)
        skip_matrix = {
            tier: tuple(stages)
            for tier, stages in (row.stage_skip_matrix_by_tier if row else {}).items()
        }
        reviewers = {
            tier: tuple(roles)
            for tier, roles in (row.required_reviewer_roles_by_tier if row else {}).items()
        }
        return ResolvedPolicy(
            weights={**scoring.DEFAULT_WEIGHTS, **((row.factor_weights if row else None) or {})},
            thresholds={
                **scoring.DEFAULT_THRESHOLDS,
                **((row.tier_thresholds if row else None) or {}),
            },
            skip_matrix={**lifecycle.DEFAULT_SKIP_MATRIX, **skip_matrix},
            reviewer_roles={**lifecycle.DEFAULT_REVIEWER_ROLES, **reviewers},
            cadence_days={
                **lifecycle.DEFAULT_CADENCE_DAYS,
                **((row.cadence_days_by_tier if row else None) or {}),
            },
            is_customised=row is not None,
        )

    async def _stages_for(
        self, session: AsyncSession, tenant_id: uuid.UUID, engagement_id: uuid.UUID, cycle: int
    ) -> list[VendorStage]:
        stmt = (
            select(VendorStage)
            .where(VendorStage.tenant_id == tenant_id)
            .where(VendorStage.engagement_id == engagement_id)
            .where(VendorStage.cycle == cycle)
        )
        rows = list((await session.execute(stmt)).scalars())
        order = {stage: index for index, stage in enumerate(lifecycle.STAGES)}
        rows.sort(key=lambda row: order[row.stage])
        return rows

    async def _current_cycle(
        self, session: AsyncSession, tenant_id: uuid.UUID, engagement_id: uuid.UUID
    ) -> int:
        highest = (
            await session.execute(
                select(func.max(VendorStage.cycle))
                .where(VendorStage.tenant_id == tenant_id)
                .where(VendorStage.engagement_id == engagement_id)
            )
        ).scalar_one_or_none()
        return int(highest or 1)

    async def _latest_tiering(
        self, session: AsyncSession, tenant_id: uuid.UUID, engagement_id: uuid.UUID, cycle: int
    ) -> VendorTieringAssessment | None:
        stmt = (
            select(VendorTieringAssessment)
            .where(VendorTieringAssessment.tenant_id == tenant_id)
            .where(VendorTieringAssessment.engagement_id == engagement_id)
            .where(VendorTieringAssessment.cycle == cycle)
            .order_by(VendorTieringAssessment.created_at.desc())
            .limit(1)
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def _latest_assessment(
        self, session: AsyncSession, tenant_id: uuid.UUID, engagement_id: uuid.UUID, cycle: int
    ) -> VendorAssessment | None:
        return (
            await session.execute(
                select(VendorAssessment)
                .where(VendorAssessment.tenant_id == tenant_id)
                .where(VendorAssessment.engagement_id == engagement_id)
                .where(VendorAssessment.cycle == cycle)
                .order_by(VendorAssessment.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def _contract_count(
        self, session: AsyncSession, tenant_id: uuid.UUID, engagement: VendorEngagement
    ) -> int:
        """Active contracts covering this engagement, or the vendor as a whole.

        A master agreement with no engagement named covers every engagement — which
        is how most vendors are actually contracted, and demanding a per-engagement
        contract would fail the common case.
        """
        return (
            await session.execute(
                select(func.count())
                .select_from(VendorContract)
                .where(VendorContract.tenant_id == tenant_id)
                .where(VendorContract.vendor_id == engagement.vendor_id)
                .where(VendorContract.status == "active")
                .where(
                    or_(
                        VendorContract.engagement_id == engagement.id,
                        VendorContract.engagement_id.is_(None),
                    )
                )
            )
        ).scalar_one()

    async def _latest_approval_at(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        engagement: VendorEngagement,
        stage: VendorStage,
    ) -> datetime | None:
        """When this cycle was last approved, if it was.

        Only ``approve`` and ``approve_with_conditions`` count. A ``defer`` or a
        ``reject`` is a decision that was made and recorded, and it is not a pass.
        """
        return (
            await session.execute(
                select(VendorApproval.decided_at)
                .where(VendorApproval.tenant_id == tenant_id)
                .where(VendorApproval.engagement_id == engagement.id)
                .where(VendorApproval.cycle == stage.cycle)
                .where(VendorApproval.decision.in_(["approve", "approve_with_conditions"]))
                .order_by(VendorApproval.decided_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def _facts(  # noqa: PLR0913, PLR0917
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        vendor: Vendor,
        engagement: VendorEngagement,
        stage: VendorStage,
        policy: ResolvedPolicy,
    ) -> lifecycle.StageFacts:
        tiering = await self._latest_tiering(session, tenant_id, engagement.id, stage.cycle)
        tier = engagement.tier
        # Section 3 built the assessment and finding tables, so the checks that
        # reported pending are answerable now. Nothing in lifecycle.py changed:
        # the rules were always written, and this is the collector catching up.
        assessment = await self._latest_assessment(session, tenant_id, engagement.id, stage.cycle)
        answers = (
            await self.answers_with_questions(
                session, tenant_id=tenant_id, assessment_id=assessment.id
            )
            if assessment
            else []
        )
        shown = visible_keys(answers)
        return lifecycle.StageFacts(
            vendor_id=vendor.id,
            vendor_name=vendor.name,
            tier=tier,
            business_owner_membership_id=vendor.business_owner_membership_id,
            data_classification=vendor.data_classification,
            tiering_assessment_id=tiering.id if tiering else None,
            stage_entered_at=stage.entered_at,
            next_cycle_opened=stage.cycle
            < await self._current_cycle(session, tenant_id, engagement.id),
            required_reviewer_roles=policy.reviewer_roles.get(tier or "", ()),
            assessments_available=True,
            selected_bank_count=1 if assessment else 0,
            unanswered_question_count=sum(
                1 for r, q in answers if q.key in shown and q.required and not is_answered(r, q)
            ),
            missing_evidence_count=sum(
                1 for r, q in answers if owes_evidence(r, q, visible=q.key in shown)
            ),
            residual_score=assessment.residual_score if assessment else None,
            findings_available=True,
            open_critical_findings=await self.open_critical_count(
                session, tenant_id=tenant_id, vendor_id=vendor.id
            ),
            # Section 4 built the contracts and the gate, so the last two checks
            # answer now. Every rule in lifecycle.py is unchanged since section 2 —
            # only this collector moved, which is what the three-valued check was
            # designed to make possible.
            contracts_available=True,
            contract_count=await self._contract_count(session, tenant_id, engagement),
            approvals_available=True,
            approval_decided_at=await self._latest_approval_at(
                session, tenant_id, engagement, stage
            ),
            assigned_reviewer_roles=tuple((await self.roster(session, tenant_id=tenant_id)).keys()),
        )

    async def _stage_views(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        vendor: Vendor,
        engagement: VendorEngagement,
        cycle: int,
    ) -> list[StageView]:
        policy = await self._resolved_policy(session, tenant_id)
        skippable = lifecycle.skips_for(engagement.tier, policy.skip_matrix)
        rows = await self._stages_for(session, tenant_id, engagement.id, cycle)
        order = {stage: index for index, stage in enumerate(lifecycle.STAGES)}
        views: list[StageView] = []
        for row in rows:
            checks = lifecycle.evaluate_exit(
                row.stage, await self._facts(session, tenant_id, vendor, engagement, row, policy)
            )
            state = lifecycle.StageState(
                stage=row.stage, status=row.status, is_gate=row.is_gate, is_required=row.is_required
            )
            views.append(
                StageView(
                    id=row.id,
                    engagement_id=row.engagement_id,
                    cycle=row.cycle,
                    stage=row.stage,
                    label=lifecycle.STAGE_LABELS[row.stage],
                    status=row.status,
                    is_gate=row.is_gate,
                    is_required=row.is_required,
                    entered_at=row.entered_at,
                    exited_at=row.exited_at,
                    skipped_reason=row.skipped_reason,
                    skipped_by_policy=row.skipped_by_policy,
                    checks=list(checks),
                    blockers=list(lifecycle.blockers(checks)),
                    pending=list(lifecycle.pending(checks)),
                    allowed_transitions=list(
                        lifecycle.allowed_transitions(
                            state,
                            checks,
                            skippable=skippable,
                            has_earlier_stage=order[row.stage] > 0,
                        )
                    ),
                )
            )
        return views

    async def _write_transition(  # noqa: PLR0913
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        stage: VendorStage,
        actor: Actor,
        action: str,
        *,
        to_stage: str | None,
        reason: str | None,
    ) -> None:
        """Both records, one transaction: the columnar row and the audit row.

        Two histories on purpose. ``vendor_transitions`` is the domain view an
        operator reads down; ``audit_log`` is the platform trail an auditor reads
        across. Writing only one of them makes the other lie by omission.
        """
        now = datetime.now(UTC)
        session.add(
            VendorTransition(
                id=uuid7(),
                tenant_id=tenant_id,
                vendor_id=stage.vendor_id,
                engagement_id=stage.engagement_id,
                stage_id=stage.id,
                cycle=stage.cycle,
                action=action,
                from_stage=stage.stage,
                to_stage=to_stage,
                reason=reason,
                actor_membership_id=actor.id if isinstance(actor, Membership) else None,
                occurred_at=now,
            )
        )
        await session.flush()
        await self._audit.record(
            session,
            action="transition",
            object_type="vendor_stage",
            object_id=stage.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"stage": stage.stage, "status": stage.status},
            after={"action": action, "to_stage": to_stage, "reason": reason},
        )

    async def materialise_cycle(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        engagement: VendorEngagement,
        cycle: int,
        policy: ResolvedPolicy,
    ) -> list[VendorStage]:
        """Write the twelve rows for one cycle, this tier's skips already marked.

        Idempotent: an existing cycle is re-planned in place rather than
        duplicated, so re-running tiering after a retier moves the skips instead
        of colliding with the unique constraint.
        """
        existing = {
            row.stage: row
            for row in await self._stages_for(session, tenant_id, engagement.id, cycle)
        }
        rows: list[VendorStage] = []
        for planned in lifecycle.plan_cycle(engagement.tier, policy.skip_matrix):
            row = existing.get(planned.stage)
            if row is None:
                row = VendorStage(
                    id=uuid7(),
                    tenant_id=tenant_id,
                    vendor_id=engagement.vendor_id,
                    engagement_id=engagement.id,
                    cycle=cycle,
                    stage=planned.stage,
                    status=planned.status,
                    is_gate=planned.is_gate,
                    is_required=planned.is_required,
                    skipped_by_policy=planned.skipped_by_policy,
                )
                session.add(row)
            elif row.status in {"not_started", "skipped"}:
                # Never re-plan work already done or under way: a retier changes
                # what is still ahead, not what has already been decided.
                row.status = planned.status
                row.skipped_by_policy = planned.skipped_by_policy
            rows.append(row)
        await session.flush()
        return rows

    async def tier_engagement(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        engagement_id: uuid.UUID,
        answers: TieringAnswers | QuestionnaireTieringInput,
    ) -> VendorDetailView:
        """Score the answers, set the tier, and lay out the cycle it implies.

        Two kinds of answers arrive here. A questionnaire run is what the interface
        sends: the tenant's own tiering questions, scored by their options. The
        five fixed factors (V6) are still accepted from API clients that post them.

        This is the method spec paragraph 82 is about: the tier is computed here
        and the *work* changes in the same transaction, because a tier that does
        not change the workload has added a dropdown rather than a control.
        """
        engagement = await self._load_engagement(session, tenant_id, engagement_id)
        if engagement.vendor_id != vendor_id:
            raise NotFound(
                _ENGAGEMENT_GONE,
                detail=f"engagement {engagement_id} is not on vendor {vendor_id}",
            )
        vendor = await self._load(session, tenant_id, vendor_id)
        if answers.override_tier and not (answers.override_justification or "").strip():
            raise InvalidInput(
                "Say why you are overriding the computed tier. The justification is "
                "what makes the override defensible to an auditor.",
                detail="override_tier without override_justification",
            )
        self._check_vocabulary(answers.override_tier, TIERS, field_name="override_tier")

        policy = await self._resolved_policy(session, tenant_id)
        cycle = await self._current_cycle(session, tenant_id, engagement.id)
        assessment = VendorTieringAssessment(
            id=uuid7(),
            tenant_id=tenant_id,
            vendor_id=vendor.id,
            engagement_id=engagement.id,
            cycle=cycle,
            override_tier=answers.override_tier,
            override_justification=(answers.override_justification or "").strip() or None,
            assessed_by_membership_id=actor.id if isinstance(actor, Membership) else None,
            assessed_at=datetime.now(UTC),
        )
        if isinstance(answers, QuestionnaireTieringInput):
            score, tier = await self._score_tiering_questionnaire(
                session, tenant_id, answers, policy, assessment
            )
        else:
            breakdown = scoring.compute_tier(
                answers.as_dict(), weights=policy.weights, thresholds=policy.thresholds
            )
            score, tier = breakdown.score, breakdown.tier
            for key, value in answers.as_dict().items():
                setattr(assessment, key, value)
            # Frozen with the row, so a later retune of the policy cannot rewrite
            # what this assessment meant when it was made.
            assessment.policy_snapshot = {
                "weights": policy.weights,
                "thresholds": policy.thresholds,
            }
        assessment.inherent_score = score
        assessment.computed_tier = tier
        session.add(assessment)
        await session.flush([assessment])

        engagement.tier = answers.override_tier or tier
        await self.materialise_cycle(session, tenant_id, engagement, cycle, policy)
        await self._recache(session, tenant_id, vendor)
        self._schedule_reassessment(vendor, engagement.tier, policy)

        await self._audit.record(
            session,
            action="create",
            object_type="vendor_tiering_assessment",
            object_id=assessment.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after={
                "engagement_id": str(engagement.id),
                "inherent_score": score,
                "computed_tier": tier,
                "override_tier": answers.override_tier,
                "questionnaire_id": str(assessment.questionnaire_id)
                if assessment.questionnaire_id
                else None,
            },
        )
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=vendor.id)

    async def _score_tiering_questionnaire(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        answers: QuestionnaireTieringInput,
        policy: ResolvedPolicy,
        assessment: VendorTieringAssessment,
    ) -> tuple[float, str]:
        """Validate and score a tiering questionnaire run, writing its snapshot onto the row."""
        questionnaire = await questionnaire_service.load_for_use(
            session,
            tenant_id=tenant_id,
            questionnaire_id=answers.questionnaire_id,
            purpose="tiering",
        )
        if questionnaire is None:
            raise InvalidInput(
                "There is no tiering questionnaire to answer. Set one up under "
                "Vendors, Questionnaires.",
                detail="no tiering questionnaire for tenant",
            )
        snapshot = await questionnaire_service.snapshot(
            session, tenant_id=tenant_id, questionnaire=questionnaire
        )
        asked = [asked_from_snapshot(q) for q in snapshot["questions"]]
        if not asked:
            raise InvalidInput(
                "This tiering questionnaire has no questions yet. Add some first.",
                detail=f"questionnaire {questionnaire.id} is empty",
            )
        by_key = {q.key: q for q in asked}
        unknown = set(answers.answers) - set(by_key)
        if unknown:
            raise InvalidInput(
                "Some answers are for questions this questionnaire no longer has. "
                "Reopen the questionnaire and answer again.",
                detail=f"unknown tiering questions {sorted(unknown)[:5]}",
            )

        stored: dict[str, dict[str, Any]] = {}
        for key, entry in answers.answers.items():
            raw = entry.get("value") if isinstance(entry, dict) else entry
            value = normalize_answer(by_key[key], raw)
            comment = (
                str(entry.get("comment") or "").strip()[:4000] if isinstance(entry, dict) else ""
            )
            if value is not None:
                stored[key] = {"value": value, **({"comment": comment} if comment else {})}

        values = {key: entry["value"] for key, entry in stored.items()}
        shown = scoring.visible_ids([q.rule() for q in asked], values)
        missing = [q for q in asked if q.key in shown and q.required and q.key not in stored]
        if missing:
            raise InvalidInput(
                f"Answer the {len(missing)} required "
                f"{'question' if len(missing) == 1 else 'questions'} before setting the tier.",
                detail=f"unanswered tiering questions {[q.key for q in missing][:5]}",
            )
        for question in asked:
            if question.key not in shown or question.key not in stored:
                continue
            needs_note = any(
                o.comment_required for o in picked_options(question, values[question.key])
            )
            if needs_note and not stored[question.key].get("comment"):
                raise InvalidInput(
                    f"Add a note to explain your answer to: {question.prompt}",
                    detail=f"comment required on {question.key}",
                )
        # Answers to questions the branching hid are not kept: they were never asked.
        stored = {key: entry for key, entry in stored.items() if key in shown}
        values = {key: entry["value"] for key, entry in stored.items()}

        thresholds = dict(questionnaire.tier_thresholds or {}) or policy.thresholds
        breakdown = scoring.compute_questionnaire_tier(
            [q.rule() for q in asked], values, thresholds=thresholds
        )
        assessment.questionnaire_id = questionnaire.id
        assessment.answers = stored
        assessment.questionnaire_snapshot = snapshot
        assessment.policy_snapshot = {"weights": {}, "thresholds": breakdown.thresholds}
        return breakdown.score, breakdown.tier

    @staticmethod
    def _schedule_reassessment(vendor: Vendor, tier: str | None, policy: ResolvedPolicy) -> None:
        """Set the next review date from the cadence, not from today's completion.

        Anchored to the previous due date where one exists, so a review done late
        does not push the next one late. Reviews that drift a little further out
        every cycle is the failure this rule exists to prevent (ER 101).
        """
        days = policy.cadence_days.get(tier or "", 0)
        if not days:
            return
        anchor = vendor.next_reassessment_on or datetime.now(UTC).date()
        vendor.next_reassessment_on = anchor + timedelta(days=int(days))

    async def _load_stage(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        vendor_id: uuid.UUID,
        stage_id: uuid.UUID,
    ) -> VendorStage:
        stage = await session.get(VendorStage, stage_id, populate_existing=True)
        if stage is None or stage.tenant_id != tenant_id or stage.vendor_id != vendor_id:
            raise NotFound(_STAGE_GONE, detail=f"vendor stage {stage_id} on vendor {vendor_id}")
        return stage

    async def advance_stage(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        stage_id: uuid.UUID,
        note: str | None = None,
    ) -> VendorDetailView:
        """Complete this stage and enter the next one that is not skipped."""
        stage = await self._load_stage(session, tenant_id, vendor_id, stage_id)
        engagement = await self._load_engagement(session, tenant_id, stage.engagement_id)
        vendor = await self._load(session, tenant_id, vendor_id)
        policy = await self._resolved_policy(session, tenant_id)

        checks = lifecycle.evaluate_exit(
            stage.stage, await self._facts(session, tenant_id, vendor, engagement, stage, policy)
        )
        outstanding = lifecycle.blockers(checks)
        if outstanding:
            raise Conflict(
                "This stage still has work outstanding. Clear the blockers listed on "
                "it and try again.",
                detail=f"{stage.stage} blocked by {[c.code for c in outstanding]}",
            )
        if stage.stage == lifecycle.TERMINAL_STAGE:
            raise Conflict(
                "Offboarding is the end of the lifecycle. There is nothing after it.",
                detail="advance from the terminal stage",
            )

        now = datetime.now(UTC)
        stage.status = "complete"
        stage.exited_at = now
        if stage.stage == "onboarding" and engagement.status == "approved":
            engagement.status = "active"
        rows = await self._stages_for(session, tenant_id, engagement.id, stage.cycle)
        # Walk over the skipped rows, so a low-tier vendor goes from tiering to
        # contracting in one move and the proportionality is visible.
        target = lifecycle.next_actionable([(r.stage, r.status) for r in rows], stage.stage)
        if target is not None:
            nxt = next(r for r in rows if r.stage == target)
            nxt.status = "in_progress"
            nxt.entered_at = now
        await self._recache(session, tenant_id, vendor)
        await self._write_transition(
            session, tenant_id, stage, actor, "advance", to_stage=target, reason=note
        )
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=vendor.id)

    async def send_back(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        stage_id: uuid.UUID,
        to_stage: str,
        reason: str,
    ) -> VendorDetailView:
        """Return the engagement to an earlier stage, resetting everything after it.

        Downstream work is invalidated **by design**. Combined with the
        gate-freshness rule, a previously granted approval stops counting without
        the append-only approval row ever being touched.
        """
        stage = await self._load_stage(session, tenant_id, vendor_id, stage_id)
        vendor = await self._load(session, tenant_id, vendor_id)
        if not reason.strip():
            raise InvalidInput(
                "Say why you are sending this back. The reason is what the owner "
                "sees when they pick it up.",
                detail="send_back without a reason",
            )
        order = {name: index for index, name in enumerate(lifecycle.STAGES)}
        if to_stage not in order:
            raise InvalidInput(
                "That is not a stage in the lifecycle.", detail=f"unknown stage {to_stage!r}"
            )
        if order[to_stage] >= order[stage.stage]:
            raise Conflict(
                "A send-back only goes backwards. To move forward, clear this "
                "stage's blockers and advance.",
                detail=f"send_back from {stage.stage} to {to_stage}",
            )

        now = datetime.now(UTC)
        rows = await self._stages_for(session, tenant_id, stage.engagement_id, stage.cycle)
        for row in rows:
            if order[row.stage] < order[to_stage] or row.status == "skipped":
                continue
            row.status = "in_progress" if row.stage == to_stage else "not_started"
            row.entered_at = now if row.stage == to_stage else None
            row.exited_at = None
        await self._write_transition(
            session, tenant_id, stage, actor, "send_back", to_stage=to_stage, reason=reason.strip()
        )
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=vendor.id)

    async def skip_stage(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        stage_id: uuid.UUID,
        reason: str,
    ) -> VendorDetailView:
        """Mark a stage skipped, if this tier's policy permits it.

        A gate is refused here and refused again by a database CHECK. Two layers
        because spec paragraph 82's "approval gates are never skipped" is a
        control statement, and a control enforced only in application code is a
        control one bug away from not existing.
        """
        stage = await self._load_stage(session, tenant_id, vendor_id, stage_id)
        engagement = await self._load_engagement(session, tenant_id, stage.engagement_id)
        vendor = await self._load(session, tenant_id, vendor_id)
        if not reason.strip():
            raise InvalidInput(
                "Say why this stage is being skipped. A skip with no reason is "
                "indistinguishable from an oversight.",
                detail="skip without a reason",
            )
        if stage.is_gate:
            raise Conflict(
                "An approval gate can never be skipped, whatever the tier.",
                detail=f"skip refused on gate {stage.stage}",
            )
        if stage.is_required:
            raise Conflict(
                f"{lifecycle.STAGE_LABELS[stage.stage]} is required for every vendor "
                "and cannot be skipped.",
                detail=f"skip refused on required stage {stage.stage}",
            )
        policy = await self._resolved_policy(session, tenant_id)
        if stage.stage not in lifecycle.skips_for(engagement.tier, policy.skip_matrix):
            raise Conflict(
                f"A {engagement.tier or 'vendor'}-tier engagement does not skip "
                f"{lifecycle.STAGE_LABELS[stage.stage].lower()}. Retier it, or clear "
                "the stage.",
                detail=f"{stage.stage} not skippable at tier {engagement.tier}",
            )

        stage.status = "skipped"
        stage.skipped_reason = reason.strip()
        stage.skipped_by_membership_id = actor.id if isinstance(actor, Membership) else None
        stage.exited_at = datetime.now(UTC)
        await self._write_transition(
            session, tenant_id, stage, actor, "skip", to_stage=None, reason=reason.strip()
        )
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=vendor.id)

    # -- the questionnaire (section 3) -----------------------------------------

    async def _current_bank(
        self, session: AsyncSession, code: str | None = None
    ) -> QuestionnaireTemplate:
        stmt = select(QuestionnaireTemplate).where(QuestionnaireTemplate.purpose == "due_diligence")
        stmt = (
            stmt.where(QuestionnaireTemplate.code == code)
            if code
            else stmt.where(QuestionnaireTemplate.is_current.is_(True)).order_by(
                QuestionnaireTemplate.code
            )
        )
        bank = (await session.execute(stmt.limit(1))).scalar_one_or_none()
        if bank is None:
            raise InvalidInput(
                "No questionnaire bank is available. Ask an administrator to load the "
                "shipped content.",
                detail=f"no questionnaire_template for code={code!r}",
            )
        return bank

    async def _bank_questions(
        self, session: AsyncSession, template_id: uuid.UUID, scope_levels: Sequence[str]
    ) -> list[QuestionnaireQuestion]:
        stmt = (
            select(QuestionnaireQuestion)
            .where(QuestionnaireQuestion.template_id == template_id)
            .where(QuestionnaireQuestion.scope_level.in_(list(scope_levels)))
            .order_by(QuestionnaireQuestion.position)
        )
        return list((await session.execute(stmt)).scalars())

    async def issue_questionnaire(  # noqa: PLR0912, PLR0913, PLR0915 -- two sources, one dispatch
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        engagement_id: uuid.UUID,
        contact_id: uuid.UUID | None = None,
        due_date: date | None = None,
        bank_code: str | None = None,
        questionnaire_id: uuid.UUID | None = None,
    ) -> IssuedQuestionnaire:
        """Create the assessment, mint the portal link, and tell the contact.

        The question set is chosen by the engagement's tier and **snapshotted onto
        the assessment**. The bank is versioned global content that can change
        under a vendor mid-answer, and a residual score computed against a
        question set nobody can reconstruct is not defensible.

        The token is returned exactly once, here, in the link. It is stored only as
        a hash, so nothing downstream — not this service, not the database, not a
        backup — can produce it again.
        """
        engagement = await self._load_engagement(session, tenant_id, engagement_id)
        if engagement.vendor_id != vendor_id:
            raise NotFound(
                _ENGAGEMENT_GONE, detail=f"engagement {engagement_id} is not on {vendor_id}"
            )
        vendor = await self._load(session, tenant_id, vendor_id)
        if engagement.tier is None:
            raise Conflict(
                "Tier this engagement before sending a questionnaire. The tier is what "
                "decides which questions are asked.",
                detail=f"engagement {engagement_id} has no tier",
            )

        contact = await self._portal_contact(session, tenant_id, vendor.id, contact_id)
        # Two sources. A tenant questionnaire is the normal one: named, or the one
        # holding this tier. The shipped bank is used only when a caller names it,
        # which is how API clients written before questionnaires keep working.
        bank: QuestionnaireTemplate | None = None
        questions: list[QuestionnaireQuestion] = []
        levels: tuple[str, ...] = ()
        snapshot: dict[str, Any] = {}
        if bank_code:
            bank = await self._current_bank(session, bank_code)
            levels = BUNDLE_BY_TIER.get(engagement.tier, ("lite",))
            questions = await self._bank_questions(session, bank.id, levels)
            if not questions:
                raise InvalidInput(
                    "That questionnaire bank has no questions for this tier.",
                    detail=f"bank {bank.code} has no questions at levels {levels}",
                )
        else:
            chosen = await questionnaire_service.load_for_use(
                session,
                tenant_id=tenant_id,
                questionnaire_id=questionnaire_id,
                purpose="due_diligence",
                tier=engagement.tier,
            )
            if chosen is None:
                raise InvalidInput(
                    "Pick a questionnaire to send. None is set as the default for "
                    f"{engagement.tier} tier vendors.",
                    detail=f"no due diligence questionnaire for tier {engagement.tier}",
                )
            snapshot = await questionnaire_service.snapshot(
                session, tenant_id=tenant_id, questionnaire=chosen
            )
            if not snapshot["questions"]:
                raise InvalidInput(
                    "That questionnaire has no questions yet. Add some before sending it.",
                    detail=f"questionnaire {chosen.id} is empty",
                )

        cycle = await self._current_cycle(session, tenant_id, engagement.id)
        now = datetime.now(UTC)

        # Re-issuing is a *resend*, not a second review. An open assessment for
        # this cycle is refreshed in place and gets a new link; creating another
        # would duplicate every response row, leave two live tokens, and make the
        # register count one questionnaire as two.
        open_already = await self._open_assessment(session, tenant_id, engagement.id, cycle)
        if open_already is not None and self._switches_questions(open_already, bank, snapshot):
            await self._retire_unanswered(session, tenant_id, actor, open_already)
            open_already = None
        if open_already is not None:
            open_already.portal_contact_id = contact.id
            open_already.due_date = due_date or open_already.due_date
            token = await self._mint_portal_token(session, tenant_id, open_already)
            await self._audit.record(
                session,
                action="update",
                object_type="vendor_assessment",
                object_id=open_already.id,
                actor=actor,
                tenant_id=tenant_id,
                before={"portal_link": "issued"},
                after={"portal_link": "reissued", "contact_id": str(contact.id)},
            )
            await self._send_portal_invitation(vendor, contact, open_already, token)
            await session.flush()
            return IssuedQuestionnaire(
                assessment_id=open_already.id,
                contact_email=contact.email or "",
                question_count=int(open_already.scope.get("question_count", 0)),
                due_date=open_already.due_date,
                portal_url=_portal_url(token),
            )

        question_count = len(questions) if bank else len(snapshot["questions"])
        scope: dict[str, Any] = {
            "tier": engagement.tier,
            "question_count": question_count,
            "snapshotted_at": now.isoformat(),
        }
        if bank:
            scope |= {
                "bank_code": bank.code,
                "bank_version": bank.version,
                "scope_levels": list(levels),
                "question_codes": [q.code for q in questions],
            }
        else:
            scope |= {
                "questionnaire_id": snapshot["id"],
                "questionnaire_name": snapshot["name"],
                "question_keys": [q["id"] for q in snapshot["questions"]],
            }
        assessment = VendorAssessment(
            id=uuid7(),
            tenant_id=tenant_id,
            vendor_id=vendor.id,
            engagement_id=engagement.id,
            template_id=bank.id if bank else None,
            questionnaire_id=uuid.UUID(snapshot["id"]) if snapshot else None,
            cycle=cycle,
            kind="reassessment" if cycle > 1 else "initial",
            status="pending",
            due_date=due_date or (now.date() + timedelta(days=_QUESTIONNAIRE_DUE_DAYS)),
            portal_contact_id=contact.id,
            scope=scope,
        )
        session.add(assessment)
        await session.flush([assessment])

        # One row per question, unanswered. The portal then updates rows rather
        # than inventing them, so a question that was asked and ignored is
        # distinguishable from one that was never asked. A tenant question travels
        # on its row, because the questionnaire it came from can be edited later.
        for question in questions:
            session.add(
                VendorAssessmentResponse(
                    id=uuid7(),
                    tenant_id=tenant_id,
                    assessment_id=assessment.id,
                    question_id=question.id,
                )
            )
        for copied in snapshot.get("questions", []):
            session.add(
                VendorAssessmentResponse(
                    id=uuid7(),
                    tenant_id=tenant_id,
                    assessment_id=assessment.id,
                    question_key=copied["id"],
                    question_snapshot=copied,
                )
            )
        await session.flush()

        token = await self._mint_portal_token(session, tenant_id, assessment)
        await self._audit.record(
            session,
            action="create",
            object_type="vendor_assessment",
            object_id=assessment.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after={
                "vendor_id": str(vendor.id),
                "bank": bank.code if bank else None,
                "questionnaire": snapshot.get("name"),
                "tier": engagement.tier,
                "question_count": question_count,
                "contact_id": str(contact.id),
            },
        )
        await self._send_portal_invitation(vendor, contact, assessment, token)
        await session.flush()
        return IssuedQuestionnaire(
            assessment_id=assessment.id,
            contact_email=contact.email or "",
            question_count=question_count,
            due_date=assessment.due_date,
            portal_url=_portal_url(token),
        )

    @staticmethod
    def _switches_questions(
        assessment: VendorAssessment,
        bank: QuestionnaireTemplate | None,
        snapshot: dict[str, Any],
    ) -> bool:
        """Whether a resend names different questions from the ones already sent."""
        if bank is not None:
            return assessment.template_id != bank.id
        return str(assessment.questionnaire_id) != snapshot.get("id")

    async def _retire_unanswered(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor: Actor,
        assessment: VendorAssessment,
    ) -> None:
        """Swap the questionnaire on a review nobody has started answering.

        The old review is expired, its link revoked, and a new one is sent in its
        place, so the trail shows what was sent first. Once the vendor has
        answered anything, the swap is refused: their work would be thrown away.
        """
        started = (
            await session.execute(
                select(func.count())
                .select_from(VendorAssessmentResponse)
                .where(VendorAssessmentResponse.tenant_id == tenant_id)
                .where(VendorAssessmentResponse.assessment_id == assessment.id)
                .where(
                    or_(
                        VendorAssessmentResponse.answered_at.is_not(None),
                        VendorAssessmentResponse.evidence_id.is_not(None),
                    )
                )
            )
        ).scalar_one()
        if started:
            raise Conflict(
                "The vendor has started answering the questionnaire already sent, so it "
                "cannot be swapped for another. Resend it as it is.",
                detail=f"assessment {assessment.id} has {started} answered rows",
            )
        was = assessment.status
        assessment.status = "expired"
        for token in (
            await session.execute(
                select(VendorPortalToken)
                .where(VendorPortalToken.tenant_id == tenant_id)
                .where(VendorPortalToken.assessment_id == assessment.id)
                .where(VendorPortalToken.revoked_at.is_(None))
            )
        ).scalars():
            token.revoked_at = datetime.now(UTC)
        await self._audit.record(
            session,
            action="update",
            object_type="vendor_assessment",
            object_id=assessment.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"status": was},
            after={"status": "expired", "reason": "replaced by a different questionnaire"},
        )
        await session.flush()

    async def _open_assessment(
        self, session: AsyncSession, tenant_id: uuid.UUID, engagement_id: uuid.UUID, cycle: int
    ) -> VendorAssessment | None:
        """An assessment for this cycle that has not been handed back yet."""
        return (
            await session.execute(
                select(VendorAssessment)
                .where(VendorAssessment.tenant_id == tenant_id)
                .where(VendorAssessment.engagement_id == engagement_id)
                .where(VendorAssessment.cycle == cycle)
                .where(VendorAssessment.status.in_(["pending", "in_progress"]))
                .order_by(VendorAssessment.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def _portal_contact(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        vendor_id: uuid.UUID,
        contact_id: uuid.UUID | None,
    ) -> VendorContact:
        stmt = (
            select(VendorContact)
            .where(VendorContact.tenant_id == tenant_id)
            .where(VendorContact.vendor_id == vendor_id)
        )
        if contact_id is not None:
            stmt = stmt.where(VendorContact.id == contact_id)
        else:
            stmt = stmt.where(VendorContact.contact_type == "portal")
        contact = (await session.execute(stmt.limit(1))).scalar_one_or_none()
        if contact is None:
            raise InvalidInput(
                "This vendor has no portal contact to send the questionnaire to. "
                "Add one with an email address first.",
                detail=f"no portal contact on vendor {vendor_id}",
            )
        if not contact.email:
            raise InvalidInput(
                f"{contact.name} has no email address, so the questionnaire link has "
                "nowhere to go.",
                detail=f"contact {contact.id} has no email",
            )
        return contact

    async def _mint_portal_token(
        self, session: AsyncSession, tenant_id: uuid.UUID, assessment: VendorAssessment
    ) -> str:
        """Issue a token, store only its hash, and revoke any that came before.

        Revocation is a write rather than a delete, so "a link was sent on Tuesday
        and replaced on Friday" stays answerable. Re-issuing therefore invalidates
        the old link, which is the behaviour somebody expects from a resend.
        """
        now = datetime.now(UTC)
        stale = (
            await session.execute(
                select(VendorPortalToken)
                .where(VendorPortalToken.tenant_id == tenant_id)
                .where(VendorPortalToken.assessment_id == assessment.id)
                .where(VendorPortalToken.revoked_at.is_(None))
            )
        ).scalars()
        for row in stale:
            row.revoked_at = now

        token = ratelimit.new_opaque_token()
        session.add(
            VendorPortalToken(
                id=uuid7(),
                token_hash=ratelimit.hash_token(token),
                tenant_id=tenant_id,
                assessment_id=assessment.id,
                expires_at=now + timedelta(days=_PORTAL_TOKEN_DAYS),
            )
        )
        await session.flush()
        return token

    async def _send_portal_invitation(
        self,
        vendor: Vendor,
        contact: VendorContact,
        assessment: VendorAssessment,
        token: str,
    ) -> None:
        """Email the link. A vendor contact is not a member, so this goes through
        the mailer directly — ``notification_service`` targets memberships only, and
        inventing a membership for an outsider would break rule 3."""
        from verity.core.email import OutboundEmail, get_mailer  # noqa: PLC0415

        due = assessment.due_date.isoformat() if assessment.due_date else "shortly"
        count = int(assessment.scope.get("question_count", 0))
        text = (
            f"Security review for {vendor.name}\n\n"
            f"{contact.name}, we are reviewing the security of the services "
            f"{vendor.name} provides to us, and would like you to complete a short "
            f"questionnaire of {count} questions.\n\n"
            f"{_portal_url(token)}\n\n"
            f"The link is personal to this review, expires in {_PORTAL_TOKEN_DAYS} days, "
            f"and does not need an account. Please complete it by {due}.\n"
        )
        await get_mailer().send(
            OutboundEmail(
                to=contact.email or "",
                subject=f"Security review questionnaire for {vendor.name}",
                text=text,
            )
        )

    # -- scoring the review (V7) ----------------------------------------------

    async def score_assessment(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        assessment_id: uuid.UUID,
        vendor_id: uuid.UUID | None = None,
    ) -> AssessmentView:
        """Roll the answers into a residual score, and raise findings from the noes.

        Scoring and finding-raising are one transaction on purpose: a score with no
        findings behind it is a number nobody can act on, and findings with no score
        are a list nobody can prioritise.
        """
        assessment = await self._load_assessment(session, tenant_id, assessment_id)
        if vendor_id is not None and assessment.vendor_id != vendor_id:
            raise NotFound(
                _ASSESSMENT_GONE, detail=f"assessment {assessment_id} is not on vendor {vendor_id}"
            )
        engagement = await self._load_engagement(session, tenant_id, assessment.engagement_id)
        rows = await self.answers_with_questions(
            session, tenant_id=tenant_id, assessment_id=assessment.id
        )
        if not rows:
            raise Conflict(
                "There is nothing to score yet. This questionnaire has no questions.",
                detail=f"assessment {assessment_id} has no responses",
            )

        tiering = await self._latest_tiering(session, tenant_id, engagement.id, assessment.cycle)
        inherent = tiering.inherent_score if tiering else 0.0
        breakdown = scoring.compute_residual(self._scored_answers(rows), inherent=inherent)

        # Read before the write, rather than asserting what it must have been.
        was = {
            "status": assessment.status,
            "residual_score": assessment.residual_score,
            "grade": assessment.grade,
        }
        assessment.residual_score = breakdown.score
        assessment.grade = breakdown.grade
        assessment.domain_scores = {
            d.domain: {"posture": d.posture, "residual": d.residual, "answered": d.answered}
            for d in breakdown.domains
        }
        assessment.score_snapshot = {
            "inherent": breakdown.inherent,
            "control_ceiling": scoring.CONTROL_CEILING,
            "domain_weights": scoring.DEFAULT_DOMAIN_WEIGHTS,
            "steps": [
                {"label": s.label, "value": s.value, "detail": s.detail} for s in breakdown.steps
            ],
        }
        assessment.status = "scored"

        raised = await self._raise_findings(session, tenant_id, actor, assessment, rows)
        await self._recache_residual(session, tenant_id, assessment)

        await self._audit.record(
            session,
            action="update",
            object_type="vendor_assessment",
            object_id=assessment.id,
            actor=actor,
            tenant_id=tenant_id,
            before=was,
            after={
                "status": "scored",
                "residual_score": breakdown.score,
                "grade": breakdown.grade,
                "findings_raised": raised,
            },
        )
        await session.flush()
        return await self.get_assessment(session, tenant_id=tenant_id, assessment_id=assessment.id)

    @staticmethod
    def _scored_answers(
        rows: Sequence[tuple[VendorAssessmentResponse, AskedQuestion]],
    ) -> list[scoring.Answer]:
        """The answers that move a residual score, in scoring's own shape.

        A bank row scores by its yes/partial/no/na vocabulary, as it always has. A
        tenant question scores only if it was asked (its condition was met) and is a
        choice with credit to give; its picked option carries the credit and says
        whether it is a gap. Text, numbers, dates and files inform the reviewer and
        never become points.
        """
        shown = visible_keys(rows)
        answers: list[scoring.Answer] = []
        for response, question in rows:
            if question.from_bank:
                answers.append(
                    scoring.Answer(
                        question_key=question.code,
                        domain=question.domain,
                        answer=response.answer or "",
                        weight=question.weight,
                        critical_control=question.critical,
                    )
                )
                continue
            if question.key not in shown or not question.scored:
                continue
            picked = (
                picked_options(question, response_value(response, question))
                if is_answered(response, question)
                else []
            )
            creditable = [o for o in picked if not o.not_applicable]
            answers.append(
                scoring.Answer(
                    question_key=question.code,
                    domain=question.domain,
                    answer=",".join(o.key for o in picked),
                    weight=question.weight,
                    critical_control=question.critical,
                    credit=max(o.score for o in creditable) / 100 if creditable else None,
                    not_applicable=bool(picked) and not creditable,
                    flagged=any(o.flag for o in picked),
                )
            )
        return answers

    @staticmethod
    def _failed(
        response: VendorAssessmentResponse, question: AskedQuestion, shown: set[str]
    ) -> bool:
        """Whether this answer is a gap that owes a finding."""
        if question.from_bank:
            return response.answer == "no"
        return (
            question.key in shown
            and is_answered(response, question)
            and any(o.flag for o in picked_options(question, response_value(response, question)))
        )

    async def _raise_findings(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor: Actor,
        assessment: VendorAssessment,
        rows: Sequence[tuple[VendorAssessmentResponse, AskedQuestion]],
    ) -> int:
        """One finding per gap: a ``no`` on a bank question, or an option marked as one.

        Idempotent per (assessment, question): re-scoring after a corrected answer
        updates the finding rather than raising a second one, and a question whose
        answer has changed away from the gap closes the finding it caused.
        """
        existing = {
            (row.question_id or row.question_key): row
            for row in (
                await session.execute(
                    select(VendorFinding)
                    .where(VendorFinding.tenant_id == tenant_id)
                    .where(VendorFinding.assessment_id == assessment.id)
                )
            ).scalars()
        }
        raised = 0
        now = datetime.now(UTC)
        shown = visible_keys(rows)
        for response, question in rows:
            failed = self._failed(response, question, shown)
            found = existing.get(question.id if question.from_bank else question.key)
            if not failed:
                if found is not None and found.status in OPEN_FINDING_STATUSES:
                    before = AuditService.snapshot(found, fields=_FINDING_SNAPSHOT)
                    found.status = "closed"
                    found.closed_at = now
                    # Its own row, naming the finding. A corrected answer closing a
                    # finding is a state change on that finding, and rolling it up
                    # into a count on the assessment loses which one moved.
                    await self._audit.record(
                        session,
                        action="update",
                        object_type="vendor_finding",
                        object_id=found.id,
                        actor=actor,
                        tenant_id=tenant_id,
                        before=before,
                        after={
                            **AuditService.snapshot(found, fields=_FINDING_SNAPSHOT),
                            "reason": "the answer that raised it changed",
                        },
                    )
                continue
            severity = _finding_severity(question)
            if found is not None:
                before = AuditService.snapshot(found, fields=_FINDING_SNAPSHOT)
                found.severity = severity
                found.is_blocking = question.blocking
                after = AuditService.snapshot(found, fields=_FINDING_SNAPSHOT)
                if before != after:
                    await self._audit.record(
                        session,
                        action="update",
                        object_type="vendor_finding",
                        object_id=found.id,
                        actor=actor,
                        tenant_id=tenant_id,
                        before=before,
                        after=after,
                    )
                continue
            new_finding = VendorFinding(
                id=uuid7(),
                tenant_id=tenant_id,
                vendor_id=assessment.vendor_id,
                engagement_id=assessment.engagement_id,
                assessment_id=assessment.id,
                question_id=question.id if question.from_bank else None,
                question_key=None if question.from_bank else question.key,
                title=_finding_title(question),
                detail=question.prompt,
                finding_source="assessment",
                severity=severity,
                is_blocking=question.blocking,
                sla_due=now.date() + timedelta(days=_FINDING_SLA_DAYS[severity]),
            )
            session.add(new_finding)
            await session.flush([new_finding])
            await self._audit.record(
                session,
                action="create",
                object_type="vendor_finding",
                object_id=new_finding.id,
                actor=actor,
                tenant_id=tenant_id,
                before=None,
                after=AuditService.snapshot(new_finding, fields=_FINDING_SNAPSHOT),
            )
            raised += 1
        await session.flush()
        return raised

    async def _recache_residual(
        self, session: AsyncSession, tenant_id: uuid.UUID, assessment: VendorAssessment
    ) -> None:
        """Refresh the vendor's cached worst residual and grade (V10).

        Worst means highest score, and the grade is taken from the same assessment
        rather than computed separately — a vendor showing a score from one
        engagement and a grade from another would be quietly incoherent.
        """
        rows = list(
            (
                await session.execute(
                    select(VendorAssessment)
                    .where(VendorAssessment.tenant_id == tenant_id)
                    .where(VendorAssessment.vendor_id == assessment.vendor_id)
                    .where(VendorAssessment.residual_score.is_not(None))
                )
            ).scalars()
        )
        if not rows:
            return
        worst = max(rows, key=lambda a: a.residual_score or 0.0)
        vendor = await self._load(session, tenant_id, assessment.vendor_id)
        vendor.current_residual_score = worst.residual_score
        vendor.current_grade = worst.grade

    # -- reading the review ----------------------------------------------------

    async def _load_assessment(
        self, session: AsyncSession, tenant_id: uuid.UUID, assessment_id: uuid.UUID
    ) -> VendorAssessment:
        row = await session.get(VendorAssessment, assessment_id, populate_existing=True)
        if row is None or row.tenant_id != tenant_id:
            raise NotFound(_ASSESSMENT_GONE, detail=f"vendor assessment {assessment_id}")
        return row

    async def answers_with_questions(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, assessment_id: uuid.UUID
    ) -> list[tuple[VendorAssessmentResponse, AskedQuestion]]:
        """The assessment's rows with the question each one asked, in asked order.

        A row answers a bank question (joined) or carries its own snapshot. Both
        come back as ``AskedQuestion``, so nothing downstream tells them apart.
        """
        stmt = (
            select(VendorAssessmentResponse, QuestionnaireQuestion)
            .outerjoin(
                QuestionnaireQuestion,
                QuestionnaireQuestion.id == VendorAssessmentResponse.question_id,
            )
            .where(VendorAssessmentResponse.tenant_id == tenant_id)
            .where(VendorAssessmentResponse.assessment_id == assessment_id)
        )
        pairs = [
            (r, asked_from_bank(q) if q is not None else asked_from_snapshot(r.question_snapshot))
            for r, q in (await session.execute(stmt)).all()
        ]
        return sorted(pairs, key=lambda pair: pair[1].position)

    @staticmethod
    def _response_view(
        response: VendorAssessmentResponse, question: AskedQuestion, shown: set[str]
    ) -> ResponseView:
        visible = question.key in shown
        value = response_value(response, question) if is_answered(response, question) else None
        return ResponseView(
            id=response.id,
            question_id=question.id,
            question_code=question.code,
            body=question.prompt,
            domain=question.domain,
            domain_label=RISK_DOMAIN_LABELS[question.domain],
            scope_level=question.scope_level,
            answer_type=question.answer_type,
            weight=question.weight,
            critical_control=question.critical,
            non_negotiable=question.blocking,
            evidence_required=question.evidence == "required",
            framework_refs=list(question.framework_refs),
            answer=response.answer,
            implementation_notes=response.implementation_notes,
            na_justification=response.na_justification,
            evidence_id=response.evidence_id,
            answered_at=response.answered_at,
            section=question.section,
            help_text=question.help_text,
            options=[
                {
                    "key": o.key,
                    "label": o.label,
                    "score": o.score,
                    "flag": o.flag,
                    "not_applicable": o.not_applicable,
                }
                for o in question.options
            ],
            value=value,
            answer_labels=answer_labels(response, question),
            flagged=VendorService._failed(response, question, shown),
            required=question.required,
            evidence=question.evidence,
            visible=visible,
            owes_evidence=owes_evidence(response, question, visible=visible),
        )

    def _assessment_view(
        self,
        assessment: VendorAssessment,
        responses: Sequence[tuple[VendorAssessmentResponse, AskedQuestion]],
        findings: Sequence[VendorFinding],
        names: dict[uuid.UUID, str],
        token: VendorPortalToken | None,
    ) -> AssessmentView:
        shown = visible_keys(responses)
        asked = [(r, q) for r, q in responses if q.key in shown]
        answered = sum(1 for r, q in asked if is_answered(r, q))
        unanswered = sum(1 for r, q in asked if q.required and not is_answered(r, q))
        missing_evidence = sum(1 for r, q in asked if owes_evidence(r, q))
        return AssessmentView(
            id=assessment.id,
            vendor_id=assessment.vendor_id,
            engagement_id=assessment.engagement_id,
            cycle=assessment.cycle,
            kind=assessment.kind,
            review_format=assessment.review_format,
            assessment_domain=assessment.assessment_domain,
            status=assessment.status,
            due_date=assessment.due_date,
            residual_score=assessment.residual_score,
            grade=assessment.grade,
            domain_scores=dict(assessment.domain_scores or {}),
            score_steps=list((assessment.score_snapshot or {}).get("steps", [])),
            scope=dict(assessment.scope or {}),
            question_count=len(asked),
            answered_count=answered,
            unanswered_count=unanswered,
            missing_evidence_count=missing_evidence,
            submitted_at=assessment.submitted_at,
            responses=[self._response_view(r, q, shown) for r, q in responses],
            findings=[self._finding_view(f, names) for f in findings],
            portal_link_live=bool(
                token and token.revoked_at is None and token.expires_at > datetime.now(UTC)
            ),
            portal_link_expires_at=token.expires_at if token else None,
            created_at=assessment.created_at,
            updated_at=assessment.updated_at,
        )

    @staticmethod
    def _finding_view(
        finding: VendorFinding,
        names: dict[uuid.UUID, str],
        vendor_name: str | None = None,
        vendor_tier: str | None = None,
    ) -> FindingView:
        owner = finding.owner_membership_id
        return FindingView(
            id=finding.id,
            vendor_id=finding.vendor_id,
            vendor_name=vendor_name,
            vendor_tier=vendor_tier,
            assessment_id=finding.assessment_id,
            # A bank question's id, or the id a tenant question carried in its
            # snapshot: either way, the question that raised it.
            question_id=finding.question_id
            or (uuid.UUID(finding.question_key) if finding.question_key else None),
            title=finding.title,
            detail=finding.detail,
            finding_source=finding.finding_source,
            severity=finding.severity,
            status=finding.status,
            treatment=finding.treatment,
            is_blocking=finding.is_blocking,
            sla_due=finding.sla_due,
            owner_membership_id=owner,
            owner_name=names.get(owner) if owner else None,
            task_id=finding.task_id,
            accepted_until=finding.accepted_until,
            accepted_rationale=finding.accepted_rationale,
            closed_at=finding.closed_at,
            # The seam to modules/risk, which has no tables. Always None today.
            promoted_risk_id=finding.promoted_risk_id,
            created_at=finding.created_at,
        )

    async def _live_token(
        self, session: AsyncSession, tenant_id: uuid.UUID, assessment_id: uuid.UUID
    ) -> VendorPortalToken | None:
        return (
            await session.execute(
                select(VendorPortalToken)
                # Explicit, and load-bearing: this table has no policy, so the
                # filter is the only wall rather than the first of two.
                .where(VendorPortalToken.tenant_id == tenant_id)
                .where(VendorPortalToken.assessment_id == assessment_id)
                .where(VendorPortalToken.revoked_at.is_(None))
                .order_by(VendorPortalToken.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def get_assessment(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, assessment_id: uuid.UUID
    ) -> AssessmentView:
        assessment = await self._load_assessment(session, tenant_id, assessment_id)
        responses = await self.answers_with_questions(
            session, tenant_id=tenant_id, assessment_id=assessment.id
        )
        findings = list(
            (
                await session.execute(
                    select(VendorFinding)
                    .where(VendorFinding.tenant_id == tenant_id)
                    .where(VendorFinding.assessment_id == assessment.id)
                    .order_by(VendorFinding.created_at)
                )
            ).scalars()
        )
        names = await self._member_names(session, tenant_id)
        token = await self._live_token(session, tenant_id, assessment.id)
        return self._assessment_view(assessment, responses, findings, names, token)

    async def list_findings(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        vendor_id: uuid.UUID | None = None,
        statuses: tuple[str, ...] = (),
    ) -> list[FindingView]:
        stmt = select(VendorFinding).where(VendorFinding.tenant_id == tenant_id)
        if vendor_id is not None:
            stmt = stmt.where(VendorFinding.vendor_id == vendor_id)
        if statuses:
            stmt = stmt.where(VendorFinding.status.in_(list(statuses)))
        rows = list((await session.execute(stmt)).scalars())
        names = await self._member_names(session, tenant_id)
        # One lookup for the whole page rather than one per row. Without it the
        # cross-vendor queue can only print an id, which is not a work queue.
        vendors = await self._vendor_facts(session, tenant_id, {f.vendor_id for f in rows})
        views = [
            self._finding_view(
                f,
                names,
                vendors.get(f.vendor_id, (None, None))[0],
                vendors.get(f.vendor_id, (None, None))[1],
            )
            for f in rows
        ]
        views.sort(key=lambda f: (FINDING_SEVERITIES.index(f.severity), f.sla_due or date.max))
        return views

    async def _vendor_facts(
        self, session: AsyncSession, tenant_id: uuid.UUID, vendor_ids: set[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[str, str | None]]:
        """Name and tier for a page of findings, in one select."""
        if not vendor_ids:
            return {}
        rows = await session.execute(
            select(Vendor.id, Vendor.name, Vendor.tier)
            .where(Vendor.tenant_id == tenant_id)
            .where(Vendor.id.in_(list(vendor_ids)))
        )
        return {row.id: (row.name, row.tier) for row in rows}

    async def open_critical_count(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, vendor_id: uuid.UUID
    ) -> int:
        """What the findings stage and the approval gate ask for.

        An accepted risk does not count as open: acceptance is a decision somebody
        made and time-boxed, not an outstanding item.
        """
        return (
            await session.execute(
                select(func.count())
                .select_from(VendorFinding)
                .where(VendorFinding.tenant_id == tenant_id)
                .where(VendorFinding.vendor_id == vendor_id)
                .where(VendorFinding.severity == "critical")
                .where(VendorFinding.status.in_(list(OPEN_FINDING_STATUSES)))
            )
        ).scalar_one()

    async def tenant_display_name(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> str:
        """The organisation's own name, for the portal page.

        A vendor contact opening a link should see who is asking. Read through the
        tenancy service rather than the table (rule 4), and degraded to a neutral
        word rather than raising: a missing display name must not take the
        questionnaire down.

        The trading name is what a third party would recognise; the legal name is
        the fallback because every tenant has one. There is no ``name`` column —
        asking for one is how every portal page came out addressed from "our
        organisation".
        """
        from verity.modules.tenancy.service import tenancy_service  # noqa: PLC0415

        try:
            profile = await tenancy_service.get_tenant(session, tenant_id)
        except Exception:
            return "our organisation"
        return profile.trading_name or profile.legal_name or "our organisation"

    # -- acting on a finding ---------------------------------------------------

    async def _load_finding(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        vendor_id: uuid.UUID,
        finding_id: uuid.UUID,
    ) -> VendorFinding:
        row = await session.get(VendorFinding, finding_id, populate_existing=True)
        if row is None or row.tenant_id != tenant_id or row.vendor_id != vendor_id:
            raise NotFound(_FINDING_GONE, detail=f"vendor finding {finding_id} on {vendor_id}")
        return row

    async def get_finding(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, finding_id: uuid.UUID
    ) -> FindingView:
        """One finding with its vendor's name, for the risk register's promotion
        (rule 4: the risk module reads it here, never from the table)."""
        row = await session.get(VendorFinding, finding_id, populate_existing=True)
        if row is None or row.tenant_id != tenant_id:
            raise NotFound(_FINDING_GONE, detail=f"vendor finding {finding_id}")
        facts = await self._vendor_facts(session, tenant_id, {row.vendor_id})
        name, tier = facts.get(row.vendor_id, (None, None))
        return self._finding_view(row, await self._member_names(session, tenant_id), name, tier)

    async def mark_finding_promoted(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        finding_id: uuid.UUID,
        risk_id: uuid.UUID,
    ) -> None:
        """Record that the finding now lives in the risk register (spec ¶85)."""
        row = await session.get(VendorFinding, finding_id, populate_existing=True)
        if row is None or row.tenant_id != tenant_id:
            raise NotFound(_FINDING_GONE, detail=f"vendor finding {finding_id}")
        row.promoted_risk_id = risk_id
        await self._audit.record(
            session,
            action="update",
            object_type="vendor_finding",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"promoted_risk_id": None},
            after={"promoted_risk_id": str(risk_id)},
        )
        await session.flush([row])

    async def remediate_finding(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        finding_id: uuid.UUID,
        owner_membership_id: uuid.UUID | None = None,
        due_at: datetime | None = None,
    ) -> FindingView:
        """Open a real task for the fix, in the tasks module.

        Not a vendor-local to-do table. The tasks module already carries
        assignment, SLA, transitions and CAPA, and a second worse one here would be
        invisible to every dashboard that counts work.
        """
        finding = await self._load_finding(session, tenant_id, vendor_id, finding_id)
        if finding.task_id is not None:
            raise Conflict(
                "This finding already has a remediation task open.",
                detail=f"finding {finding_id} already linked to task {finding.task_id}",
            )
        if finding.status not in OPEN_FINDING_STATUSES:
            raise Conflict(
                "This finding is closed. Reopen it before planning remediation.",
                detail=f"finding {finding_id} is {finding.status}",
            )
        vendor = await self._load(session, tenant_id, finding.vendor_id)

        from verity.modules.tasks.service import task_service  # noqa: PLC0415

        task = await task_service.create_task(
            session,
            tenant_id=tenant_id,
            actor=actor,
            task_kind="issue",
            title=f"{vendor.name}: {finding.title}",
            description=finding.detail,
            priority=_TASK_PRIORITY[finding.severity],
            category="vendor",
            owner_membership_id=owner_membership_id or finding.owner_membership_id,
            due_at=due_at
            or (
                datetime.combine(finding.sla_due, datetime.min.time(), tzinfo=UTC)
                if finding.sla_due
                else None
            ),
            raised_from_type="vendor_finding",
        )
        before = AuditService.snapshot(finding, fields=_FINDING_SNAPSHOT)
        finding.task_id = task.id
        finding.status = "in_remediation"
        finding.treatment = "remediate"
        if owner_membership_id is not None:
            finding.owner_membership_id = owner_membership_id
        await self._audit.record(
            session,
            action="update",
            object_type="vendor_finding",
            object_id=finding.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(finding, fields=_FINDING_SNAPSHOT),
        )
        await session.flush()
        names = await self._member_names(session, tenant_id)
        return self._finding_view(finding, names)

    async def accept_finding(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        finding_id: uuid.UUID,
        until: date,
        rationale: str,
    ) -> FindingView:
        """Accept the risk, for a stated time and a stated reason.

        Both are required, and the expiry must be in the future: an open-ended
        acceptance is a risk nobody will look at again, which is the failure this
        whole record exists to prevent.
        """
        finding = await self._load_finding(session, tenant_id, vendor_id, finding_id)
        if not rationale.strip():
            raise InvalidInput(
                "Say why this risk is acceptable. The rationale is what a reviewer "
                "reads when the acceptance comes up for renewal.",
                detail="acceptance without a rationale",
            )
        if until <= datetime.now(UTC).date():
            raise InvalidInput(
                "The acceptance has to expire in the future. Pick a review date.",
                detail=f"accepted_until {until} is not in the future",
            )
        before = AuditService.snapshot(finding, fields=_FINDING_SNAPSHOT)
        finding.status = "accepted"
        finding.treatment = "accept"
        finding.accepted_until = until
        finding.accepted_rationale = rationale.strip()
        finding.accepted_by_membership_id = actor.id if isinstance(actor, Membership) else None
        await self._audit.record(
            session,
            action="approve",
            object_type="vendor_finding",
            object_id=finding.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(finding, fields=_FINDING_SNAPSHOT),
        )
        await session.flush()
        names = await self._member_names(session, tenant_id)
        return self._finding_view(finding, names)

    async def close_finding(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        finding_id: uuid.UUID,
        note: str | None = None,
    ) -> FindingView:
        finding = await self._load_finding(session, tenant_id, vendor_id, finding_id)
        before = AuditService.snapshot(finding, fields=_FINDING_SNAPSHOT)
        finding.status = "closed"
        finding.closed_at = datetime.now(UTC)
        await self._audit.record(
            session,
            action="update",
            object_type="vendor_finding",
            object_id=finding.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after={**AuditService.snapshot(finding, fields=_FINDING_SNAPSHOT), "note": note},
        )
        await session.flush()
        names = await self._member_names(session, tenant_id)
        return self._finding_view(finding, names)

    # -- the roster, and who may decide (section 4) ----------------------------

    async def roster(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> dict[str, tuple[uuid.UUID, ...]]:
        """Role -> the memberships holding it. The resolution half of spec 82."""
        rows = list(
            (
                await session.execute(
                    select(VendorTeamRosterEntry).where(
                        VendorTeamRosterEntry.tenant_id == tenant_id
                    )
                )
            ).scalars()
        )
        by_role: dict[str, list[uuid.UUID]] = {}
        for row in rows:
            by_role.setdefault(row.role, []).append(row.membership_id)
        return {role: tuple(ids) for role, ids in by_role.items()}

    async def set_roster_role(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        role: str,
        membership_id: uuid.UUID,
    ) -> dict[str, tuple[uuid.UUID, ...]]:
        self._check_vocabulary(role, ROSTER_ROLES, field_name="role")
        existing = (
            await session.execute(
                select(VendorTeamRosterEntry)
                .where(VendorTeamRosterEntry.tenant_id == tenant_id)
                .where(VendorTeamRosterEntry.role == role)
                .where(VendorTeamRosterEntry.membership_id == membership_id)
            )
        ).scalar_one_or_none()
        if existing is None:
            session.add(
                VendorTeamRosterEntry(
                    id=uuid7(), tenant_id=tenant_id, role=role, membership_id=membership_id
                )
            )
            await self._audit.record(
                session,
                action="create",
                object_type="vendor_team_roster",
                object_id=membership_id,
                actor=actor,
                tenant_id=tenant_id,
                before=None,
                after={"role": role, "membership_id": str(membership_id)},
            )
        await session.flush()
        return await self.roster(session, tenant_id=tenant_id)

    async def _disqualified_approvers(
        self, session: AsyncSession, tenant_id: uuid.UUID, engagement: VendorEngagement
    ) -> dict[uuid.UUID, str]:
        """Who may not decide this gate, and why (V4).

        **Two exclusions, not one.** ER 122's prose excludes the vendor's business
        owner *and* whoever submitted the stage; the diagram annotation names only
        the submitter. The prose is the stricter reading and the one an auditor
        expects, and it has a consequence worth stating: a one-admin workspace
        cannot approve its own vendors. That is correct, and it is the same rule
        the vulnerability exception flow already enforces.

        Returned as reasons rather than a set, so the approver picker can grey a
        name *and say why* — enforcing this only on submit means the user has
        already written a rationale before learning the rule.
        """
        vendor = await self._load(session, tenant_id, engagement.vendor_id)
        blocked: dict[uuid.UUID, str] = {}
        if vendor.business_owner_membership_id:
            blocked[vendor.business_owner_membership_id] = "business owner of this vendor"
        submitter = await self._stage_submitter(session, tenant_id, engagement)
        if submitter is not None:
            blocked.setdefault(submitter, "submitted this stage for approval")
        return blocked

    async def _stage_submitter(
        self, session: AsyncSession, tenant_id: uuid.UUID, engagement: VendorEngagement
    ) -> uuid.UUID | None:
        """Who advanced the engagement into the approval stage.

        Read from the transition history rather than stored on the stage: the
        history is append-only, so this answer cannot be edited after the fact by
        anybody, including us.
        """
        row = (
            await session.execute(
                select(VendorTransition)
                .where(VendorTransition.tenant_id == tenant_id)
                .where(VendorTransition.engagement_id == engagement.id)
                .where(VendorTransition.to_stage == "approval")
                .order_by(VendorTransition.occurred_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return row.actor_membership_id if row else None

    async def approvers(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        engagement_id: uuid.UUID,
        vendor_id: uuid.UUID | None = None,
    ) -> list[ApproverView]:
        """Everyone who could decide, with the disqualified ones marked and reasoned.

        Served so the interface can grey a name at the moment of choosing rather
        than refusing it after a rationale has been written.
        """
        engagement = await self._load_engagement(session, tenant_id, engagement_id)
        if vendor_id is not None and engagement.vendor_id != vendor_id:
            raise NotFound(
                _ENGAGEMENT_GONE, detail=f"engagement {engagement_id} not on {vendor_id}"
            )
        blocked = await self._disqualified_approvers(session, tenant_id, engagement)
        names = await self._member_names(session, tenant_id)
        roster = await self.roster(session, tenant_id=tenant_id)
        approver_roles = {
            m for role in ("exec_approver", "tprm_lead") for m in roster.get(role, ())
        }
        return [
            ApproverView(
                membership_id=member_id,
                name=name,
                is_designated_approver=member_id in approver_roles,
                disqualified_reason=blocked.get(member_id),
            )
            for member_id, name in sorted(names.items(), key=lambda kv: kv[1].lower())
        ]

    # -- the gate --------------------------------------------------------------

    async def decide(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        engagement_id: uuid.UUID,
        decision: str,
        rationale: str,
        conditions: Sequence[ConditionInput] = (),
    ) -> VendorDetailView:
        """Decide the approval gate. Four-valued, segregated, and append-only (V3, V4).

        ``defer`` is deliberately not ``reject``: a product offering only the two
        extremes gets ``reject`` used to mean "not yet", which then reads as a
        refused vendor forever.

        The decision does not itself advance the stage. It writes the record the
        gate's exit rule looks for, and the advance stays an explicit act — which
        is what makes the gate-freshness rule work, because a send-back can then
        restart the stage without anything having to un-approve.
        """
        self._check_vocabulary(decision, APPROVAL_DECISIONS, field_name="decision")
        if not rationale.strip():
            raise InvalidInput(
                "Say why. A decision with no reasoning is a signature with no basis, "
                "and it is the first thing an auditor asks to see.",
                detail="approval without a rationale",
            )
        engagement = await self._load_engagement(session, tenant_id, engagement_id)
        if engagement.vendor_id != vendor_id:
            raise NotFound(
                _ENGAGEMENT_GONE, detail=f"engagement {engagement_id} not on {vendor_id}"
            )
        vendor = await self._load(session, tenant_id, vendor_id)

        deciding = actor.id if isinstance(actor, Membership) else None
        blocked = await self._disqualified_approvers(session, tenant_id, engagement)
        if deciding is not None and deciding in blocked:
            names = await self._member_names(session, tenant_id)
            raise Conflict(
                f"{names.get(deciding, 'You')} cannot approve this vendor: "
                f"{blocked[deciding]}. Somebody else has to decide.",
                detail=f"segregation of duties: {deciding} is {blocked[deciding]}",
            )
        if decision == "approve_with_conditions" and not conditions:
            raise InvalidInput(
                "An approval with conditions needs at least one condition. Without "
                "one it is an unconditional approval written more elaborately.",
                detail="approve_with_conditions with no conditions",
            )

        cycle = await self._current_cycle(session, tenant_id, engagement.id)
        stage = await self._stage_row(session, tenant_id, engagement.id, cycle, "approval")
        # The gate has to have been reached. Without this a reviewer could approve
        # at intake, before a single stage of the review had happened — which
        # would make the whole lifecycle decorative.
        if stage is None or stage.entered_at is None:
            raise Conflict(
                "This engagement has not reached the approval stage yet. Work through "
                "the lifecycle first; the gate is the last thing, not the first.",
                detail=f"approval stage not entered on engagement {engagement.id}",
            )
        if stage.status == "complete":
            raise Conflict(
                "This gate has already been passed. Send the review back if it needs "
                "deciding again.",
                detail=f"approval stage already complete on engagement {engagement.id}",
            )
        now = datetime.now(UTC)
        approval = VendorApproval(
            id=uuid7(),
            tenant_id=tenant_id,
            vendor_id=vendor.id,
            engagement_id=engagement.id,
            stage_id=stage.id,
            cycle=cycle,
            decision=decision,
            rationale=rationale.strip(),
            # Frozen here: the business owner can change, and "was segregation of
            # duties applied" has to stay answerable from the row itself.
            excluded_membership_ids=[str(m) for m in blocked],
            decided_by_membership_id=deciding,
            decided_at=now,
        )
        session.add(approval)
        await session.flush([approval])

        for condition in conditions:
            await self._add_condition(session, tenant_id, actor, vendor, approval, condition)

        if decision == "reject":
            engagement.status = "on_hold"
        elif decision in {"approve", "approve_with_conditions"}:
            engagement.status = "approved"
        await self._recache(session, tenant_id, vendor)
        await self._audit.record(
            session,
            action="approve",
            object_type="vendor_approval",
            object_id=approval.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after={
                "decision": decision,
                "engagement_id": str(engagement.id),
                "conditions": len(conditions),
                "excluded": approval.excluded_membership_ids,
            },
        )
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=vendor.id)

    async def _stage_row(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        engagement_id: uuid.UUID,
        cycle: int,
        stage: str,
    ) -> VendorStage | None:
        return (
            await session.execute(
                select(VendorStage)
                .where(VendorStage.tenant_id == tenant_id)
                .where(VendorStage.engagement_id == engagement_id)
                .where(VendorStage.cycle == cycle)
                .where(VendorStage.stage == stage)
            )
        ).scalar_one_or_none()

    async def _add_condition(  # noqa: PLR0913, PLR0917
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor: Vendor,
        approval: VendorApproval,
        data: ConditionInput,
    ) -> VendorApprovalCondition:
        """A condition, and the real task that chases it.

        A condition with no task is a note in a record nobody opens again. The
        tasks module already has assignment, SLA and transitions, so the condition
        row holds the compliance meaning and the task holds the work.
        """
        if not data.description.strip():
            raise InvalidInput("Say what the condition is.", detail="condition with no description")
        condition = VendorApprovalCondition(
            id=uuid7(),
            tenant_id=tenant_id,
            approval_id=approval.id,
            description=data.description.strip(),
            owner_membership_id=data.owner_membership_id,
            due_date=data.due_date,
        )
        session.add(condition)
        await session.flush([condition])

        from verity.modules.tasks.service import task_service  # noqa: PLC0415

        task = await task_service.create_task(
            session,
            tenant_id=tenant_id,
            actor=actor,
            task_kind="task",
            title=f"{vendor.name}: {data.description.strip()[:180]}",
            description=(
                f"A condition of the approval decided on "
                f"{approval.decided_at.date().isoformat()}.\n\n{approval.rationale}"
            ),
            priority="high",
            category="vendor",
            owner_membership_id=data.owner_membership_id,
            due_at=(
                datetime.combine(data.due_date, datetime.min.time(), tzinfo=UTC)
                if data.due_date
                else None
            ),
            raised_from_type="vendor_approval_condition",
        )
        condition.task_id = task.id
        await session.flush()
        return condition

    async def close_condition(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        condition_id: uuid.UUID,
        status: str,
        waived_reason: str | None = None,
    ) -> ConditionView:
        """Mark a condition met or waived. A waiver states why; being met does not."""
        self._check_vocabulary(status, CONDITION_STATUSES, field_name="status")
        condition = await session.get(VendorApprovalCondition, condition_id, populate_existing=True)
        if condition is None or condition.tenant_id != tenant_id:
            raise NotFound(_CONDITION_GONE, detail=f"vendor approval condition {condition_id}")
        # The path names a vendor; a condition on a different vendor's approval is
        # a stale link, not something to act on.
        approval = await session.get(VendorApproval, condition.approval_id)
        if approval is None or approval.vendor_id != vendor_id:
            raise NotFound(_CONDITION_GONE, detail=f"condition {condition_id} not on {vendor_id}")
        if status == "waived" and not (waived_reason or "").strip():
            raise InvalidInput(
                "Say why the condition is being waived. A waiver with no reason is "
                "indistinguishable from it having been forgotten.",
                detail="waiver with no reason",
            )
        before = AuditService.snapshot(condition, fields=("status", "waived_reason"))
        condition.status = status
        condition.waived_reason = (waived_reason or "").strip() or None
        await self._audit.record(
            session,
            action="update",
            object_type="vendor_approval_condition",
            object_id=condition.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(condition, fields=("status", "waived_reason")),
        )
        await session.flush()
        names = await self._member_names(session, tenant_id)
        return self._condition_view(condition, names)

    @staticmethod
    def _condition_view(row: VendorApprovalCondition, names: dict[uuid.UUID, str]) -> ConditionView:
        owner = row.owner_membership_id
        return ConditionView(
            id=row.id,
            approval_id=row.approval_id,
            description=row.description,
            owner_membership_id=owner,
            owner_name=names.get(owner) if owner else None,
            due_date=row.due_date,
            status=row.status,
            task_id=row.task_id,
            waived_reason=row.waived_reason,
        )

    async def _approvals_for(
        self, session: AsyncSession, tenant_id: uuid.UUID, vendor_id: uuid.UUID
    ) -> list[ApprovalView]:
        rows = list(
            (
                await session.execute(
                    select(VendorApproval)
                    .where(VendorApproval.tenant_id == tenant_id)
                    .where(VendorApproval.vendor_id == vendor_id)
                    .order_by(VendorApproval.decided_at.desc())
                )
            ).scalars()
        )
        if not rows:
            return []
        conditions = list(
            (
                await session.execute(
                    select(VendorApprovalCondition)
                    .where(VendorApprovalCondition.tenant_id == tenant_id)
                    .where(VendorApprovalCondition.approval_id.in_([r.id for r in rows]))
                )
            ).scalars()
        )
        names = await self._member_names(session, tenant_id)
        by_approval: dict[uuid.UUID, list[ConditionView]] = {}
        for condition in conditions:
            by_approval.setdefault(condition.approval_id, []).append(
                self._condition_view(condition, names)
            )
        return [
            ApprovalView(
                id=row.id,
                engagement_id=row.engagement_id,
                cycle=row.cycle,
                stage_id=row.stage_id,
                decision=row.decision,
                rationale=row.rationale,
                decided_by_membership_id=row.decided_by_membership_id,
                decided_by_name=names.get(row.decided_by_membership_id)
                if row.decided_by_membership_id
                else None,
                excluded_membership_ids=list(row.excluded_membership_ids or []),
                decided_at=row.decided_at,
                conditions=by_approval.get(row.id, []),
            )
            for row in rows
        ]

    # -- the paperwork ---------------------------------------------------------

    async def add_document(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        data: DocumentInput,
    ) -> DocumentView:
        """Record a SOC report, certificate or DPA and the window it covers.

        ``valid_until`` is what the expiry sweep reads, so a document with no
        expiry is accepted but reported as such rather than treated as permanent.
        """
        vendor = await self._load(session, tenant_id, vendor_id)
        self._check_vocabulary(data.doc_type, DOC_TYPES, field_name="doc_type")
        if data.issue_date and data.valid_until and data.valid_until < data.issue_date:
            raise InvalidInput(
                "The document expires before it was issued. Check the dates.",
                detail=f"valid_until {data.valid_until} precedes issue_date {data.issue_date}",
            )
        row = VendorDocument(
            id=uuid7(),
            tenant_id=tenant_id,
            vendor_id=vendor.id,
            doc_type=data.doc_type,
            title=self._require_name(data.title, what="document"),
            issue_date=data.issue_date,
            valid_until=data.valid_until,
            collection_status=data.collection_status,
            evidence_id=data.evidence_id,
        )
        session.add(row)
        await session.flush([row])
        await self._audit.record(
            session,
            action="create",
            object_type="vendor_document",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after=AuditService.snapshot(row, fields=_DOCUMENT_SNAPSHOT),
        )
        await session.flush()
        names = await self._member_names(session, tenant_id)
        return self._document_view(row, names)

    @staticmethod
    def _document_view(row: VendorDocument, names: dict[uuid.UUID, str]) -> DocumentView:
        today = datetime.now(UTC).date()
        expires_in = (row.valid_until - today).days if row.valid_until else None
        reviewer = row.reviewed_by_membership_id
        return DocumentView(
            id=row.id,
            vendor_id=row.vendor_id,
            doc_type=row.doc_type,
            title=row.title,
            issue_date=row.issue_date,
            valid_until=row.valid_until,
            # Derived on read, never stored: a stored "expired" flag is wrong for
            # however long it is between the expiry and the next sweep.
            expires_in_days=expires_in,
            is_expired=bool(row.valid_until and row.valid_until < today),
            collection_status=row.collection_status,
            review_notes=row.review_notes,
            reviewed_by_name=names.get(reviewer) if reviewer else None,
            reviewed_at=row.reviewed_at,
            evidence_id=row.evidence_id,
        )

    async def review_soc_report(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        data: SocReviewInput,
    ) -> SocReviewView:
        """Turn a SOC report into queryable fields — the CC9.2 artefact (ER 110).

        This is the record that lets the platform answer a control it already ships
        and currently cannot. It is structured rather than a file plus a note
        because "which of our critical vendors have an unqualified SOC 2 Type II
        covering the audit period" has to be a query, not a reading exercise.
        """
        vendor = await self._load(session, tenant_id, vendor_id)
        self._check_vocabulary(data.report_kind, SOC_REPORT_KINDS, field_name="report_kind")
        self._check_vocabulary(data.report_type, SOC_REPORT_TYPES, field_name="report_type")
        self._check_vocabulary(data.opinion, SOC_OPINIONS, field_name="opinion")
        if (
            data.audit_period_start
            and data.audit_period_end
            and (data.audit_period_end < data.audit_period_start)
        ):
            raise InvalidInput(
                "The audit period ends before it starts. Check the dates.",
                detail="audit period reversed",
            )
        row = VendorSocReportReview(
            id=uuid7(),
            tenant_id=tenant_id,
            vendor_id=vendor.id,
            document_id=data.document_id,
            report_kind=data.report_kind,
            report_type=data.report_type,
            audit_period_start=data.audit_period_start,
            audit_period_end=data.audit_period_end,
            tsc_included=list(data.tsc_included),
            opinion=data.opinion,
            bridge_letter_received=data.bridge_letter_received,
            findings_material=data.findings_material,
            cuec_reviewed=data.cuec_reviewed,
            cuec_notes=data.cuec_notes,
            subservice_orgs=data.subservice_orgs,
            cpa_firm=data.cpa_firm,
            reviewed_by_membership_id=actor.id if isinstance(actor, Membership) else None,
            reviewed_at=datetime.now(UTC),
        )
        session.add(row)
        await session.flush([row])

        # A qualified or adverse opinion, or material findings, is a finding in its
        # own right. Recording the review and leaving the reader to notice is how a
        # bad report gets filed and forgotten.
        if data.opinion in {"qualified", "adverse", "disclaimer"} or data.findings_material:
            session.add(
                VendorFinding(
                    id=uuid7(),
                    tenant_id=tenant_id,
                    vendor_id=vendor.id,
                    title=f"SOC report: {data.opinion} opinion"
                    if data.opinion != "unqualified"
                    else "SOC report: material findings",
                    detail=_soc_finding_detail(data),
                    finding_source="document_review",
                    severity="high" if data.opinion == "unqualified" else "critical",
                    sla_due=datetime.now(UTC).date() + timedelta(days=30),
                )
            )
        await self._audit.record(
            session,
            action="create",
            object_type="vendor_soc_report_review",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after={
                "opinion": data.opinion,
                "findings_material": data.findings_material,
                "report": f"{data.report_kind} {data.report_type}",
            },
        )
        await session.flush()
        return self._soc_view(row)

    @staticmethod
    def _soc_view(row: VendorSocReportReview) -> SocReviewView:
        today = datetime.now(UTC).date()
        return SocReviewView(
            id=row.id,
            vendor_id=row.vendor_id,
            document_id=row.document_id,
            report_kind=row.report_kind,
            report_type=row.report_type,
            audit_period_start=row.audit_period_start,
            audit_period_end=row.audit_period_end,
            tsc_included=list(row.tsc_included or []),
            opinion=row.opinion,
            bridge_letter_received=row.bridge_letter_received,
            findings_material=row.findings_material,
            cuec_reviewed=row.cuec_reviewed,
            cuec_notes=row.cuec_notes,
            subservice_orgs=row.subservice_orgs,
            cpa_firm=row.cpa_firm,
            reviewed_at=row.reviewed_at,
            # A report whose period ended more than a year ago is stale whatever
            # its opinion said, and a bridge letter is what covers the gap.
            period_is_stale=bool(
                row.audit_period_end
                and (today - row.audit_period_end).days > _SOC_PERIOD_STALE_DAYS
            ),
            needs_bridge_letter=bool(
                row.audit_period_end
                and (today - row.audit_period_end).days > _SOC_BRIDGE_AFTER_DAYS
                and not row.bridge_letter_received
            ),
        )

    async def add_contract(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        data: ContractInput,
    ) -> ContractView:
        vendor = await self._load(session, tenant_id, vendor_id)
        self._check_vocabulary(data.contract_type, CONTRACT_TYPES, field_name="contract_type")
        self._check_vocabulary(data.status, CONTRACT_STATUSES, field_name="status")
        if data.start_date and data.end_date and data.end_date < data.start_date:
            raise InvalidInput(
                "The contract ends before it starts. Check the dates.",
                detail="contract term reversed",
            )
        row = VendorContract(
            id=uuid7(),
            tenant_id=tenant_id,
            vendor_id=vendor.id,
            engagement_id=data.engagement_id,
            contract_type=data.contract_type,
            title=self._require_name(data.title, what="contract"),
            start_date=data.start_date,
            end_date=data.end_date,
            renewal_date=data.renewal_date,
            auto_renew=data.auto_renew,
            notice_period_days=data.notice_period_days,
            breach_notification_hours=data.breach_notification_hours,
            right_to_audit=data.right_to_audit,
            subprocessor_terms=data.subprocessor_terms,
            exit_data_return_clause=data.exit_data_return_clause,
            value=data.value,
            status=data.status,
        )
        session.add(row)
        await session.flush([row])
        await self._recache_contract_value(session, tenant_id, vendor)
        await self._audit.record(
            session,
            action="create",
            object_type="vendor_contract",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after=AuditService.snapshot(row, fields=_CONTRACT_SNAPSHOT),
        )
        await session.flush()
        return self._contract_view(row)

    async def _recache_contract_value(
        self, session: AsyncSession, tenant_id: uuid.UUID, vendor: Vendor
    ) -> None:
        """Sum the active contracts onto the vendor's cached annual value (V10)."""
        total = (
            await session.execute(
                select(func.sum(VendorContract.value))
                .where(VendorContract.tenant_id == tenant_id)
                .where(VendorContract.vendor_id == vendor.id)
                .where(VendorContract.status == "active")
            )
        ).scalar_one_or_none()
        vendor.annual_contract_value = float(total) if total is not None else None

    @staticmethod
    def _contract_view(row: VendorContract) -> ContractView:
        today = datetime.now(UTC).date()
        renews_in = (row.renewal_date - today).days if row.renewal_date else None
        return ContractView(
            id=row.id,
            vendor_id=row.vendor_id,
            engagement_id=row.engagement_id,
            contract_type=row.contract_type,
            title=row.title,
            start_date=row.start_date,
            end_date=row.end_date,
            renewal_date=row.renewal_date,
            renews_in_days=renews_in,
            auto_renew=row.auto_renew,
            notice_period_days=row.notice_period_days,
            breach_notification_hours=row.breach_notification_hours,
            right_to_audit=row.right_to_audit,
            subprocessor_terms=row.subprocessor_terms,
            exit_data_return_clause=row.exit_data_return_clause,
            value=row.value,
            status=row.status,
            # The clause flags an auditor asks about, counted so a register can
            # sort on "which contracts are missing protections".
            clauses_present=sum(
                (row.right_to_audit, row.subprocessor_terms, row.exit_data_return_clause)
            ),
            # auto_renew plus a notice period is the trap: miss the window and the
            # contract renews itself for another term.
            notice_deadline=(
                row.renewal_date - timedelta(days=row.notice_period_days)
                if row.renewal_date and row.notice_period_days and row.auto_renew
                else None
            ),
        )

    async def add_subprocessor(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        data: SubprocessorInput,
    ) -> list[SubprocessorView]:
        vendor = await self._load(session, tenant_id, vendor_id)
        self._check_vocabulary(data.provenance, SUBPROCESSOR_PROVENANCE, field_name="provenance")
        if data.linked_vendor_id == vendor.id:
            raise InvalidInput(
                "A vendor cannot be its own subprocessor.",
                detail="self-referential subprocessor",
            )
        session.add(
            VendorSubprocessor(
                id=uuid7(),
                tenant_id=tenant_id,
                vendor_id=vendor.id,
                name=self._require_name(data.name, what="subprocessor"),
                service=data.service.strip(),
                data_location=self._clean(data.data_location),
                provenance=data.provenance,
                linked_vendor_id=data.linked_vendor_id,
                notification_obligation=self._clean(data.notification_obligation),
            )
        )
        await self._audit.record(
            session,
            action="create",
            object_type="vendor_subprocessor",
            object_id=vendor.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after={"name": data.name, "provenance": data.provenance},
        )
        await session.flush()
        return await self.subprocessors(session, tenant_id=tenant_id, vendor_id=vendor.id)

    async def subprocessors(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, vendor_id: uuid.UUID
    ) -> list[SubprocessorView]:
        rows = list(
            (
                await session.execute(
                    select(VendorSubprocessor)
                    .where(VendorSubprocessor.tenant_id == tenant_id)
                    .where(VendorSubprocessor.vendor_id == vendor_id)
                    .order_by(VendorSubprocessor.name)
                )
            ).scalars()
        )
        # How many *other* vendors also declare this fourth party. The concentration
        # question — "how much of our estate depends on this one supplier" — is only
        # answerable because the subprocessor rows point at a vendor row.
        shared: dict[uuid.UUID, int] = {}
        linked = [r.linked_vendor_id for r in rows if r.linked_vendor_id]
        if linked:
            counts = await session.execute(
                select(
                    VendorSubprocessor.linked_vendor_id,
                    func.count(func.distinct(VendorSubprocessor.vendor_id)),
                )
                .where(VendorSubprocessor.tenant_id == tenant_id)
                .where(VendorSubprocessor.linked_vendor_id.in_(linked))
                .group_by(VendorSubprocessor.linked_vendor_id)
            )
            shared = {row[0]: row[1] for row in counts.all()}
        return [
            SubprocessorView(
                id=r.id,
                vendor_id=r.vendor_id,
                name=r.name,
                service=r.service,
                data_location=r.data_location,
                provenance=r.provenance,
                linked_vendor_id=r.linked_vendor_id,
                notification_obligation=r.notification_obligation,
                status=r.status,
                also_used_by_vendors=max(shared.get(r.linked_vendor_id, 1) - 1, 0)
                if r.linked_vendor_id
                else 0,
            )
            for r in rows
        ]

    # -- intake: the front door ------------------------------------------------

    async def request_vendor(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        data: IntakeInput,
    ) -> IntakeView:
        """Ask for a vendor. This is not yet a vendor row, and that is the point.

        A register that fills with everything anyone ever proposed stops being a
        list of who has our data.
        """
        row = VendorIntakeRequest(
            id=uuid7(),
            tenant_id=tenant_id,
            requested_by_membership_id=actor.id if isinstance(actor, Membership) else None,
            vendor_name=self._require_name(data.vendor_name, what="vendor"),
            department=self._clean(data.department),
            proposed_service=data.proposed_service.strip(),
            data_types_shared=list(data.data_types_shared),
            urgency=data.urgency,
        )
        self._check_vocabulary(data.urgency, URGENCIES, field_name="urgency")
        # Screening is a name match against the register, not a judgement: if we
        # already deal with them, the requester should know before anyone reviews.
        duplicates = await self.find_duplicates(session, tenant_id=tenant_id, name=row.vendor_name)
        row.screening_status = "flagged" if duplicates else "passed"
        session.add(row)
        await session.flush([row])
        await self._audit.record(
            session,
            action="create",
            object_type="vendor_intake_request",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after={"vendor_name": row.vendor_name, "screening_status": row.screening_status},
        )
        await session.flush()
        return self._intake_view(row, await self._member_names(session, tenant_id), duplicates)

    async def decide_intake(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        request_id: uuid.UUID,
        approve: bool,
        reason: str | None = None,
    ) -> IntakeView:
        """Accept or decline. Accepting creates the vendor and its first engagement
        in the same transaction; declining creates nothing and keeps the reason."""
        row = await session.get(VendorIntakeRequest, request_id, populate_existing=True)
        if row is None or row.tenant_id != tenant_id:
            raise NotFound(_INTAKE_GONE, detail=f"vendor intake request {request_id}")
        if row.decision != "pending":
            raise Conflict(
                "This request has already been decided.",
                detail=f"intake {request_id} is {row.decision}",
            )
        if not approve and not (reason or "").strip():
            raise InvalidInput(
                "Say why the request is being declined. The same tool will be asked "
                "for again next quarter, and the reason is what makes it recognisable.",
                detail="intake rejection with no reason",
            )

        now = datetime.now(UTC)
        row.decided_by_membership_id = actor.id if isinstance(actor, Membership) else None
        row.decided_at = now
        row.decision_reason = (reason or "").strip() or None
        if approve:
            created = await self.create_vendor(
                session,
                tenant_id=tenant_id,
                actor=actor,
                data=VendorInput(
                    name=row.vendor_name,
                    business_unit=row.department,
                    services_provided=row.proposed_service,
                    data_types_in_scope=tuple(row.data_types_shared or []),
                ),
            )
            row.decision = "approved"
            row.created_vendor_id = created.id
        else:
            row.decision = "rejected"
        await self._audit.record(
            session,
            action="approve" if approve else "update",
            object_type="vendor_intake_request",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"decision": "pending"},
            after={
                "decision": row.decision,
                "created_vendor_id": str(row.created_vendor_id) if row.created_vendor_id else None,
                "reason": row.decision_reason,
            },
        )
        await session.flush()
        return self._intake_view(row, await self._member_names(session, tenant_id), [])

    @staticmethod
    def _intake_view(
        row: VendorIntakeRequest,
        names: dict[uuid.UUID, str],
        duplicates: Sequence[DuplicateMatch],
    ) -> IntakeView:
        requester = row.requested_by_membership_id
        decider = row.decided_by_membership_id
        return IntakeView(
            id=row.id,
            vendor_name=row.vendor_name,
            department=row.department,
            proposed_service=row.proposed_service,
            data_types_shared=list(row.data_types_shared or []),
            urgency=row.urgency,
            screening_status=row.screening_status,
            decision=row.decision,
            decision_reason=row.decision_reason,
            requested_by_name=names.get(requester) if requester else None,
            decided_by_name=names.get(decider) if decider else None,
            decided_at=row.decided_at,
            created_vendor_id=row.created_vendor_id,
            duplicates=list(duplicates),
            created_at=row.created_at,
        )

    async def list_intake(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, decision: str | None = None
    ) -> list[IntakeView]:
        """The intake queue. Pending first, because that is the work."""
        stmt = select(VendorIntakeRequest).where(VendorIntakeRequest.tenant_id == tenant_id)
        if decision:
            stmt = stmt.where(VendorIntakeRequest.decision == decision)
        rows = list((await session.execute(stmt)).scalars())
        names = await self._member_names(session, tenant_id)
        # Resolve the matches for flagged rows only. The flag without the names
        # behind it is the queue telling a reviewer "something is wrong here"
        # and refusing to say what, which is the one thing they need to decide.
        # One lookup per flagged row, and only the flagged ones — a screened-clean
        # request has nothing to show and should not pay for the query.
        matches: dict[uuid.UUID, list[DuplicateMatch]] = {}
        for row in rows:
            if row.screening_status == "flagged":
                matches[row.id] = await self.find_duplicates(
                    session, tenant_id=tenant_id, name=row.vendor_name
                )
        views = [self._intake_view(r, names, matches.get(r.id, [])) for r in rows]
        views.sort(key=lambda v: (v.decision != "pending", v.created_at), reverse=False)
        return views

    # -- the exit --------------------------------------------------------------

    async def offboard(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        engagement_id: uuid.UUID | None,
        reason: str,
    ) -> VendorDetailView:
        """Start the evidenced exit (ER 127). Archive, never delete.

        Offboarding one engagement is not terminating the vendor, which is why the
        engagement is optional and its absence means the whole relationship.
        """
        vendor = await self._load(session, tenant_id, vendor_id)
        if not reason.strip():
            raise InvalidInput(
                "Say why the relationship is ending. It is the first thing anyone "
                "reviewing the exit will ask.",
                detail="offboarding with no reason",
            )
        row = VendorOffboarding(
            id=uuid7(),
            tenant_id=tenant_id,
            vendor_id=vendor.id,
            engagement_id=engagement_id,
            reason=reason.strip(),
        )
        session.add(row)
        if engagement_id is not None:
            engagement = await self._load_engagement(session, tenant_id, engagement_id)
            engagement.status = "offboarding"
        else:
            vendor.lifecycle_status = "offboarding"
        await self._audit.record(
            session,
            action="transition",
            object_type="vendor_offboarding",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"lifecycle_status": vendor.lifecycle_status},
            after={"reason": reason.strip(), "engagement_id": str(engagement_id or "")},
        )
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=vendor.id)

    async def complete_offboarding(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        offboarding_id: uuid.UUID,
        data: OffboardingCompletion,
    ) -> VendorDetailView:
        """Close the exit, once every step is evidenced.

        Refuses while a step is outstanding. An offboarding marked complete with
        access still live is exactly the record an auditor uses to show the process
        is theatre.
        """
        row = await session.get(VendorOffboarding, offboarding_id, populate_existing=True)
        if row is None or row.tenant_id != tenant_id or row.vendor_id != vendor_id:
            raise NotFound(
                _OFFBOARDING_GONE, detail=f"vendor offboarding {offboarding_id} on {vendor_id}"
            )
        now = datetime.now(UTC)
        if data.access_revoked:
            row.access_revoked_at = row.access_revoked_at or now
            row.revoked_by_membership_id = actor.id if isinstance(actor, Membership) else None
        if data.data_returned:
            row.data_return_attested_at = row.data_return_attested_at or now
        row.contract_provisions_reviewed = (
            row.contract_provisions_reviewed or data.contract_provisions_reviewed
        )
        row.final_payments_settled = row.final_payments_settled or data.final_payments_settled
        row.certificate_evidence_id = data.certificate_evidence_id or row.certificate_evidence_id
        row.notes = self._clean(data.notes) or row.notes

        outstanding = [
            label
            for label, done in (
                ("access revoked", row.access_revoked_at is not None),
                ("data return attested", row.data_return_attested_at is not None),
                ("contract provisions reviewed", row.contract_provisions_reviewed),
                ("final payments settled", row.final_payments_settled),
            )
            if not done
        ]
        if data.complete and outstanding:
            raise Conflict(
                "The exit is not finished: " + ", ".join(outstanding) + ".",
                detail=f"offboarding {offboarding_id} outstanding: {outstanding}",
            )
        vendor = await self._load(session, tenant_id, row.vendor_id)
        if data.complete:
            row.completed_at = now
            # Archived, never deleted (rule 6). An auditor's first question about a
            # missing vendor is who removed it and why.
            if row.engagement_id is None:
                vendor.lifecycle_status = "archived"
            else:
                engagement = await self._load_engagement(session, tenant_id, row.engagement_id)
                engagement.status = "archived"
        await self._audit.record(
            session,
            action="transition",
            object_type="vendor_offboarding",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after={
                "completed": row.completed_at is not None,
                "outstanding": outstanding,
            },
        )
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=vendor.id)

    # -- reassessment ----------------------------------------------------------

    async def open_reassessment(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        engagement_id: uuid.UUID,
    ) -> VendorDetailView:
        """Start the next cycle, carrying the tier forward.

        The new cycle's stages are laid out from the *current* tier, so a vendor
        that has since been retiered is reviewed at the depth it now warrants
        rather than the depth it warranted last year.

        ``next_reassessment_on`` is **not** recomputed from today. It moves on the
        cadence from where it already was, so a review completed late does not push
        the next one late — reviews drifting a little further out every cycle is
        the failure this rule exists to prevent (ER 101).
        """
        engagement = await self._load_engagement(session, tenant_id, engagement_id)
        if engagement.vendor_id != vendor_id:
            raise NotFound(
                _ENGAGEMENT_GONE, detail=f"engagement {engagement_id} not on {vendor_id}"
            )
        vendor = await self._load(session, tenant_id, vendor_id)
        policy = await self._resolved_policy(session, tenant_id)
        cycle = await self._current_cycle(session, tenant_id, engagement.id) + 1
        await self.materialise_cycle(session, tenant_id, engagement, cycle, policy)
        self._schedule_reassessment(vendor, engagement.tier, policy)
        await self._audit.record(
            session,
            action="transition",
            object_type="vendor_engagement",
            object_id=engagement.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"cycle": cycle - 1},
            after={"cycle": cycle, "next_reassessment_on": str(vendor.next_reassessment_on)},
        )
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=vendor_id)

    async def due_for_reassessment(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, on: date | None = None
    ) -> list[uuid.UUID]:
        """Vendors whose next review has come round. What the scheduled job reads."""
        cutoff = on or datetime.now(UTC).date()
        return list(
            (
                await session.execute(
                    select(Vendor.id)
                    .where(Vendor.tenant_id == tenant_id)
                    .where(Vendor.next_reassessment_on.is_not(None))
                    .where(Vendor.next_reassessment_on <= cutoff)
                    .where(Vendor.lifecycle_status.not_in(["archived", "terminated"]))
                )
            ).scalars()
        )

    async def expiring_documents(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, within_days: int = 30
    ) -> list[DocumentView]:
        """Documents already expired or about to be. What the expiry sweep reads."""
        horizon = datetime.now(UTC).date() + timedelta(days=within_days)
        rows = list(
            (
                await session.execute(
                    select(VendorDocument)
                    .where(VendorDocument.tenant_id == tenant_id)
                    .where(VendorDocument.valid_until.is_not(None))
                    .where(VendorDocument.valid_until <= horizon)
                    .order_by(VendorDocument.valid_until)
                )
            ).scalars()
        )
        names = await self._member_names(session, tenant_id)
        return [self._document_view(r, names) for r in rows]

    async def raise_sla_findings(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> int:
        """One finding per breached service level, idempotent per SLA.

        A breached SLA is a fact the vendor has already caused, so the sweep is
        allowed to write it — unlike the reassessment and expiry sweeps, which only
        tell somebody. The idempotency is what makes a nightly job safe: an open
        finding for the same service level suppresses a second.

        The actor is ``System``: nobody asked for this, the clock did.
        """
        breached = list(
            (
                await session.execute(
                    select(VendorSla)
                    .where(VendorSla.tenant_id == tenant_id)
                    .where(VendorSla.status == "breached")
                )
            ).scalars()
        )
        raised = 0
        for sla in breached:
            title = f"SLA breached: {sla.name}"
            already = (
                await session.execute(
                    select(VendorFinding.id)
                    .where(VendorFinding.tenant_id == tenant_id)
                    .where(VendorFinding.vendor_id == sla.vendor_id)
                    .where(VendorFinding.finding_source == "sla_breach")
                    .where(VendorFinding.title == title)
                    .where(VendorFinding.status.in_(list(OPEN_FINDING_STATUSES)))
                )
            ).scalar_one_or_none()
            if already is not None:
                continue
            finding = VendorFinding(
                id=uuid7(),
                tenant_id=tenant_id,
                vendor_id=sla.vendor_id,
                title=title,
                detail=f"Committed {sla.target}; measured {sla.measurement or 'not recorded'}.",
                finding_source="sla_breach",
                severity="high",
                sla_due=datetime.now(UTC).date() + timedelta(days=_FINDING_SLA_DAYS["high"]),
            )
            session.add(finding)
            await session.flush([finding])
            await self._audit.record(
                session,
                action="create",
                object_type="vendor_finding",
                object_id=finding.id,
                actor=System(),
                tenant_id=tenant_id,
                before=None,
                after=AuditService.snapshot(finding, fields=_FINDING_SNAPSHOT),
            )
            raised += 1
        await session.flush()
        return raised

    async def breaching_slas(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[uuid.UUID]:
        """SLA rows whose measurement is at risk or breached. The sweep's input."""
        return list(
            (
                await session.execute(
                    select(VendorSla.id)
                    .where(VendorSla.tenant_id == tenant_id)
                    .where(VendorSla.status.in_(["at_risk", "breached"]))
                )
            ).scalars()
        )


vendor_service = VendorService()
