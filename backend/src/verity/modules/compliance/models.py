"""Compliance: the global content plane — Layers A and B of
openspec/changes/week2-compliance-engine/design.md.

Six tables, none of them tenant-owned. They are shipped like code: written only by
the content loader running as the migration (owner) role, read by every tenant.
``CLAUDE.md`` rule 1 names global content as the exception to ``tenant_id``, and
``week2-decisions.md`` D10 makes that concrete for these six — no ``tenant_id``, no
row-level security, ``GRANT SELECT`` only to the application role. The wall is the
missing grant, not a policy: a service cannot author a framework even by mistake,
because the privilege is not there to use.

Layer C — ``controls``, ``control_requirement_map``, ``engagements``,
``engagement_frameworks``, ``engagement_scope_categories`` — is tenant-owned, carries
the standard policy, and lands in its own change. Nothing here references it.

Two shapes worth reading before adding to this file:

- ``requirements.id`` is the **stable identity**, minted once per
  ``(framework_id, code)`` and never re-minted. A typo fix or a wording change
  mutates the row; every crosswalk edge is a foreign key to it, so a content update
  cannot leave a dangling mapping. Versioning therefore lives in
  ``framework_version_requirements``, not on the requirement — publishing v1.1
  inserts membership rows for the new version only, and a tenant pinned to v1 keeps
  its denominator (design.md, D7b).
- ``control_templates.canonical_key`` is deliberately **not** unique. Two content
  packs may ship two templates for one concept, and the shared key is what lets
  instantiation collapse them into a single tenant control instead of a twin
  (D7a). On the 114 seeded rows it equals ``code``.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Final

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.elements import conv

from verity.db.base import (
    Base,
    TenantScoped,
    Timestamped,
    UUIDPrimaryKey,
    status_check,
    tenant_index,
)

CONTROL_CATEGORIES: Final[tuple[str, ...]] = (
    "Governance, Risk & Compliance",
    "Data Management & Privacy",
    "Identity & Access Management",
    "Secure Development & Code Management",
    "Infrastructure & Network Security",
    "Logging, Monitoring & Incident Management",
    "Human Resources & Personnel Security",
    "Business Continuity & Third-Party Management",
    "Endpoint Security",
    "Communications & Collaboration Security",
    "Physical & Environmental Security",
)
"""The library's domain taxonomy — which part of the estate a control lives in.

This is the **Type** the signed spec asks every control to carry (decision D1).
One list, used verbatim on ``control_templates`` **and** on ``controls``: a
template whose category a control could not legally hold cannot be instantiated.
The **Sub-type** is ``sub_category``, a finer area inside it, authored per control
in the content pack and deliberately not CHECK constrained (D1 proposed it, and
the client has not confirmed the vocabulary)."""

CONTROL_TYPES: Final[tuple[str, ...]] = (
    "Preventive",
    "Detective",
    "Corrective",
    "Deterrent",
    "Compensating",
    "Directive",
)
"""What a control does about a risk: stop it, surface it, or restore after it.
Shown in the product as **Design**, so the spec's word Type means the domain."""

CONTROL_SUB_TYPES: Final[tuple[str, ...]] = ("Manual", "Automated", "Hybrid")
"""How a control is operated. Hybrid is the honest middle: a system produces the
signal and a person acts on it, which is most of a real SOC 2 estate. Shown in the
product as **Automation**."""

TEMPLATE_IMPORTANCE: Final[tuple[str, ...]] = ("mandatory", "preferred")
"""92 of the 114 shipped templates are mandatory, 22 preferred. The source JSON
carries these upper-cased; the loader normalises."""

COVERAGE_VALUES: Final[tuple[str, ...]] = ("full", "partial")
"""D7c. Every seeded mapping is ``full`` at ``weight=1.000``, which is why the
weighted readiness formula reduces exactly to 1.0 / 0.5 / 0.0 on day one."""

