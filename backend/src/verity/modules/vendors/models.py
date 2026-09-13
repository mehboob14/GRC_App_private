"""Third-party vendor risk — the register (Week 5 / Deliverable 1.2).

The first slice of ``openspec/changes/week5-vendor-risk``: the three tables the
whole module hangs off. Column lists are transcribed verbatim from the ER's
section-3.7 diagrams into that change's ``design.md`` §1, which is the single
build reference this file was written from.

**The engagement is the unit of risk (V10).** A vendor is the organisation; an
engagement is one *use* of it by one part of the business. Tiering, assessments,
contracts and the twelve-stage lifecycle all hang off an engagement, because the
same vendor serving marketing and payroll is two different risks and averaging
them destroys the information tiering exists to produce (ER ¶89, ADR-0009).
Every vendor gets one implicit default engagement at creation, so no query
anywhere special-cases an absent one and the simple case stays simple.

``tier``, ``current_residual_score``, ``current_grade`` and
``annual_contract_value`` on ``Vendor`` are **cached read-model columns** holding
the worst engagement's values, so a portfolio of hundreds ranks without a join.
They are derived, never authoritative, and nothing acts on them. The engagement
row is what anyone acts on.

``Integratable`` rides the register now because ``docs/conventions/database.md``
names this table: a Phase-2 procurement or SSO connector is then an upsert rather
than a migration (rule 9).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Final

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.elements import conv

from verity.db.base import (
    Base,
    Integratable,
    TenantScoped,
    Timestamped,
    UUIDPrimaryKey,
    integration_unique,
    status_check,
    tenant_index,
)
from verity.modules.vendors.lifecycle import STAGE_STATUSES, STAGES, TRANSITION_ACTIONS

VENDOR_TYPES: Final[tuple[str, ...]] = ("vendor", "supplier", "contractor", "partner")

# One vocabulary, two subjects. A vendor's standing as an organisation and an
# engagement's standing as one use of it move through the same states, so the
# check constraint and the client's status filter are the same list. Independent
# values though: a vendor stays ``active`` while one engagement is ``terminated``.
LIFECYCLE_STATUSES: Final[tuple[str, ...]] = (
    "requested",
    "under_review",
    "approved",
    "active",
    "flagged",
    "on_hold",
    "offboarding",
    "terminated",
    "archived",
)

TIERS: Final[tuple[str, ...]] = ("critical", "high", "medium", "low")

# Third copy in this codebase (assets.DATA_CLASSIFICATIONS,
# documents.CLASSIFICATIONS). It stays a copy rather than an import because the
# import-linter contract forbids reaching another module's models.
DATA_CLASSIFICATIONS: Final[tuple[str, ...]] = (
    "public",
    "internal",
    "confidential",
    "restricted",
)

CONTACT_TYPES: Final[tuple[str, ...]] = ("security", "privacy", "commercial", "portal")

# -- the questionnaire bank (V5, V8, V13) -------------------------------------

# V8's ten risk domains. Named in neither signed document; the ER annotates
# ``questions.domain`` as "of ten risk domains" and lists none of them.
RISK_DOMAINS: Final[tuple[str, ...]] = (
    "information_security",
    "access_control",
    "data_protection_privacy",
    "business_continuity",
    "incident_response",
    "secure_development",
    "infrastructure_cloud",
    "personnel_security",
    "compliance_legal",
    "fourth_party_management",
)

RISK_DOMAIN_LABELS: Final[dict[str, str]] = {
    "information_security": "Information security programme",
    "access_control": "Access control",
    "data_protection_privacy": "Data protection and privacy",
    "business_continuity": "Business continuity and resilience",
    "incident_response": "Incident response",
    "secure_development": "Secure development",
    "infrastructure_cloud": "Infrastructure and cloud",
    "personnel_security": "Personnel security",
    "compliance_legal": "Compliance and legal",
    "fourth_party_management": "Fourth-party management",
}

# How deep a questionnaire goes. This is what spec 82's "right-sizes assessment
# depth" actually means: a low-tier vendor answers the lite set and stops.
SCOPE_LEVELS: Final[tuple[str, ...]] = ("lite", "core", "detail")

# -- questionnaires a tenant builds -------------------------------------------

QUESTIONNAIRE_PURPOSES: Final[tuple[str, ...]] = ("tiering", "due_diligence")
"""Two questionnaires with two audiences, and they are easy to confuse.

