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
ANSWER_TYPES: Final[tuple[str, ...]] = (
    "yes_no_na",
    "select",
    "multi_select",
    "text",
    "numeric",
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

    data_sensitivity: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    business_criticality: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    system_access: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    regulatory_scope: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    fourth_party_reliance: Mapped[int] = mapped_column(default=0, server_default=text("0"))

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
    domain: Mapped[str]
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
    decision: Mapped[str] = mapped_column(default="pending", server_default="pending")

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
        status_check("vendor_assessments", "decision", ASSESSMENT_DECISIONS),
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
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questionnaire_questions.id", ondelete="RESTRICT")
    )
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
        status_check("vendor_assessment_responses", "answer", ANSWER_VALUES),
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
