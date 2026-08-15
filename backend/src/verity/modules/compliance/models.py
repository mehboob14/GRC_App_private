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
from datetime import datetime
from decimal import Decimal
from typing import Final

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.elements import conv

from verity.db.base import Base, Timestamped, UUIDPrimaryKey, status_check

CONTROL_TYPES: Final[tuple[str, ...]] = (
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
"""The Type vocabulary (D1), derived from the 11 categories the shipped library
already carries on all 114 rows. One list, used verbatim on ``control_templates``
**and** on ``controls``: a template whose type a control could not legally hold is a
template that cannot be instantiated. If the client supplies its own axis, this is a
``DROP CONSTRAINT`` / ``ADD CONSTRAINT`` plus an ``UPDATE`` of the seeded rows."""

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

    ``category`` is the library's own taxonomy and ``control_type`` is the client-facing
    Type axis; D1 seeds them equal on all 114 rows and they diverge only if the client
    supplies a different Type vocabulary, which is then an ``UPDATE`` of one column.

    ``control_sub_type`` carries **no** ``CHECK``, deliberately. D1: no Sub-type
    vocabulary exists yet, and a check against an empty vocabulary rejects every
    non-null value — a column no custom control could ever populate. The constraint
    arrives with the client's list.
    """

    __tablename__ = "control_templates"

    code: Mapped[str] = mapped_column(unique=True)
    canonical_key: Mapped[str]
    name: Mapped[str]
    category: Mapped[str]
    control_type: Mapped[str]
    control_sub_type: Mapped[str | None] = mapped_column(default=None)
    importance: Mapped[str]
    description: Mapped[str]
    implementation_guidance: Mapped[str | None] = mapped_column(default=None)
    built_in: Mapped[bool] = mapped_column(server_default=text("true"), default=True)

    __table_args__ = (
        status_check("control_templates", "control_type", CONTROL_TYPES),
        status_check("control_templates", "importance", TEMPLATE_IMPORTANCE),
        # Not unique: two content packs may legitimately ship two templates for one
        # concept, and the shared key is what collapses them at instantiation.
        Index("ix_control_templates__canonical_key", "canonical_key"),
    )

    def __repr__(self) -> str:
        return f"ControlTemplate(id={self.id!r}, code={self.code!r})"


class TemplateRequirementMap(UUIDPrimaryKey, Timestamped, Base):
    """The shipped crosswalk: which template satisfies which requirement. 150 rows.

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