``tiering`` is internal. Our own business owner answers it about how we use the
vendor (what data, what access, how critical), and the answers set the tier.
``due_diligence`` goes to the vendor through the portal. They answer it about their
own controls, with evidence, and the answers set the residual score and findings."""

QUESTIONNAIRE_STATUSES: Final[tuple[str, ...]] = ("active", "archived")

QUESTION_TYPES: Final[tuple[str, ...]] = (
    "single_choice",
    "multi_choice",
    "text",
    "paragraph",
    "number",
    "date",
    "file",
)
"""What a tenant-built question can ask for. Only the two choice types score;
the rest are recorded and shown to the reviewer, never turned into points."""

CHOICE_TYPES: Final[frozenset[str]] = frozenset(("single_choice", "multi_choice"))

EVIDENCE_RULES: Final[tuple[str, ...]] = ("none", "optional", "required")

# The shipped bank's own types, kept for the rows already written against them,
# plus the builder's so a library can ship questions in either shape.
ANSWER_TYPES: Final[tuple[str, ...]] = (
    "yes_no_na",
    "select",
    "multi_select",
    "text",
    "numeric",
    "single_choice",
    "multi_choice",
    "paragraph",
    "number",
    "date",
    "file",
)

# Which scope levels each tier is asked. This is spec 82's "right-sizes assessment
# depth" as data: a low-tier vendor answers 15 questions and a critical one 59.
BUNDLE_BY_TIER: Final[dict[str, tuple[str, ...]]] = {
    "critical": ("lite", "core", "detail"),
    "high": ("lite", "core", "detail"),
    "medium": ("lite", "core"),
    "low": ("lite",),
}

# -- the review ---------------------------------------------------------------

ASSESSMENT_KINDS: Final[tuple[str, ...]] = ("initial", "reassessment")
REVIEW_FORMATS: Final[tuple[str, ...]] = (
    "questionnaire",
    "soc_report_review",
    "external_report",
)
ASSESSMENT_DOMAINS: Final[tuple[str, ...]] = ("security", "privacy", "legal", "esg")
ASSESSMENT_STATUSES: Final[tuple[str, ...]] = (
    "pending",
    "in_progress",
    "submitted",
    "expired",
    "scored",
)
ASSESSMENT_DECISIONS: Final[tuple[str, ...]] = (
    "pending",
    "approved",
    "approved_with_conditions",
    "rejected",
)
# yes/partial/no/na, and the CHECK admits NULL so an unanswered row is legal.
ANSWER_VALUES: Final[tuple[str, ...]] = ("yes", "partial", "no", "na")
GRADES: Final[tuple[str, ...]] = ("A", "B", "C", "D", "F")

FINDING_SOURCES: Final[tuple[str, ...]] = (
    "assessment",
    "sla_breach",
    "signal",
    "document_review",
    "offboarding",
)
FINDING_SEVERITIES: Final[tuple[str, ...]] = ("critical", "high", "medium", "low")
FINDING_STATUSES: Final[tuple[str, ...]] = ("open", "in_remediation", "accepted", "closed")
FINDING_TREATMENTS: Final[tuple[str, ...]] = ("remediate", "mitigate", "transfer", "accept")
OPEN_FINDING_STATUSES: Final[frozenset[str]] = frozenset(("open", "in_remediation"))

# -- the decision, the paperwork and the exit (section 4) ---------------------

ROSTER_ROLES: Final[tuple[str, ...]] = (
    "tprm_lead",
    "analyst",
    "security",
    "privacy",
    "legal",
    "procurement",
    "exec_approver",
    "it",
)
"""Who plays which part, tenant-wide. Roles as rows, not the reference product's
JSON blob — and this is half of spec 82's "required reviewers", the other half
being which roles a tier demands."""

URGENCIES: Final[tuple[str, ...]] = ("low", "normal", "high")
INTAKE_SCREENING: Final[tuple[str, ...]] = ("pending", "passed", "flagged")
INTAKE_DECISIONS: Final[tuple[str, ...]] = ("pending", "approved", "auto_approved", "rejected")
"""``auto_approved`` is distinct from ``approved`` on purpose: it is what
``auto_approve_low_tier`` produces, and an auditor has to be able to tell a
machine decision from a human one."""

# V3. This table is authoritative and the ER's assessment-level decision column is
# dropped: two tables holding overlapping decision state is a data-integrity trap.
# Verbs, not participles, and four-valued — `defer` is not `reject`, and a product
# offering only the two extremes gets `reject` used to mean "not yet", which then
# reads as a refused vendor forever.
APPROVAL_DECISIONS: Final[tuple[str, ...]] = (
    "approve",
    "approve_with_conditions",
    "defer",
    "reject",
)
CONDITION_STATUSES: Final[tuple[str, ...]] = ("open", "met", "overdue", "waived")

DOC_TYPES: Final[tuple[str, ...]] = (
    "soc_report",
    "iso_cert",
    "bridge_letter",
    "dpa",
    "pentest",
    "insurance",
    "financials",
    "bcdr",
    "policy",
)
DOC_COLLECTION_STATUSES: Final[tuple[str, ...]] = ("requested", "received", "reviewed")

SOC_REPORT_KINDS: Final[tuple[str, ...]] = ("soc1", "soc2", "soc3")
SOC_REPORT_TYPES: Final[tuple[str, ...]] = ("type_i", "type_ii")
SOC_OPINIONS: Final[tuple[str, ...]] = ("unqualified", "qualified", "adverse", "disclaimer")

CONTRACT_TYPES: Final[tuple[str, ...]] = ("master", "dpa", "sla", "security_addendum", "nda")
CONTRACT_STATUSES: Final[tuple[str, ...]] = ("draft", "active", "expired", "terminated")
SLA_STATUSES: Final[tuple[str, ...]] = ("on_track", "at_risk", "breached")

SUBPROCESSOR_PROVENANCE: Final[tuple[str, ...]] = (
    "vendor_declared",
    "auto_detected",
    "intelligence",
)
SUBPROCESSOR_STATUSES: Final[tuple[str, ...]] = ("active", "removed")

SCORECARD_PROVIDERS: Final[tuple[str, ...]] = (
    "securityscorecard",
    "bitsight",
    "upguard",
    "manual",
)
SIGNAL_TYPES: Final[tuple[str, ...]] = (
    "rating_change",
    "breach",
    "adverse_media",
    "financial",
    "sla_breach",
    "cert_expiry",
)
SIGNAL_SOURCE_CLASSES: Final[tuple[str, ...]] = (
    "rating_platform",
    "breach_intel",
    "media",
    "financial_provider",
    "internal",
)
SIGNAL_STATUSES: Final[tuple[str, ...]] = ("new", "acknowledged", "dismissed")
ALERT_ACTIONS: Final[tuple[str, ...]] = ("notify", "create_task", "trigger_reassessment")
ALERT_CHANNELS: Final[tuple[str, ...]] = ("in_app", "email", "slack")
"""``slack`` is accepted and inert: the connector is Phase 2. Storing a channel the
platform cannot deliver to is deliberate — the alternative is a customer
configuring Slack, seeing it accepted, and never learning it does nothing."""

DISCOVERED_DISPOSITIONS: Final[tuple[str, ...]] = (
    "pending",
    "added_as_vendor",
    "linked_to_vendor",
    "ignored",
)

COMMENT_AUTHOR_TYPES: Final[tuple[str, ...]] = ("internal_user", "vendor_contact")
COMMENT_VISIBILITY: Final[tuple[str, ...]] = ("internal_only", "vendor_shared")
"""``visibility`` is load-bearing. An ``internal_only`` comment reaching the portal
is a disclosure incident, so the portal query filters on it and a test covers it."""

DEFAULT_ENGAGEMENT_NAME: Final = "General use"

_MEMBERSHIP_FK = "tenant_memberships.id"
_VENDOR_FK = "vendors.id"
_ENGAGEMENT_FK = "vendor_engagements.id"


class Vendor(UUIDPrimaryKey, TenantScoped, Timestamped, Integratable, Base):
    """The organisation. One row per third party the tenant deals with."""

    __tablename__ = "vendors"

    # identity
    name: Mapped[str]
    vendor_type: Mapped[str] = mapped_column(default="vendor")
    industry: Mapped[str | None] = mapped_column(default=None)
    website: Mapped[str | None] = mapped_column(default=None)
    business_unit: Mapped[str | None] = mapped_column(default=None)
    services_provided: Mapped[str] = mapped_column(default="", server_default=text("''"))

    # data scope — what we hand over, and where it lands
    stores_pii: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    data_location: Mapped[str | None] = mapped_column(default=None)
    data_types_in_scope: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    data_classification: Mapped[str | None] = mapped_column(default=None)

    lifecycle_status: Mapped[str] = mapped_column(default="requested", server_default="requested")

    # -- cached from the worst engagement (V10). Derived, never authoritative. --
    # NULL means "not scored yet", never a laundered middle value. The tiering
    # engine writes tier; scoring writes the other two. Until those land nothing
    # in the codebase sets them, which is why they are nullable with no default.
    tier: Mapped[str | None] = mapped_column(default=None)
    current_residual_score: Mapped[float | None] = mapped_column(Float, default=None)
    # No CHECK: the grade vocabulary is settled by the scoring engine that
    # produces it, and guessing it here would constrain a column nothing writes.
    current_grade: Mapped[str | None] = mapped_column(default=None)
    annual_contract_value: Mapped[float | None] = mapped_column(Float, default=None)

    # ownership — memberships, never users (rule 3)
    business_owner_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    security_owner_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    relationship_owner_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )

    # Computed from the tier's cadence, never from the last completion date, so
    # reviews cannot drift a little further out every cycle (ER ¶101).
    next_reassessment_on: Mapped[date | None] = mapped_column(default=None)
    tags: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )

    __table_args__ = (
        status_check("vendors", "vendor_type", VENDOR_TYPES),
        status_check("vendors", "lifecycle_status", LIFECYCLE_STATUSES),
        # Nullable columns: NULL passes an IN(...) check, so "not set" stays legal.
        status_check("vendors", "data_classification", DATA_CLASSIFICATIONS),
        status_check("vendors", "tier", TIERS),
        # Deliberately no unique constraint on name or website (ER ¶90). Two real
        # subsidiaries share a trading name, so duplicate detection warns on save
        # and offers the match rather than refusing a legitimate record.
        integration_unique("vendors"),
        tenant_index("vendors", "lifecycle_status"),
        tenant_index("vendors", "tier"),
        tenant_index("vendors", "business_owner_membership_id"),
        tenant_index("vendors", "next_reassessment_on"),
    )

    def __repr__(self) -> str:
        return f"Vendor(id={self.id!r}, tenant_id={self.tenant_id!r}, name={self.name!r})"


class VendorEngagement(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One use of a vendor by one part of the business — the unit of risk (V10)."""

    __tablename__ = "vendor_engagements"

    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_VENDOR_FK, ondelete="CASCADE"))
    name: Mapped[str]
    service_description: Mapped[str] = mapped_column(default="", server_default=text("''"))
    business_unit: Mapped[str | None] = mapped_column(default=None)
    internal_owner_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    # The engagement-level tier is the real one; the vendor caches the worst.
    tier: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="requested", server_default="requested")
    start_date: Mapped[date | None] = mapped_column(default=None)
    end_date: Mapped[date | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("vendor_engagements", "status", LIFECYCLE_STATUSES),
        status_check("vendor_engagements", "tier", TIERS),
        CheckConstraint(
            "(start_date IS NULL) OR (end_date IS NULL) OR (end_date >= start_date)",
            name=conv("ck_vendor_engagements__dates_ordered"),
        ),
        tenant_index("vendor_engagements", "vendor_id"),
        tenant_index("vendor_engagements", "status"),
        tenant_index("vendor_engagements", "tier"),
    )

    def __repr__(self) -> str:
        return f"VendorEngagement(id={self.id!r}, vendor_id={self.vendor_id!r}, name={self.name!r})"