COVERAGE_FULL: Final = "full"

_WEIGHT = Numeric(4, 3)


class Framework(UUIDPrimaryKey, Timestamped, Base):
    """A compliance framework — SOC 2 today, ISO 27001 as an ``INSERT`` later."""

    __tablename__ = "frameworks"

    code: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    description: Mapped[str | None] = mapped_column(default=None)
    built_in: Mapped[bool] = mapped_column(server_default=text("true"), default=True)

    def __repr__(self) -> str:
        return f"Framework(id={self.id!r}, code={self.code!r})"


class FrameworkVersion(UUIDPrimaryKey, Timestamped, Base):
    """A published revision of a framework — ``'2017-rev-2022'`` (D7b).

    An engagement pins one of these, and readiness always computes against the pin,
    so content published mid-engagement cannot move a tenant's number. The partial
    unique index gives exactly one current version per framework, which is a
    constraint rather than a convention because "which one is current" is read on
    every framework list.
    """

    __tablename__ = "framework_versions"

    framework_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("frameworks.id", ondelete="RESTRICT")
    )
    version: Mapped[str]
    published_at: Mapped[datetime]
    is_current: Mapped[bool] = mapped_column(server_default=text("false"), default=False)

    __table_args__ = (
        UniqueConstraint("framework_id", "version"),
        Index(
            "uq_framework_versions__framework_id_current",
            "framework_id",
            unique=True,
            postgresql_where=text("is_current"),
        ),
    )

    def __repr__(self) -> str:
        return f"FrameworkVersion(id={self.id!r}, version={self.version!r})"


class Requirement(UUIDPrimaryKey, Timestamped, Base):
    """One criterion of one framework. The row is the requirement's permanent identity.

    ``requirement_key`` (``'SOC2:CC6.1'``) is the human-facing natural key, carried as
    a real column so it appears in exports, API responses, and log lines without a
    join — an operator names a requirement without knowing a uuid.

    ``is_always_in_scope`` carries "Security is always in scope" as data rather than
    as a string-prefix test on ``code``: true for the 33 common criteria, false for
    the 28 in Availability, Confidentiality, Processing Integrity, and Privacy. A
    second framework decides its own answer at seed time.
    """

    __tablename__ = "requirements"

    framework_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("frameworks.id", ondelete="RESTRICT")
    )
    code: Mapped[str]
    requirement_key: Mapped[str] = mapped_column(unique=True)
    # The fine-grained grouping used for display — 'Logical & Physical Access'.
    category: Mapped[str]
    # The Trust Services Category an engagement scopes on: Security, Availability,
    # Confidentiality, Processing Integrity, Privacy. Scope keys on this rather than
    # on `category`, so 'Security' is a value a user can actually select (the 33 CC
    # criteria span nine display categories that no auditor would recognise as
    # Security).
    trust_services_category: Mapped[str]
    name: Mapped[str]
    description: Mapped[str | None] = mapped_column(default=None)
    is_always_in_scope: Mapped[bool] = mapped_column(server_default=text("false"), default=False)

    __table_args__ = (UniqueConstraint("framework_id", "code"),)

    def __repr__(self) -> str:
        return f"Requirement(id={self.id!r}, requirement_key={self.requirement_key!r})"


class FrameworkVersionRequirement(Timestamped, Base):
    """Which requirements a published version contains. No surrogate key — the pair
    *is* the row (design.md).

    A version that drops a requirement simply omits the row; the requirement and every
    historical mapping to it stay explainable. ``RESTRICT`` both ways: neither a
    published version nor a requirement can be withdrawn out from under a pin.
    """

    __tablename__ = "framework_version_requirements"

    framework_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("framework_versions.id", ondelete="RESTRICT"), primary_key=True
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("requirements.id", ondelete="RESTRICT"), primary_key=True
    )

    def __repr__(self) -> str:
        return (
            f"FrameworkVersionRequirement(version={self.framework_version_id!r}, "
            f"requirement={self.requirement_id!r})"
        )


