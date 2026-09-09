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
from datetime import date
from typing import Final

from sqlalchemy import CheckConstraint, Float, ForeignKey, text
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