class VendorContact(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A person at the vendor. The questionnaire portal addressee lives here."""

    __tablename__ = "vendor_contacts"

    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_VENDOR_FK, ondelete="CASCADE"))
    name: Mapped[str]
    email: Mapped[str | None] = mapped_column(default=None)
    phone: Mapped[str | None] = mapped_column(default=None)
    contact_type: Mapped[str] = mapped_column(default="commercial")

    __table_args__ = (
        status_check("vendor_contacts", "contact_type", CONTACT_TYPES),
        # A portal contact is written to, so it must be reachable. Every other
        # kind is a directory entry and an email is optional.
        CheckConstraint(
            "(contact_type <> 'portal') OR (email IS NOT NULL)",
            name=conv("ck_vendor_contacts__portal_has_email"),
        ),
        tenant_index("vendor_contacts", "vendor_id"),
        tenant_index("vendor_contacts", "contact_type"),
    )

    def __repr__(self) -> str:
        return f"VendorContact(id={self.id!r}, vendor_id={self.vendor_id!r}, name={self.name!r})"


class VendorTieringPolicy(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """Per-tenant tiering configuration. One row, and only if it was customised.

    No row is seeded. ``scoring.DEFAULT_*`` and ``lifecycle.DEFAULT_*`` are the
    defaults and this table is the override, so a new tenant needs no provisioning
    step and no migration has to insert a tenant-owned row it cannot see through
    that row's own RLS policy. What stops a later change to those defaults from
    rewriting history is ``VendorTieringAssessment.policy_snapshot``, not this row.
    """

    __tablename__ = "vendor_tiering_policies"

    factor_weights: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    tier_thresholds: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    cadence_days_by_tier: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    questionnaire_bundle_by_tier: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    finding_sla_days_by_severity: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    auto_approve_low_tier: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    # The two the ER leaves implicit. Spec 82 promises the tier right-sizes
    # assessment depth, required reviewers and cadence; the ER draws the depth and
    # the cadence and gives the other two nowhere to live.
    stage_skip_matrix_by_tier: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    required_reviewer_roles_by_tier: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )

    __table_args__ = (UniqueConstraint("tenant_id", name="uq_vendor_tiering_policies__tenant_id"),)


class VendorTieringAssessment(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One scored tiering run. Immutable history: a retier writes a new row."""

    __tablename__ = "vendor_tiering_assessments"

    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_VENDOR_FK, ondelete="CASCADE"))
    engagement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_ENGAGEMENT_FK, ondelete="CASCADE"))
    cycle: Mapped[int] = mapped_column(default=1, server_default=text("1"))

    # The five fixed factors (V6). Filled on runs made before tiering became a
    # questionnaire, and on API calls that still post the five numbers; empty on
    # a questionnaire run, whose answers live in ``answers`` instead.
    data_sensitivity: Mapped[int | None] = mapped_column(default=None)
    business_criticality: Mapped[int | None] = mapped_column(default=None)
    system_access: Mapped[int | None] = mapped_column(default=None)
    regulatory_scope: Mapped[int | None] = mapped_column(default=None)
    fourth_party_reliance: Mapped[int | None] = mapped_column(default=None)

    questionnaire_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vendor_questionnaires.id", ondelete="SET NULL"), default=None
    )
    # ``{question_id: {"value": ..., "comment": ...}}`` for a questionnaire run.
    answers: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    # The questions, options and thresholds exactly as answered. The questionnaire
    # is tenant-editable, and a tier nobody can re-derive is a tier nobody can
    # defend, so the run keeps its own copy the way ``policy_snapshot`` does.
    questionnaire_snapshot: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )

    inherent_score: Mapped[float] = mapped_column(Float)
    computed_tier: Mapped[str]
    # A human beating the arithmetic, on the record, rather than by editing the
    # inputs until the model agrees — which leaves no trace that it happened.
    override_tier: Mapped[str | None] = mapped_column(default=None)
    override_justification: Mapped[str | None] = mapped_column(default=None)

    # The weights and thresholds this run used. Not in the ER, and it earns its
    # width: the policy is tenant-editable, and without this "why is this vendor
    # critical" stops being answerable the moment somebody retunes it.
    policy_snapshot: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )

    assessed_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    assessed_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("vendor_tiering_assessments", "computed_tier", TIERS),
        status_check("vendor_tiering_assessments", "override_tier", TIERS),
        CheckConstraint(
            "(override_tier IS NULL) OR (override_justification IS NOT NULL)",
            name=conv("ck_vendor_tiering_assessments__override_has_reason"),
        ),
        CheckConstraint(
            "data_sensitivity BETWEEN 0 AND 4 AND business_criticality BETWEEN 0 AND 4 AND "
            "system_access BETWEEN 0 AND 4 AND regulatory_scope BETWEEN 0 AND 4 AND "
            "fourth_party_reliance BETWEEN 0 AND 4",
            name=conv("ck_vendor_tiering_assessments__factor_range"),
        ),
        tenant_index("vendor_tiering_assessments", "vendor_id"),
        tenant_index("vendor_tiering_assessments", "engagement_id", "cycle"),
    )


class VendorStage(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """The lifecycle as rows (ER 101), one set per engagement per cycle.

    A skipped stage is a written row, never an omitted one. "Policy said this was
    disproportionate" and "someone forgot" must not look the same to an auditor,
    and a row that was never inserted cannot tell them apart.
    """

    __tablename__ = "vendor_stages"

    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_VENDOR_FK, ondelete="CASCADE"))
    engagement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_ENGAGEMENT_FK, ondelete="CASCADE"))
    # A plain integer rather than a vendor_cycles table: a reassessment increments
    # it and inserts a fresh set of rows. A table would add a join to every
    # lifecycle query in order to hold one integer the stage rows already imply.
    cycle: Mapped[int] = mapped_column(default=1, server_default=text("1"))
    stage: Mapped[str]
    status: Mapped[str] = mapped_column(default="not_started", server_default="not_started")
    is_gate: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    is_required: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    checklist: Mapped[list[Any]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    entered_at: Mapped[datetime | None] = mapped_column(default=None)
    exited_at: Mapped[datetime | None] = mapped_column(default=None)
    skipped_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    skipped_reason: Mapped[str | None] = mapped_column(default=None)
    # The tier rule that skipped it, so a skip is defensible and not merely recorded.
    skipped_by_policy: Mapped[str | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("vendor_stages", "stage", STAGES),
        status_check("vendor_stages", "status", STAGE_STATUSES),
        # Spec 82's "approval gates are never skipped" as a constraint rather than
        # a convention. It is the one rule in this module whose violation is a
        # control failure and not a bug, so it lives in the database.
        CheckConstraint(
            "NOT (is_gate AND status = 'skipped')",
            name=conv("ck_vendor_stages__gate_never_skipped"),
        ),
        UniqueConstraint(
            "tenant_id",
            "engagement_id",
            "cycle",
            "stage",
            name="uq_vendor_stages__engagement_cycle_stage",
        ),
        tenant_index("vendor_stages", "vendor_id"),
        tenant_index("vendor_stages", "engagement_id", "cycle"),
        tenant_index("vendor_stages", "status"),
    )


class VendorTransition(UUIDPrimaryKey, TenantScoped, Base):
    """Every stage movement, append-only. The module's columnar history.

    Carries ``occurred_at`` alone, the documented exception in
    docs/conventions/database.md: an ``updated_at`` on a table that refuses UPDATE
    could only ever lie. Both FK actors are ``ON DELETE NO ACTION`` rather than the
    ``SET NULL`` the sibling transition tables use — SET NULL issues an UPDATE, the
    append-only trigger refuses it, and the membership delete fails. A null actor
    means the system moved the stage, never a deleted person.
    """

    __tablename__ = "vendor_transitions"

    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_VENDOR_FK, ondelete="CASCADE"))
    engagement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_ENGAGEMENT_FK, ondelete="CASCADE"))
    stage_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vendor_stages.id", ondelete="NO ACTION"), default=None
    )
    cycle: Mapped[int] = mapped_column(default=1, server_default=text("1"))
    action: Mapped[str]
    from_stage: Mapped[str | None] = mapped_column(default=None)
    to_stage: Mapped[str | None] = mapped_column(default=None)
    reason: Mapped[str | None] = mapped_column(default=None)
    actor_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="NO ACTION"), default=None
    )
    occurred_at: Mapped[datetime] = mapped_column()

    __table_args__ = (
        status_check("vendor_transitions", "action", TRANSITION_ACTIONS),
        tenant_index("vendor_transitions", "vendor_id"),
        tenant_index("vendor_transitions", "engagement_id", "cycle"),
    )