class ControlTemplate(UUIDPrimaryKey, Timestamped, Base):
    """A shipped control the platform instantiates into a tenant. The compliance IP.

    Four axes that each say something the others do not: ``category`` is where in
    the estate the control lives (the Type), ``sub_category`` the area inside it
    (the Sub-type), and ``control_sub_type`` is how it is operated (Manual /
    Automated / Hybrid, shown as Automation). ``control_type`` (Preventive /
    Detective / Corrective, shown as Design) is available but NULL on shipped
    content — see the column.
    """

    __tablename__ = "control_templates"

    code: Mapped[str] = mapped_column(unique=True)
    canonical_key: Mapped[str]
    name: Mapped[str]
    category: Mapped[str]
    # Optional, and NULL on everything shipped: Preventive/Detective/Corrective
    # is how an organisation describes its own control design. It is not a SOC 2
    # concept and the AICPA does not classify the criteria that way, so the
    # platform must not assert it on framework content. Tenants set it on their
    # own internal or custom controls.
    control_type: Mapped[str | None] = mapped_column(default=None)
    control_sub_type: Mapped[str | None] = mapped_column(default=None)
    # The Sub-type the signed spec asks for: a finer area inside the Type (category).
    sub_category: Mapped[str | None] = mapped_column(default=None)
    importance: Mapped[str]
    description: Mapped[str]
    implementation_guidance: Mapped[str | None] = mapped_column(default=None)
    # What a person or a Verity module provides beyond what the control's checks
    # collect. Each item: ``key``, ``name``, ``assurance`` (design or operating),
    # ``cadence``, ``source`` (upload or platform) and, for platform, ``module``.
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    # The content pack that ships this template. A pack prunes only its own.
    pack: Mapped[str] = mapped_column(default="soc2", server_default=text("'soc2'"))
    built_in: Mapped[bool] = mapped_column(server_default=text("true"), default=True)

    __table_args__ = (
        status_check("control_templates", "category", CONTROL_CATEGORIES),
        status_check("control_templates", "control_type", CONTROL_TYPES),
        status_check("control_templates", "control_sub_type", CONTROL_SUB_TYPES),
        status_check("control_templates", "importance", TEMPLATE_IMPORTANCE),
        # Not unique: two content packs may legitimately ship two templates for one
        # concept, and the shared key is what collapses them at instantiation.
        Index("ix_control_templates__canonical_key", "canonical_key"),
    )

    def __repr__(self) -> str:
        return f"ControlTemplate(id={self.id!r}, code={self.code!r})"


