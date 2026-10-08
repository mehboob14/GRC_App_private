"""Risk register (Week 7 / Deliverable 1.2).

Built from ``openspec/changes/week7-risk-register``: ``design.md`` §1 is the
column reference and ``risk-decisions.md`` records every place the ER was
extended.

**The register owns the matrix (R1).** ER 3.6 keys the matrix by tenant; a
workspace here keeps several registers, each with its own levels, bands,
taxonomy and review cadence, so a 5 by 5 enterprise register sits next to a 3 by 3
project register. The four score columns hold raw levels; their upper bound is
the register's, so it is checked in the service rather than by a constant CHECK.

**Scores are generated columns (R2).** ``likelihood * impact``, stored, so the
register sorts and filters on them without the application recomputing.

**Acceptance is a request and a decision (R6).** ``accepted`` on a risk is only
ever set by an approved acceptance, and an expired or revoked one reopens it.

Cross-module references to controls are a bare uuid here and a real foreign key
in the migration, so the mapper never resolves another module's table.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Final

from sqlalchemy import CheckConstraint, FetchedValue, ForeignKey, Index, SmallInteger, text
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

REGISTER_TYPES: Final[tuple[str, ...]] = (
    "enterprise",
    "rcsa",
    "iso_27001",
    "soc_2",
    "pci_dss",
    "sox",
    "gdpr",
    "nist_csf",
    "sama_csf",
    "internal",
    "project",
    "third_party",
    "other",
)
REGISTER_STATUSES: Final[tuple[str, ...]] = ("active", "archived")

RISK_STATUSES: Final[tuple[str, ...]] = ("open", "in_treatment", "mitigated", "accepted", "closed")
TREATMENTS: Final[tuple[str, ...]] = ("mitigate", "accept", "avoid", "transfer")
ORIGINS: Final[tuple[str, ...]] = ("manual", "library", "import", "vendor_finding", "assessment")

ACCEPTANCE_STATUSES: Final[tuple[str, ...]] = (
    "pending",
    "active",
    "rejected",
    "withdrawn",
    "expired",
    "revoked",
)

EVENT_KINDS: Final[tuple[str, ...]] = (
    "created",
    "updated",
    "scored",
    "status",
    "treatment",
    "owner",
    "control_linked",
    "control_unlinked",
    "linked",
    "unlinked",
    "action_added",
    "acceptance_requested",
    "acceptance_approved",
    "acceptance_rejected",
    "acceptance_withdrawn",
    "acceptance_revoked",
    "acceptance_expired",
    "reviewed",
    "imported",
    "adopted",
    "promoted",
)

MIN_LEVELS: Final = 3
MAX_LEVELS: Final = 6

_MEMBERSHIP_FK: Final = "tenant_memberships.id"


def _member(**kwargs: Any) -> Mapped[uuid.UUID | None]:  # noqa: ANN401 — mapped_column kwargs
    return mapped_column(ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None, **kwargs)


class RiskRegister(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One register and its configuration: matrix, bands, taxonomy, cadence."""

    __tablename__ = "risk_registers"

    name: Mapped[str]
    register_type: Mapped[str] = mapped_column(default="enterprise")
    description: Mapped[str | None] = mapped_column(default=None)
    owner_membership_id: Mapped[uuid.UUID | None] = _member()
    is_default: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    status: Mapped[str] = mapped_column(default="active", server_default="active")
    likelihood_levels: Mapped[int] = mapped_column(SmallInteger, default=5)
    impact_levels: Mapped[int] = mapped_column(SmallInteger, default=5)
    # [{level, label, description}] in level order; length equals the level count.
    likelihood_scale: Mapped[list[dict[str, Any]]] = mapped_column(postgresql.JSONB, default=list)
    impact_scale: Mapped[list[dict[str, Any]]] = mapped_column(postgresql.JSONB, default=list)
    # [{key, label, min_score}] ascending; the first starts at 1.
    severity_bands: Mapped[list[dict[str, Any]]] = mapped_column(postgresql.JSONB, default=list)
    review_cadence_days: Mapped[int] = mapped_column(default=90, server_default=text("90"))
    # {method: product|additive|weighted, likelihood_weight, impact_weight}
    scoring_formula: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=lambda: {"method": "product"}
    )
    # {<category id>: {appetite, tolerance}} in score units of this register.
    appetite: Mapped[dict[str, Any]] = mapped_column(postgresql.JSONB, default=dict)
    created_by_membership_id: Mapped[uuid.UUID | None] = _member()

    __table_args__ = (
        status_check("risk_registers", "register_type", REGISTER_TYPES),
        status_check("risk_registers", "status", REGISTER_STATUSES),
        CheckConstraint(
            f"likelihood_levels BETWEEN {MIN_LEVELS} AND {MAX_LEVELS} "
            f"AND impact_levels BETWEEN {MIN_LEVELS} AND {MAX_LEVELS}",
            name=conv("ck_risk_registers__levels_in_range"),
        ),
        CheckConstraint(
            "review_cadence_days BETWEEN 7 AND 730",
            name=conv("ck_risk_registers__cadence_in_range"),
        ),
        Index(
            "uq_risk_registers__tenant_id_default",
            "tenant_id",
            unique=True,
            postgresql_where=text("is_default"),
        ),
    )