# ---------------------------------------------------------------------------
# Global content plane — no tenant_id, no RLS, exactly like the control library
# ---------------------------------------------------------------------------


class QuestionnaireTemplate(UUIDPrimaryKey, Timestamped, Base):
    """A published, versioned bank of questions (V5).

    Global content: no ``tenant_id`` and no RLS, the same plane the SOC 2 control
    library sits on. ``built_in`` is forward-looking — a Phase-2 tenant-authored
    bank gets its own tenant-owned table with a policy, rather than a nullable
    ``tenant_id`` retrofitted onto global content after rows exist.

    **V13.** No SIG, CAIQ or HECVAT question text is shipped. That content belongs
    to Shared Assessments, CSA and EDUCAUSE. ``framework_mappings`` names the
    standards this bank covers by identifier so an auditor recognises the coverage
    without any licensed wording being reproduced.
    """

    __tablename__ = "questionnaire_templates"

    # The stable identity across versions and re-seeds, matching how frameworks
    # and control_templates identify themselves.
    code: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    version: Mapped[str]
    description: Mapped[str | None] = mapped_column(default=None)
    suggested_tiers: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    framework_mappings: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    built_in: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    is_current: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    """Which version an issue picks by default. An assessment already in flight
    keeps the ``template_id`` it was dispatched with, so publishing a new version
    never moves a questionnaire under a vendor mid-answer."""
    purpose: Mapped[str] = mapped_column(default="due_diligence", server_default="due_diligence")
    """Which builder this library feeds. A tenant copies from it, never answers it."""

    __table_args__ = (status_check("questionnaire_templates", "purpose", QUESTIONNAIRE_PURPOSES),)

    def __repr__(self) -> str:
        return f"QuestionnaireTemplate(code={self.code!r}, version={self.version!r})"


class QuestionnaireQuestion(UUIDPrimaryKey, Timestamped, Base):
    """One question in a bank. Global content, like its template."""

    __tablename__ = "questionnaire_questions"

    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questionnaire_templates.id", ondelete="CASCADE")
    )
    # Stable across bank versions, so a response written against 2026.1 is still
    # recognisable when 2026.2 rewords the prose. Unique per template, not global:
    # two banks may legitimately both ask about MFA.
    code: Mapped[str]
    # The question itself. The ER's diagram omits it, relying on its own
    # shared-column note; a question table without the question cannot work.
    body: Mapped[str]
    position: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    # Null on a tiering library question: exposure has no control domain.
    domain: Mapped[str | None] = mapped_column(default=None)
    section: Mapped[str | None] = mapped_column(default=None)
    help_text: Mapped[str | None] = mapped_column(default=None)
    # ``[{"key", "label", "score", ...}]`` for a choice question. Empty on the
    # original yes/partial/no/na rows, whose four answers are implied.
    options: Mapped[list[dict[str, Any]]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    required: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    scope_level: Mapped[str] = mapped_column(default="core", server_default="core")
    answer_type: Mapped[str] = mapped_column(default="yes_no_na", server_default="yes_no_na")
    weight: Mapped[float] = mapped_column(Float, default=1.0, server_default=text("1.0"))
    # A "no" here floors the residual score at high, however good the rest is (V7).
    critical_control: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    # A "no" here raises a blocking finding, which the approval gate will not pass.
    non_negotiable: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    evidence_required: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    framework_refs: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    # Conditional branching: this question activates only when the parent carries
    # one of the answers in trigger_condition.
    parent_question_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("questionnaire_questions.id", ondelete="SET NULL"), default=None
    )
    trigger_condition: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )

    __table_args__ = (
        status_check("questionnaire_questions", "domain", RISK_DOMAINS),
        status_check("questionnaire_questions", "scope_level", SCOPE_LEVELS),
        status_check("questionnaire_questions", "answer_type", ANSWER_TYPES),
        UniqueConstraint("template_id", "code", name="uq_questionnaire_questions__template_code"),
        Index("ix_questionnaire_questions__template_id_domain", "template_id", "domain"),
    )

    def __repr__(self) -> str:
        return f"QuestionnaireQuestion(code={self.code!r}, domain={self.domain!r})"


# ---------------------------------------------------------------------------
# Questionnaires a tenant builds — tenant-owned, RLS, the V5 "Phase 2" table
# ---------------------------------------------------------------------------


class VendorQuestionnaire(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A questionnaire a tenant has built, usually by copying from the library.

    One table for both purposes because the builder is the same: sections of typed
    questions with options, rules and scores. What differs is who answers and what
    the answers set, which ``purpose`` names.

    Editing never reaches back. A tiering run and a dispatched review each keep a
    snapshot of the questions they were answered against, so a questionnaire can be
    reworded, reordered or pruned the day after it was used.

    Never deleted (rule 6): retired by archiving, which keeps every run and review
    that points at it readable.
    """

    __tablename__ = "vendor_questionnaires"

    purpose: Mapped[str]
    name: Mapped[str]
    description: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="active", server_default="active")
    # Tiering only: the questionnaire the tiering dialog opens with.
    is_default: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    # Due diligence only: the tiers this one is preselected for when sending. A
    # tier belongs to at most one questionnaire; the service moves it, not copies.
    default_tiers: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    # Tiering only: lower bounds on the 0 to 100 score. Empty means the policy's.
    tier_thresholds: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    library_code: Mapped[str | None] = mapped_column(default=None)
    """The library template it was started from, for provenance. Nothing joins on it."""
    created_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    updated_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )

    __table_args__ = (
        status_check("vendor_questionnaires", "purpose", QUESTIONNAIRE_PURPOSES),
        status_check("vendor_questionnaires", "status", QUESTIONNAIRE_STATUSES),
        tenant_index("vendor_questionnaires", "purpose", "status"),
        # One tiering default per tenant, or the dialog would have to guess.
        Index(
            "uq_vendor_questionnaires__tenant_id_default_tiering",
            "tenant_id",
            unique=True,
            postgresql_where=text("purpose = 'tiering' AND is_default"),
        ),
    )

    def __repr__(self) -> str:
        return f"VendorQuestionnaire(id={self.id!r}, purpose={self.purpose!r})"


class VendorQuestionnaireQuestion(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One question in a tenant questionnaire.

    ``options`` is a list of ``{"key", "label", "score", "flag", "not_applicable",
    "comment_required", "min_tier"}``. JSON rather than a child table because an
    option has no life outside its question: it is written, read and snapshotted
    as part of it, and nothing ever queries one option on its own.
    """

    __tablename__ = "vendor_questionnaire_questions"

    questionnaire_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vendor_questionnaires.id", ondelete="CASCADE")
    )
    position: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    section: Mapped[str] = mapped_column(default="General", server_default="General")
    prompt: Mapped[str]
    help_text: Mapped[str | None] = mapped_column(default=None)
    answer_type: Mapped[str] = mapped_column(
        default="single_choice", server_default="single_choice"
    )
    options: Mapped[list[dict[str, Any]]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    required: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    evidence: Mapped[str] = mapped_column(default="none", server_default="none")
    # Option keys that make a document owed. Empty means any answer owes it.
    evidence_on: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0, server_default=text("1.0"))
    # Due diligence only. Which domain the answer counts toward in the residual.
    domain: Mapped[str | None] = mapped_column(default=None)
    # Due diligence only. A flagged answer here floors the residual at high (V7).
    critical: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    # Due diligence only. A flagged answer here raises a finding the gate will not pass.
    blocking: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    # ``{"question_id": ..., "option_keys": [...]}``: ask this only when an
    # earlier question was answered with one of those options. Empty means always.
    condition: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    framework_refs: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    library_code: Mapped[str | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("vendor_questionnaire_questions", "answer_type", QUESTION_TYPES),
        status_check("vendor_questionnaire_questions", "evidence", EVIDENCE_RULES),
        status_check("vendor_questionnaire_questions", "domain", RISK_DOMAINS),
        # Named by hand: the generated name runs past Postgres's 63 characters.
        Index(
            "ix_vendor_questionnaire_questions__tenant_id_questionnaire_id",
            "tenant_id",
            "questionnaire_id",
            "position",
        ),
    )

    def __repr__(self) -> str:
        return f"VendorQuestionnaireQuestion(id={self.id!r}, type={self.answer_type!r})"