class TemplateRequirementMap(UUIDPrimaryKey, Timestamped, Base):
    """The shipped crosswalk: which template satisfies which requirement.

    ``coverage`` is ``full`` when the control is a primary route for the criterion's
    central obligation and ``partial`` when it supports part of it; ``rationale``
    says which part and what else the criterion needs. A mapping with no rationale
    is a claim nobody can check, so the loader writes both from the content pack.

    Traversed in both directions — requirement→template for coverage, template→
    requirement for the detail view — so it carries two covering indexes rather than
    one, and neither drill-down touches the heap.
    """

    __tablename__ = "template_requirement_map"

    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("control_templates.id", ondelete="RESTRICT")
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("requirements.id", ondelete="RESTRICT")
    )
    coverage: Mapped[str] = mapped_column(
        server_default=text(f"'{COVERAGE_FULL}'"), default=COVERAGE_FULL
    )
    weight: Mapped[Decimal] = mapped_column(
        _WEIGHT, server_default=text("1.000"), default=Decimal("1.000")
    )
    rationale: Mapped[str | None] = mapped_column(default=None)

    __table_args__ = (
        UniqueConstraint(
            "template_id",
            "requirement_id",
            name="uq_template_requirement_map__template_requirement",
        ),
        status_check("template_requirement_map", "coverage", COVERAGE_VALUES),
        CheckConstraint(
            "weight > 0 AND weight <= 1",
            # conv: the ck naming convention contains %(constraint_name)s, so an
            # unmarked explicit name is wrapped a second time at table-attach.
            name=conv("ck_template_requirement_map__weight"),
        ),
        Index(
            "ix_template_requirement_map__requirement_template",
            "requirement_id",
            "template_id",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"TemplateRequirementMap(template={self.template_id!r}, "
            f"requirement={self.requirement_id!r})"
        )


# ---------------------------------------------------------------------------
# Tenant plane — the working control library
# ---------------------------------------------------------------------------

CONTROL_STATUSES: Final[tuple[str, ...]] = (
    "not_started",
    "in_progress",
    "implemented",
    "not_applicable",
)
"""Implementation state of a tenant's control. Rule 6: a control is never
deleted — it is disabled with a reason, which is a separate flag from status so
the state it was in when it was retired is not overwritten."""

CONTROL_SOURCES: Final[tuple[str, ...]] = ("template", "custom")
"""Where the control came from. ``template`` rows keep ``template_id`` so a
library update can be diffed against them; ``custom`` rows are the tenant's own
and have no upstream."""


class Control(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One control in a tenant's working library.

    Instantiated from a :class:`ControlTemplate` or authored by the tenant. The
    template's text is **copied**, not referenced: a tenant edits its own
    wording, and a later library update must not silently rewrite what an
    auditor already reviewed. ``template_id`` records the ancestry so a future
    'template changed' diff is possible.

    Rule 6 — compliance objects are never hard-deleted. ``disabled_at`` +
    ``disabled_reason`` retire a control with a recorded justification; the
    paired CHECK keeps the two from disagreeing.

    Rule 9 — ``source``/``external_id``/``synced_at`` are here from the first
    migration so a future connector that discovers controls is a sync, not a
    migration.
    """

    __tablename__ = "controls"

    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("control_templates.id", ondelete="RESTRICT"), default=None
    )
    code: Mapped[str]
    name: Mapped[str]
    description: Mapped[str]
    implementation_guidance: Mapped[str | None] = mapped_column(default=None)
    category: Mapped[str]
    # The Sub-type: a finer grouping under ``category`` (the Type). Copied from the
    # template at adoption and free text on a custom control, so it is
    # deliberately not CHECK-constrained.
    sub_category: Mapped[str | None] = mapped_column(default=None)
    # NULL for anything instantiated from a template — see ControlTemplate.
    control_type: Mapped[str | None] = mapped_column(default=None)
    control_sub_type: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="not_started")

    # Rule 3: an in-tenant person is a membership, never a global user id.
    owner_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )

    origin: Mapped[str] = mapped_column(default="template")
    disabled_at: Mapped[datetime | None] = mapped_column(default=None)
    disabled_reason: Mapped[str | None] = mapped_column(default=None)

    source: Mapped[str | None] = mapped_column(default=None)
    external_id: Mapped[str | None] = mapped_column(default=None)
    synced_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("controls", "status", CONTROL_STATUSES),
        status_check("controls", "control_type", CONTROL_TYPES),
        status_check("controls", "control_sub_type", CONTROL_SUB_TYPES),
        status_check("controls", "category", CONTROL_CATEGORIES),
        status_check("controls", "origin", CONTROL_SOURCES),
        CheckConstraint(
            "(disabled_at IS NULL) = (disabled_reason IS NULL)",
            name=conv("ck_controls__disabled_has_reason"),
        ),
        # One control per template per tenant: adopting the library twice must
        # not double it. Custom controls have a NULL template_id, and Postgres
        # treats NULLs as distinct, so they are unaffected.
        UniqueConstraint("tenant_id", "template_id", name="uq_controls__tenant_template"),
        UniqueConstraint("tenant_id", "code", name="uq_controls__tenant_code"),
        tenant_index("controls", "status"),
        tenant_index("controls", "category"),
        # Rule 9's uniqueness for anything that arrives from outside.
        Index(
            "uq_controls__tenant_source_external",
            "tenant_id",
            "source",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
    )

    def __repr__(self) -> str:
        return f"Control(id={self.id!r}, tenant_id={self.tenant_id!r}, code={self.code!r})"


class ControlRequirement(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """Which criterion a tenant's control satisfies.

    Seeded from the shipped crosswalk at instantiation, then owned by the
    tenant: mapping a control to another criterion, or unmapping one, is a
    tenant decision an auditor may need to see. This is the table the coverage
    view reads — a criterion with no row here has no control.
    """

    __tablename__ = "control_requirements"

    control_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("controls.id", ondelete="CASCADE"))
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("requirements.id", ondelete="RESTRICT")
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "control_id", "requirement_id", name="uq_control_requirements"
        ),
        tenant_index("control_requirements", "requirement_id"),
        tenant_index("control_requirements", "control_id"),
    )

    def __repr__(self) -> str:
        return (
            f"ControlRequirement(control_id={self.control_id!r}, "
            f"requirement_id={self.requirement_id!r})"
        )


# ---------------------------------------------------------------------------
# Engagement — the audit being prepared for, and what is in its scope
# ---------------------------------------------------------------------------

AUDIT_TYPES: Final[tuple[str, ...]] = ("type_1", "type_2")
"""SOC 2 Type I is a point in time; Type II is a period. The distinction is not
cosmetic: Type II is what makes ``window_start``/``window_end`` an observation
period evidence must fall inside."""

ENGAGEMENT_STATUSES: Final[tuple[str, ...]] = ("draft", "active", "closed")


class Engagement(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """The audit a tenant is preparing for, and the scope it covers.

    One per tenant for now — UNIQUE (tenant_id) — because "engagement setup" is
    a settings screen, not a history. Keeping past engagements is a later change
    that drops this constraint; nothing else here assumes singularity.

    ``categories_in_scope`` holds Trust Services Categories, not criteria. That
    is how SOC 2 scope is actually chosen: you elect Availability or
    Confidentiality, and the criteria follow. Security (the Common Criteria) is
    always in scope and is carried by ``requirements.is_always_in_scope``, not
    by this column, so a tenant cannot elect its way out of it.

    A Type I engagement has a single ``as_of`` date and no window; a Type II has
    both bounds. The CHECK below is what keeps those from disagreeing.
    """

    __tablename__ = "engagements"

    name: Mapped[str]
    framework_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("framework_versions.id", ondelete="RESTRICT")
    )
    audit_type: Mapped[str]
    status: Mapped[str] = mapped_column(default="draft")
    window_start: Mapped[date | None] = mapped_column(default=None)
    window_end: Mapped[date | None] = mapped_column(default=None)
    categories_in_scope: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default=text("'{}'"), default=list
    )

    __table_args__ = (
        status_check("engagements", "audit_type", AUDIT_TYPES),
        status_check("engagements", "status", ENGAGEMENT_STATUSES),
        # Type II observes a period, so it needs both bounds; Type I is a point
        # in time and needs neither. A half-specified window is a bug.
        CheckConstraint(
            "(audit_type = 'type_2') = (window_start IS NOT NULL AND window_end IS NOT NULL)",
            name=conv("ck_engagements__window_matches_type"),
        ),
        CheckConstraint(
            "window_end IS NULL OR window_start IS NULL OR window_end >= window_start",
            name=conv("ck_engagements__window_ordered"),
        ),
        UniqueConstraint("tenant_id", name="uq_engagements__tenant"),
    )

    def __repr__(self) -> str:
        return f"Engagement(tenant_id={self.tenant_id!r}, audit_type={self.audit_type!r})"