class RiskCategory(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A category (``parent_id`` null) or a subcategory of one, per register (R10)."""

    __tablename__ = "risk_categories"

    register_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("risk_registers.id", ondelete="CASCADE")
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("risk_categories.id", ondelete="CASCADE"), default=None
    )
    name: Mapped[str]
    position: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    archived_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (tenant_index("risk_categories", "register_id"),)


class RiskTemplate(UUIDPrimaryKey, Timestamped, Base):
    """A starter library risk. Global content: no tenant, SELECT only for the app."""

    __tablename__ = "risk_templates"

    code: Mapped[str] = mapped_column(unique=True)
    title: Mapped[str]
    description: Mapped[str] = mapped_column(default="", server_default=text("''"))
    category: Mapped[str]
    sub_category: Mapped[str | None] = mapped_column(default=None)
    default_likelihood: Mapped[int] = mapped_column(SmallInteger)
    default_impact: Mapped[int] = mapped_column(SmallInteger)
    root_cause: Mapped[str | None] = mapped_column(default=None)
    consequences: Mapped[str | None] = mapped_column(default=None)
    recommendations: Mapped[str | None] = mapped_column(default=None)
    treatment: Mapped[str | None] = mapped_column(default=None)
    control_keys: Mapped[list[str]] = mapped_column(postgresql.JSONB, default=list)
    frameworks: Mapped[list[str]] = mapped_column(postgresql.JSONB, default=list)
    built_in: Mapped[bool] = mapped_column(default=True, server_default=text("true"))


class Risk(UUIDPrimaryKey, TenantScoped, Timestamped, Integratable, Base):
    """The risk itself (ER ``RISKS``)."""

    __tablename__ = "risks"

    register_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("risk_registers.id", ondelete="RESTRICT")
    )
    code: Mapped[str]
    title: Mapped[str]
    description: Mapped[str] = mapped_column(default="", server_default=text("''"))
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("risk_categories.id", ondelete="RESTRICT")
    )
    sub_category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("risk_categories.id", ondelete="RESTRICT"), default=None
    )
    status: Mapped[str] = mapped_column(default="open", server_default="open")
    treatment: Mapped[str | None] = mapped_column(default=None)
    inherent_likelihood: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    inherent_impact: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    residual_likelihood: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    residual_impact: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    # Filled by the ``trg_risks_scores`` trigger from the register's formula (R2).
    inherent_score: Mapped[int | None] = mapped_column(
        server_default=FetchedValue(), server_onupdate=FetchedValue()
    )
    residual_score: Mapped[int | None] = mapped_column(
        server_default=FetchedValue(), server_onupdate=FetchedValue()
    )
    # Tenant-defined extras (``customfields``), validated against the definitions.
    custom_fields: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    root_cause: Mapped[str | None] = mapped_column(default=None)
    consequences: Mapped[str | None] = mapped_column(default=None)
    recommendations: Mapped[str | None] = mapped_column(default=None)
    treatment_plan: Mapped[str | None] = mapped_column(default=None)
    owner_membership_id: Mapped[uuid.UUID | None] = _member()
    department_group_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("groups.id", ondelete="SET NULL"), default=None
    )
    treatment_due_on: Mapped[date | None] = mapped_column(default=None)
    next_review_on: Mapped[date | None] = mapped_column(default=None)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(default=None)
    origin: Mapped[str] = mapped_column(default="manual", server_default="manual")
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("risk_templates.id", ondelete="SET NULL"), default=None
    )
    origin_ref: Mapped[uuid.UUID | None] = mapped_column(default=None)
    closure_justification: Mapped[str | None] = mapped_column(default=None)
    closed_at: Mapped[datetime | None] = mapped_column(default=None)
    closed_by_membership_id: Mapped[uuid.UUID | None] = _member()
    created_by_membership_id: Mapped[uuid.UUID | None] = _member()

    __table_args__ = (
        status_check("risks", "status", RISK_STATUSES),
        status_check("risks", "treatment", TREATMENTS),
        status_check("risks", "origin", ORIGINS),
        CheckConstraint(
            "(inherent_likelihood IS NULL) = (inherent_impact IS NULL) "
            "AND (residual_likelihood IS NULL) = (residual_impact IS NULL)",
            name=conv("ck_risks__scores_paired"),
        ),
        CheckConstraint(
            "COALESCE(inherent_likelihood, 1) >= 1 AND COALESCE(inherent_impact, 1) >= 1 "
            "AND COALESCE(residual_likelihood, 1) >= 1 AND COALESCE(residual_impact, 1) >= 1",
            name=conv("ck_risks__scores_positive"),
        ),
        # A closed risk with no reason is the audit gap the reason exists to close.
        CheckConstraint(
            "(status <> 'closed') OR (closure_justification IS NOT NULL)",
            name=conv("ck_risks__closure_justified"),
        ),
        tenant_index("risks", "code", unique=True),
        integration_unique("risks"),
        tenant_index("risks", "register_id"),
        tenant_index("risks", "status"),
        tenant_index("risks", "owner_membership_id"),
        tenant_index("risks", "residual_score"),
        tenant_index("risks", "next_review_on"),
        tenant_index("risks", "category_id"),
    )

    def __repr__(self) -> str:
        return f"Risk(id={self.id!r}, code={self.code!r}, status={self.status!r})"


class RiskControlMap(UUIDPrimaryKey, TenantScoped, Base):
    """A control that mitigates a risk (ER ``RISK_CONTROL_MAP``)."""

    __tablename__ = "risk_control_map"

    risk_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("risks.id", ondelete="CASCADE"))
    # Real FK to controls in the migration; bare here (module boundary).
    control_id: Mapped[uuid.UUID]
    created_by_membership_id: Mapped[uuid.UUID | None] = _member()
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    __table_args__ = (
        tenant_index("risk_control_map", "risk_id", "control_id", unique=True),
        tenant_index("risk_control_map", "control_id"),
    )


class RiskAcceptance(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A request to accept a risk's residual exposure, and its decision (R6, R7)."""

    __tablename__ = "risk_acceptances"

    risk_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("risks.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(default="pending", server_default="pending")
    rationale: Mapped[str]
    expires_on: Mapped[date]
    requested_by_membership_id: Mapped[uuid.UUID | None] = _member()
    approver_membership_id: Mapped[uuid.UUID | None] = _member()
    residual_score_at_request: Mapped[int | None] = mapped_column(default=None)
    decided_at: Mapped[datetime | None] = mapped_column(default=None)
    decision_note: Mapped[str | None] = mapped_column(default=None)
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)
    revoked_by_membership_id: Mapped[uuid.UUID | None] = _member()
    revoke_reason: Mapped[str | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("risk_acceptances", "status", ACCEPTANCE_STATUSES),
        CheckConstraint(
            "approver_membership_id IS NULL OR requested_by_membership_id IS NULL "
            "OR approver_membership_id <> requested_by_membership_id",
            name=conv("ck_risk_acceptances__not_self_approved"),
        ),
        Index(
            "uq_risk_acceptances__tenant_id_risk_id_open",
            "tenant_id",
            "risk_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'active')"),
        ),
        tenant_index("risk_acceptances", "status", "expires_on"),
    )


class RiskEvent(UUIDPrimaryKey, TenantScoped, Base):
    """One entry in a risk's history. Score snapshots feed a later trend chart."""

    __tablename__ = "risk_events"

    risk_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("risks.id", ondelete="CASCADE"))
    kind: Mapped[str]
    from_value: Mapped[str | None] = mapped_column(default=None)
    to_value: Mapped[str | None] = mapped_column(default=None)
    note: Mapped[str | None] = mapped_column(default=None)
    inherent_score: Mapped[int | None] = mapped_column(default=None)
    residual_score: Mapped[int | None] = mapped_column(default=None)
    actor_membership_id: Mapped[uuid.UUID | None] = _member()
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    __table_args__ = (
        status_check("risk_events", "kind", EVENT_KINDS),
        tenant_index("risk_events", "risk_id", "created_at"),
    )