# ---------------------------------------------------------------------------
# The review
# ---------------------------------------------------------------------------


class VendorAssessment(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One review cycle against a vendor engagement.

    The portal credential does not live here. It cannot: a portal request presents
    a token and nothing else, and this table is tenant-owned with FORCE RLS, so it
    cannot be read until a tenant has been bound. See ``VendorPortalToken``.
    """

    __tablename__ = "vendor_assessments"

    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_VENDOR_FK, ondelete="CASCADE"))
    engagement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_ENGAGEMENT_FK, ondelete="CASCADE"))
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("questionnaire_templates.id", ondelete="SET NULL"), default=None
    )
    # Set when the review was sent from a tenant questionnaire rather than the
    # shipped bank. Provenance only: the questions travel on the response rows.
    questionnaire_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vendor_questionnaires.id", ondelete="SET NULL"), default=None
    )
    cycle: Mapped[int] = mapped_column(default=1, server_default=text("1"))
    kind: Mapped[str] = mapped_column(default="initial", server_default="initial")
    review_format: Mapped[str] = mapped_column(
        default="questionnaire", server_default="questionnaire"
    )
    assessment_domain: Mapped[str] = mapped_column(default="security", server_default="security")
    # Snapshotted at dispatch: the template is versioned global content that could
    # change under a vendor mid-questionnaire, and a residual score computed
    # against a question set nobody can reconstruct is not defensible.
    scope: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    status: Mapped[str] = mapped_column(default="pending", server_default="pending")
    due_date: Mapped[date | None] = mapped_column(default=None)

    residual_score: Mapped[float | None] = mapped_column(Float, default=None)
    grade: Mapped[str | None] = mapped_column(default=None)
    domain_scores: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    # The scoring inputs this run used, frozen the way the tiering snapshot is, so
    # a later retune of the ceiling or the domain weights cannot rewrite a past
    # score's explanation.
    score_snapshot: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    # No ``decision`` column, deliberately (V3). ``vendor_approvals`` is the record
    # of who decided what, when and why; this table is the work product. Two tables
    # holding overlapping decision state is a data-integrity trap, and the ER draws
    # two enums here that disagree with each other.

    # The credential itself lives in VendorPortalToken, on the global plane —
    # see that class for why it cannot live on this tenant-owned row.
    portal_contact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vendor_contacts.id", ondelete="SET NULL"), default=None
    )
    submitted_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("vendor_assessments", "kind", ASSESSMENT_KINDS),
        status_check("vendor_assessments", "review_format", REVIEW_FORMATS),
        status_check("vendor_assessments", "assessment_domain", ASSESSMENT_DOMAINS),
        status_check("vendor_assessments", "status", ASSESSMENT_STATUSES),
        status_check("vendor_assessments", "grade", GRADES),
        tenant_index("vendor_assessments", "vendor_id"),
        tenant_index("vendor_assessments", "engagement_id", "cycle"),
        tenant_index("vendor_assessments", "status"),
    )

    def __repr__(self) -> str:
        return f"VendorAssessment(id={self.id!r}, status={self.status!r})"


class VendorPortalToken(UUIDPrimaryKey, Timestamped, Base):
    """The vendor portal credential — global plane, deliberately unpolicied (V11).

    A portal request arrives with a token and no session, so the tenant has to be
    resolved *before* it can be bound; ``vendor_assessments`` is tenant-owned with
    FORCE row-level security, so it cannot be the thing that answers that. This
    table is the way out, and it is not a new idea: ``users`` and
    ``user_identities`` already sit on this plane doing exactly this job, turning
    an externally held credential into an internal identity before any tenant is
    known.

    What it deliberately does **not** hold: the token, any personal data, or
    anything about the vendor. Only a sha256 of the issued token, and the pair it
    resolves to. A reader of the whole table learns that some hash belongs to some
    tenant, and to use that they would already need the token it was made from.

    Rotation writes a new row and revokes the old one, so the history of who was
    sent a link and when survives — an overwritten column would lose it. Every
    read of this table in the service filters ``tenant_id`` explicitly, which
    matters more here than anywhere else in the module: on this table that filter
    is the only wall, not the first of two.
    """

    __tablename__ = "vendor_portal_tokens"

    token_hash: Mapped[str] = mapped_column(unique=True)
    tenant_id: Mapped[uuid.UUID]
    """Not TenantScoped: no policy, and no FK to tenants either, because a torn-down
    tenant's rows are removed by the teardown path rather than cascaded here."""
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vendor_assessments.id", ondelete="CASCADE")
    )
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)
    last_used_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (Index("ix_vendor_portal_tokens__assessment_id", "assessment_id"),)

    def __repr__(self) -> str:
        return f"VendorPortalToken(assessment_id={self.assessment_id!r})"


