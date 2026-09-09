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

from sqlalchemy import CheckConstraint, Float, ForeignKey, UniqueConstraint, text
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