class VendorAssessmentResponse(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One answer. The table the reference product had and never wrote to.

    Its portal wrote a JSON blob and scoring silently parsed that instead, so the
    normalised table sat empty and every per-question query returned nothing. Here
    the portal writes rows and scoring reads rows. There is no JSON path.
    """

    __tablename__ = "vendor_assessment_responses"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vendor_assessments.id", ondelete="CASCADE")
    )
    # Exactly one of the next two. ``question_id`` points into the shipped bank,
    # which is immutable and versioned. ``question_key`` names a question from a
    # tenant questionnaire, and ``question_snapshot`` carries that question as it
    # was sent, because the questionnaire itself can be edited afterwards.
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("questionnaire_questions.id", ondelete="RESTRICT"), default=None
    )
    question_key: Mapped[str | None] = mapped_column(default=None)
    question_snapshot: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    # The bank's yes/partial/no/na, or a snapshot question's option key. Every
    # typed value (several options, text, a number, a date) is in answer_value.
    answer: Mapped[str | None] = mapped_column(default=None)
    answer_value: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    implementation_notes: Mapped[str | None] = mapped_column(default=None)
    na_justification: Mapped[str | None] = mapped_column(default=None)
    delegated_to_contact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vendor_contacts.id", ondelete="SET NULL"), default=None
    )
    # A bare uuid in the ORM, and a real FK in the database. Declaring the
    # relationship here would make the vendors mapper resolve evidence's table at
    # configuration time, which means importing another module's models — the one
    # thing the boundary contract forbids. The migration owns the constraint;
    # audit_log.actor_id already carries a column this way for the same reason.
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    answered_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        # The four-value vocabulary binds bank rows only. A snapshot row's answer
        # is one of that question's own option keys, checked by the service
        # against the snapshot it carries.
        CheckConstraint(
            "(question_id IS NULL) OR (answer IS NULL) OR "
            "(answer IN ('yes', 'partial', 'no', 'na'))",
            name=conv("ck_vendor_assessment_responses__answer_valid"),
        ),
        CheckConstraint(
            "(question_id IS NULL) <> (question_key IS NULL)",
            name=conv("ck_vendor_assessment_responses__one_question_source"),
        ),
        Index(
            "uq_vendor_assessment_responses__assessment_question_key",
            "tenant_id",
            "assessment_id",
            "question_key",
            unique=True,
            postgresql_where=text("question_key IS NOT NULL"),
        ),
        # "Does not apply" is a claim, and an unexplained one is how a
        # questionnaire is emptied without anybody noticing.
        CheckConstraint(
            "(answer IS DISTINCT FROM 'na') OR (na_justification IS NOT NULL)",
            name=conv("ck_vendor_assessment_responses__na_has_reason"),
        ),
        UniqueConstraint(
            "tenant_id",
            "assessment_id",
            "question_id",
            name="uq_vendor_assessment_responses__assessment_question",
        ),
        tenant_index("vendor_assessment_responses", "assessment_id"),
    )


class VendorFinding(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """What the review found.

    ``promoted_risk_id`` ships nullable with **no foreign key and no promotion
    action**: ``modules/risk/`` has no tables in any migration. The seam is designed
    on both sides, so the column is here and the button is absent rather than
    faked. Spec ¶85 and the ¶109 exit criterion are not satisfiable until a risk
    slice lands — a sequencing gap, stated rather than hidden.
    """

    __tablename__ = "vendor_findings"

    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_VENDOR_FK, ondelete="CASCADE"))
    engagement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_ENGAGEMENT_FK, ondelete="CASCADE"), default=None
    )
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vendor_assessments.id", ondelete="SET NULL"), default=None
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("questionnaire_questions.id", ondelete="SET NULL"), default=None
    )
    # The snapshot question that raised it, for a review sent from a tenant
    # questionnaire. What keeps re-scoring idempotent where question_id is empty.
    question_key: Mapped[str | None] = mapped_column(default=None)
    title: Mapped[str]
    detail: Mapped[str] = mapped_column(default="", server_default=text("''"))
    finding_source: Mapped[str] = mapped_column(default="assessment", server_default="assessment")
    severity: Mapped[str] = mapped_column(default="medium", server_default="medium")
    status: Mapped[str] = mapped_column(default="open", server_default="open")
    treatment: Mapped[str] = mapped_column(default="remediate", server_default="remediate")
    # A critical-control failure that the approval gate will not pass.
    is_blocking: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    sla_due: Mapped[date | None] = mapped_column(default=None)
    owner_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    # Remediation is a real task in the tasks module, never a vendor-local to-do
    # list that no dashboard counts. A bare uuid here and a real FK in the
    # migration, so the mapper never has to resolve another module's table.
    task_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    accepted_until: Mapped[date | None] = mapped_column(default=None)
    accepted_rationale: Mapped[str | None] = mapped_column(default=None)
    accepted_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    closed_at: Mapped[datetime | None] = mapped_column(default=None)
    # No FK: modules/risk has no tables yet. See the class docstring.
    promoted_risk_id: Mapped[uuid.UUID | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("vendor_findings", "finding_source", FINDING_SOURCES),
        status_check("vendor_findings", "severity", FINDING_SEVERITIES),
        status_check("vendor_findings", "status", FINDING_STATUSES),
        status_check("vendor_findings", "treatment", FINDING_TREATMENTS),
        # Acceptance is time-boxed or it is not acceptance: an open-ended accepted
        # risk is a risk nobody will ever look at again.
        CheckConstraint(
            "(status <> 'accepted') OR "
            "(accepted_until IS NOT NULL AND accepted_rationale IS NOT NULL)",
            name=conv("ck_vendor_findings__acceptance_is_time_boxed"),
        ),
        tenant_index("vendor_findings", "vendor_id"),
        tenant_index("vendor_findings", "assessment_id"),
        tenant_index("vendor_findings", "status", "severity"),
        tenant_index("vendor_findings", "owner_membership_id"),
        tenant_index("vendor_findings", "sla_due"),
    )

    def __repr__(self) -> str:
        return f"VendorFinding(id={self.id!r}, severity={self.severity!r}, status={self.status!r})"


# ---------------------------------------------------------------------------
# The decision (section 4)
# ---------------------------------------------------------------------------


class VendorApproval(UUIDPrimaryKey, TenantScoped, Base):
    """The gate record. **Append-only** (ER 122).

    A decision is a thing that happened, so it is never edited. Changing your mind
    is a new row, and a send-back invalidates a stale approval without touching the
    old one — the gate-freshness rule reads ``decided_at >= stage.entered_at``, so
    the previous decision stays in the record and simply stops satisfying a stage
    that restarted after it.

    Both actor keys are ``ON DELETE NO ACTION``: ``SET NULL`` issues an UPDATE that
    the append-only trigger refuses, which would fail the membership delete.
    """

    __tablename__ = "vendor_approvals"

    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_VENDOR_FK, ondelete="CASCADE"))
    engagement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_ENGAGEMENT_FK, ondelete="CASCADE"))
    stage_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vendor_stages.id", ondelete="NO ACTION"), default=None
    )
    cycle: Mapped[int] = mapped_column(default=1, server_default=text("1"))
    decision: Mapped[str]
    rationale: Mapped[str]
    # Who was excluded and why, frozen at decision time. Not derivable later: the
    # business owner can change, and an auditor asking "was segregation of duties
    # applied here" needs the answer this row held when it was written.
    excluded_membership_ids: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    decided_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="NO ACTION"), default=None
    )
    decided_at: Mapped[datetime] = mapped_column()

    __table_args__ = (
        status_check("vendor_approvals", "decision", APPROVAL_DECISIONS),
        # A decision with no reasoning is a signature with no basis, and it is the
        # first thing an auditor asks to see.
        CheckConstraint(
            "length(btrim(rationale)) > 0", name=conv("ck_vendor_approvals__rationale_present")
        ),
        tenant_index("vendor_approvals", "vendor_id"),
        tenant_index("vendor_approvals", "engagement_id", "cycle"),
        tenant_index("vendor_approvals", "stage_id"),
    )


class VendorApprovalCondition(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A condition attached to an "approve with conditions" decision.

    Each one becomes a real task. A condition nobody is assigned and nothing chases
    is the difference between a conditional approval and an unconditional one that
    was written down more elaborately.
    """

    __tablename__ = "vendor_approval_conditions"

    approval_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vendor_approvals.id", ondelete="CASCADE")
    )
    description: Mapped[str]
    owner_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    due_date: Mapped[date | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="open", server_default="open")
    # A bare uuid, and a real FK in the migration: an ORM relationship here would
    # make the vendors mapper resolve the tasks table at configuration time.
    task_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    waived_reason: Mapped[str | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("vendor_approval_conditions", "status", CONDITION_STATUSES),
        CheckConstraint(
            "(status <> 'waived') OR (waived_reason IS NOT NULL)",
            name=conv("ck_vendor_approval_conditions__waiver_has_reason"),
        ),
        tenant_index("vendor_approval_conditions", "approval_id"),
        tenant_index("vendor_approval_conditions", "status"),
    )


# ---------------------------------------------------------------------------
# The paperwork
# ---------------------------------------------------------------------------


class VendorDocument(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A SOC report, certificate, DPA or policy the vendor supplied.

    ``valid_until`` is what drives the expiry sweep, and ``evidence_id`` is what
    lets a reviewed document stand as audit evidence for CC9.2 without being
    uploaded a second time into the evidence library (ER 109).
    """

    __tablename__ = "vendor_documents"

    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_VENDOR_FK, ondelete="CASCADE"))
    doc_type: Mapped[str]
    title: Mapped[str]
    file_ref: Mapped[str | None] = mapped_column(default=None)
    issue_date: Mapped[date | None] = mapped_column(default=None)
    valid_until: Mapped[date | None] = mapped_column(default=None)
    collection_status: Mapped[str] = mapped_column(default="requested", server_default="requested")
    review_notes: Mapped[str | None] = mapped_column(default=None)
    reviewed_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(default=None)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("vendor_documents", "doc_type", DOC_TYPES),
        status_check("vendor_documents", "collection_status", DOC_COLLECTION_STATUSES),
        CheckConstraint(
            "(issue_date IS NULL) OR (valid_until IS NULL) OR (valid_until >= issue_date)",
            name=conv("ck_vendor_documents__coverage_window_ordered"),
        ),
        tenant_index("vendor_documents", "vendor_id"),
        tenant_index("vendor_documents", "doc_type"),
        # The expiry sweep's query, so it stays an index scan as the register grows.
        tenant_index("vendor_documents", "valid_until"),
    )


class VendorSocReportReview(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A SOC report turned from a PDF into queryable fields.

    **ER 110 calls this "precisely the CC9.2 evidence an auditor asks for."** It is
    why the module can satisfy a control the platform already ships and currently
    cannot answer. ``opinion`` and ``findings_material`` lead every rendering of it,
    because those two decide whether anything else on the record matters.
    """

    __tablename__ = "vendor_soc_report_reviews"

    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_VENDOR_FK, ondelete="CASCADE"))
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vendor_documents.id", ondelete="SET NULL"), default=None
    )
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vendor_assessments.id", ondelete="SET NULL"), default=None
    )
    report_kind: Mapped[str] = mapped_column(default="soc2", server_default="soc2")
    report_type: Mapped[str] = mapped_column(default="type_ii", server_default="type_ii")
    audit_period_start: Mapped[date | None] = mapped_column(default=None)
    audit_period_end: Mapped[date | None] = mapped_column(default=None)
    tsc_included: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    opinion: Mapped[str] = mapped_column(default="unqualified", server_default="unqualified")
    bridge_letter_received: Mapped[bool] = mapped_column(
        default=False, server_default=text("false")
    )
    findings_material: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    # Complementary user-entity controls: the things the report assumes *we* do.
    # Unreviewed CUECs are the most commonly missed part of reading a SOC report.
    cuec_reviewed: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    cuec_notes: Mapped[str | None] = mapped_column(default=None)
    subservice_orgs: Mapped[str | None] = mapped_column(default=None)
    cpa_firm: Mapped[str | None] = mapped_column(default=None)
    reviewed_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("vendor_soc_report_reviews", "report_kind", SOC_REPORT_KINDS),
        status_check("vendor_soc_report_reviews", "report_type", SOC_REPORT_TYPES),
        status_check("vendor_soc_report_reviews", "opinion", SOC_OPINIONS),
        CheckConstraint(
            "(audit_period_start IS NULL) OR (audit_period_end IS NULL) OR "
            "(audit_period_end >= audit_period_start)",
            name=conv("ck_vendor_soc_report_reviews__period_ordered"),
        ),
        tenant_index("vendor_soc_report_reviews", "vendor_id"),
        tenant_index("vendor_soc_report_reviews", "audit_period_end"),
    )


class VendorContract(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """Term dates and the security clauses that are otherwise buried in a PDF.

    The five clause flags each answer a question a questionnaire asks and an
    auditor checks. They are booleans on a row rather than prose in a file because
    "do our vendors have a right-to-audit clause" should be a query.
    """

    __tablename__ = "vendor_contracts"

    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_VENDOR_FK, ondelete="CASCADE"))
    engagement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_ENGAGEMENT_FK, ondelete="CASCADE"), default=None
    )
    contract_type: Mapped[str] = mapped_column(default="master", server_default="master")
    title: Mapped[str]
    start_date: Mapped[date | None] = mapped_column(default=None)
    end_date: Mapped[date | None] = mapped_column(default=None)
    renewal_date: Mapped[date | None] = mapped_column(default=None)
    auto_renew: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    notice_period_days: Mapped[int | None] = mapped_column(default=None)
    breach_notification_hours: Mapped[int | None] = mapped_column(default=None)
    right_to_audit: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    subprocessor_terms: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    exit_data_return_clause: Mapped[bool] = mapped_column(
        default=False, server_default=text("false")
    )
    value: Mapped[float | None] = mapped_column(Float, default=None)
    status: Mapped[str] = mapped_column(default="draft", server_default="draft")
    file_ref: Mapped[str | None] = mapped_column(default=None)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("vendor_contracts", "contract_type", CONTRACT_TYPES),
        status_check("vendor_contracts", "status", CONTRACT_STATUSES),
        CheckConstraint(
            "(start_date IS NULL) OR (end_date IS NULL) OR (end_date >= start_date)",
            name=conv("ck_vendor_contracts__term_ordered"),
        ),
        tenant_index("vendor_contracts", "vendor_id"),
        tenant_index("vendor_contracts", "status"),
        tenant_index("vendor_contracts", "renewal_date"),
    )


class VendorSla(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A committed service level, and what was actually measured.

    ``status`` is stored because the ER draws it, but **the breach flag the
    interface shows is derived on read** from the measurement against the target.
    A stored breach goes stale between sweeps, and "breached" that quietly means
    "was breached last Tuesday" is worse than no flag at all.
    """

    __tablename__ = "vendor_slas"

    contract_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vendor_contracts.id", ondelete="CASCADE")
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_VENDOR_FK, ondelete="CASCADE"))
    name: Mapped[str]
    target: Mapped[str]
    measurement: Mapped[str | None] = mapped_column(default=None)
    measured_at: Mapped[date | None] = mapped_column(default=None)
    cure_period_days: Mapped[int | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="on_track", server_default="on_track")

    __table_args__ = (
        status_check("vendor_slas", "status", SLA_STATUSES),
        tenant_index("vendor_slas", "contract_id"),
        tenant_index("vendor_slas", "vendor_id", "status"),
    )


class VendorSubprocessor(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """The fourth-party register.

    ``linked_vendor_id`` is what makes concentration risk visible — the same cloud
    provider sitting under nine of your vendors is a fact you can only see once the
    subprocessor rows point at the vendor row.
    """

    __tablename__ = "vendor_subprocessors"

    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_VENDOR_FK, ondelete="CASCADE"))
    name: Mapped[str]
    service: Mapped[str] = mapped_column(default="", server_default=text("''"))
    data_location: Mapped[str | None] = mapped_column(default=None)
    provenance: Mapped[str] = mapped_column(
        default="vendor_declared", server_default="vendor_declared"
    )
    linked_vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_VENDOR_FK, ondelete="SET NULL"), default=None
    )
    notification_obligation: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="active", server_default="active")

    __table_args__ = (
        status_check("vendor_subprocessors", "provenance", SUBPROCESSOR_PROVENANCE),
        status_check("vendor_subprocessors", "status", SUBPROCESSOR_STATUSES),
        # A vendor that subprocesses to itself is a data-entry slip, not a fact.
        CheckConstraint(
            "linked_vendor_id IS NULL OR linked_vendor_id <> vendor_id",
            name=conv("ck_vendor_subprocessors__not_self_referential"),
        ),
        tenant_index("vendor_subprocessors", "vendor_id"),
        tenant_index("vendor_subprocessors", "linked_vendor_id"),
    )


# ---------------------------------------------------------------------------
# Intake, the roster, and the exit
# ---------------------------------------------------------------------------


class VendorIntakeRequest(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A request to onboard a vendor, before it is one.

    The front door. A declined request keeps its reason and its decider and never
    becomes a vendor row, which is what keeps the register a list of vendors the
    organisation actually uses rather than everything anyone ever proposed.
    """

    __tablename__ = "vendor_intake_requests"

    requested_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    vendor_name: Mapped[str]
    department: Mapped[str | None] = mapped_column(default=None)
    proposed_service: Mapped[str] = mapped_column(default="", server_default=text("''"))
    data_types_shared: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    urgency: Mapped[str] = mapped_column(default="normal", server_default="normal")
    screening_status: Mapped[str] = mapped_column(default="pending", server_default="pending")
    decision: Mapped[str] = mapped_column(default="pending", server_default="pending")
    decision_reason: Mapped[str | None] = mapped_column(default=None)
    decided_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    decided_at: Mapped[datetime | None] = mapped_column(default=None)
    created_vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_VENDOR_FK, ondelete="SET NULL"), default=None
    )

    __table_args__ = (
        status_check("vendor_intake_requests", "urgency", URGENCIES),
        status_check("vendor_intake_requests", "screening_status", INTAKE_SCREENING),
        status_check("vendor_intake_requests", "decision", INTAKE_DECISIONS),
        # A refusal with no stated reason is the request arriving again next
        # quarter with nobody able to say why it was turned down.
        CheckConstraint(
            "(decision <> 'rejected') OR (decision_reason IS NOT NULL)",
            name=conv("ck_vendor_intake_requests__rejection_has_reason"),
        ),
        tenant_index("vendor_intake_requests", "decision"),
        tenant_index("vendor_intake_requests", "requested_by_membership_id"),
    )


class VendorTeamRosterEntry(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """Who plays which role on third-party risk, tenant-wide.

    Roles as rows rather than the reference product's JSON blob, and the resolution
    half of spec 82's "required reviewers": the tiering policy says which roles a
    tier demands, and this says who holds them.
    """

    __tablename__ = "vendor_team_roster"

    role: Mapped[str]
    membership_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_MEMBERSHIP_FK, ondelete="CASCADE"))

    __table_args__ = (
        status_check("vendor_team_roster", "role", ROSTER_ROLES),
        UniqueConstraint(
            "tenant_id", "role", "membership_id", name="uq_vendor_team_roster__role_member"
        ),
        tenant_index("vendor_team_roster", "role"),
    )


class VendorOffboarding(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """The evidenced exit (ER 127).

    ``engagement_id`` is the point: ending one department's use of a vendor is not
    terminating the vendor, and a module that cannot tell those apart revokes too
    much or too little. Nothing hard-deletes — a terminated vendor is archived.
    """

    __tablename__ = "vendor_offboardings"

    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_VENDOR_FK, ondelete="CASCADE"))
    engagement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_ENGAGEMENT_FK, ondelete="CASCADE"), default=None
    )
    reason: Mapped[str]
    access_revoked_at: Mapped[datetime | None] = mapped_column(default=None)
    revoked_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    data_return_attested_at: Mapped[datetime | None] = mapped_column(default=None)
    attestation_assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vendor_assessments.id", ondelete="SET NULL"), default=None
    )
    contract_provisions_reviewed: Mapped[bool] = mapped_column(
        default=False, server_default=text("false")
    )
    final_payments_settled: Mapped[bool] = mapped_column(
        default=False, server_default=text("false")
    )
    certificate_evidence_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    notes: Mapped[str | None] = mapped_column(default=None)

    __table_args__ = (
        tenant_index("vendor_offboardings", "vendor_id"),
        tenant_index("vendor_offboardings", "engagement_id"),
    )


# ---------------------------------------------------------------------------
# Monitoring — built, surfaced, and fed by nothing until Phase 2
# ---------------------------------------------------------------------------


class VendorScorecard(UUIDPrimaryKey, TenantScoped, Timestamped, Integratable, Base):
    """An external security rating. **Manual entry only, in every planned phase.**

    SecurityScorecard, BitSight and UpGuard are in no phase's connector catalogue,
    so every row here is typed in by a person. Rule-9 columns ride anyway, so if
    that ever changes the connector is a sync and not a migration.
    """

    __tablename__ = "vendor_scorecards"

    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_VENDOR_FK, ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(default="manual", server_default="manual")
    score: Mapped[float | None] = mapped_column(Float, default=None)
    overall_grade: Mapped[str | None] = mapped_column(default=None)
    factor_scores: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    as_of: Mapped[datetime] = mapped_column()

    __table_args__ = (
        status_check("vendor_scorecards", "provider", SCORECARD_PROVIDERS),
        integration_unique("vendor_scorecards"),
        tenant_index("vendor_scorecards", "vendor_id", "as_of"),
    )


class VendorSignal(UUIDPrimaryKey, TenantScoped, Timestamped, Integratable, Base):
    """An adverse event about a vendor. Nothing feeds this until Phase 2.

    ``dedup_key`` is what makes the eventual connector idempotent: the same breach
    reported twice is one signal, and without it a re-sync would replay every
    event a customer has already acknowledged.
    """

    __tablename__ = "vendor_signals"

    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(_VENDOR_FK, ondelete="CASCADE"))
    signal_type: Mapped[str]
    source_class: Mapped[str] = mapped_column(default="internal", server_default="internal")
    severity: Mapped[str] = mapped_column(default="medium", server_default="medium")
    title: Mapped[str]
    detail: Mapped[str] = mapped_column(default="", server_default=text("''"))
    dedup_key: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="new", server_default="new")
    acknowledged_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(default=None)
    triggered_assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vendor_assessments.id", ondelete="SET NULL"), default=None
    )
    observed_at: Mapped[datetime] = mapped_column()

    __table_args__ = (
        status_check("vendor_signals", "signal_type", SIGNAL_TYPES),
        status_check("vendor_signals", "source_class", SIGNAL_SOURCE_CLASSES),
        status_check("vendor_signals", "severity", FINDING_SEVERITIES),
        status_check("vendor_signals", "status", SIGNAL_STATUSES),
        integration_unique("vendor_signals"),
        # The same event arriving twice is one signal, whoever reported it.
        UniqueConstraint("tenant_id", "dedup_key", name="uq_vendor_signals__dedup_key"),
        tenant_index("vendor_signals", "vendor_id", "status"),
        tenant_index("vendor_signals", "observed_at"),
    )


class VendorAlertRule(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """What to notify on, and where. In-app works; Slack is wired and inert."""

    __tablename__ = "vendor_alert_rules"

    name: Mapped[str]
    tier_scope: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    signal_types: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    min_severity: Mapped[str] = mapped_column(default="medium", server_default="medium")
    action: Mapped[str] = mapped_column(default="notify", server_default="notify")
    channel: Mapped[str] = mapped_column(default="in_app", server_default="in_app")
    is_enabled: Mapped[bool] = mapped_column(default=True, server_default=text("true"))

    __table_args__ = (
        status_check("vendor_alert_rules", "min_severity", FINDING_SEVERITIES),
        status_check("vendor_alert_rules", "action", ALERT_ACTIONS),
        status_check("vendor_alert_rules", "channel", ALERT_CHANNELS),
        tenant_index("vendor_alert_rules", "is_enabled"),
    )


class VendorDiscoveredApp(UUIDPrimaryKey, TenantScoped, Timestamped, Integratable, Base):
    """Shadow IT from the identity connectors. **Phase 2 — no source until then.**"""

    __tablename__ = "vendor_discovered_apps"

    # No FK: connector_connections does not exist yet, and inventing one to point
    # at would be schema for a module that has not been designed.
    source_connection_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    app_name: Mapped[str]
    oauth_scopes: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    authorizing_users: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    first_seen_at: Mapped[datetime | None] = mapped_column(default=None)
    disposition: Mapped[str] = mapped_column(default="pending", server_default="pending")
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_VENDOR_FK, ondelete="SET NULL"), default=None
    )

    __table_args__ = (
        status_check("vendor_discovered_apps", "disposition", DISCOVERED_DISPOSITIONS),
        integration_unique("vendor_discovered_apps"),
        tenant_index("vendor_discovered_apps", "disposition"),
    )


class VendorAssessmentComment(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """The reviewer conversation on an assessment, which otherwise happens in email.

    ``author_type`` + ``author_id`` is the same polymorphic pair ``audit_log`` uses,
    for the same reason: one foreign key cannot point at both a membership and a
    vendor contact. ``visibility`` is load-bearing — an ``internal_only`` comment
    reaching the portal is a disclosure incident.
    """

    __tablename__ = "vendor_assessment_comments"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vendor_assessments.id", ondelete="CASCADE")
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    author_type: Mapped[str] = mapped_column(
        default="internal_user", server_default="internal_user"
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    visibility: Mapped[str] = mapped_column(default="internal_only", server_default="internal_only")
    body: Mapped[str]

    __table_args__ = (
        status_check("vendor_assessment_comments", "author_type", COMMENT_AUTHOR_TYPES),
        status_check("vendor_assessment_comments", "visibility", COMMENT_VISIBILITY),
        # Just the assessment: adding visibility would take the generated name
        # past Postgres' 63-character identifier limit, and the thread is short
        # enough that filtering visibility after the index scan costs nothing.
        tenant_index("vendor_assessment_comments", "assessment_id"),
    )
