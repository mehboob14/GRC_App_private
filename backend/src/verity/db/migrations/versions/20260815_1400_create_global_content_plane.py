"""create the global content plane — frameworks, requirements, control templates

Revision ID: e6b1d97c4a52
Revises: c3f9a1b4e2d8
Create Date: 2026-08-15 14:00:00.000000

Layers A and B of openspec/changes/week2-compliance-engine/design.md: the six
tables the platform ships like code. ``frameworks``, ``framework_versions``,
``requirements``, ``framework_version_requirements``, ``control_templates``,
``template_requirement_map``.

**No table here enables row-level security, and that is deliberate.** These are
global content — ``CLAUDE.md`` rule 1's stated exception to ``tenant_id``, made
concrete for these six by ``week2-decisions.md`` D10. RLS naively applied to a
global table would make every tenant's compliance read return zero rows, which is
the more dangerous of the two failure modes because it looks like empty data
rather than like a bug.

**The application role receives ``SELECT`` and nothing else.** ``grant_crud()`` is
deliberately not called: the content loader runs as the migration (owner) role,
which ``core/config.py`` already requires to be distinct from the application role
in a deployed environment. A service cannot author a framework or a requirement
even by mistake — the privilege is absent, so there is no policy to get wrong.

Seeds ``frameworks:read`` (D9), the one Week 2 key these tables need. The other
four Week 2 keys — ``controls:read``, ``controls:manage``, ``engagements:read``,
``engagements:manage`` — belong to the migration that creates the tenant-owned
tables they govern, and are not seeded here.

The downgrade drops all six tables and the permission row. It destroys the shipped
content library, not tenant work: nothing tenant-owned exists in this change yet.
Once ``controls.template_id`` exists, the ``RESTRICT`` foreign keys will refuse
this downgrade while any tenant has instantiated a control, which is the intended
protection.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.core.config import get_settings

revision: str = "e6b1d97c4a52"
down_revision: str | None = "c3f9a1b4e2d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Frozen copies of the vocabularies in modules/compliance/models.py, literal here
# for the same reason the Week 1 migration spells out its status checks: a migration
# that imports a live constant rewrites its own history the day the constant moves,
# and a fresh database then gets different DDL from an upgraded one. The ORM side is
# the live definition; `tests/unit/test_compliance_models.py` fails if the two drift.
_CONTROL_TYPES: Sequence[str] = (
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
_TEMPLATE_IMPORTANCE: Sequence[str] = ("mandatory", "preferred")
_COVERAGE_VALUES: Sequence[str] = ("full", "partial")

# Reverse dependency order; each drop takes its indexes and constraints with it.
_TABLES = (
    "template_requirement_map",
    "control_templates",
    "framework_version_requirements",
    "requirements",
    "framework_versions",
    "frameworks",
)

_PERMISSION_KEY = "frameworks:read"


def _timestamps() -> tuple[sa.Column[Any], sa.Column[Any]]:
    return (
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def _in_list(column: str, allowed: Sequence[str]) -> str:
    """Render ``col IN ('a', 'b')`` from a compile-time constant tuple.

    The vocabularies live in ``modules/compliance/models.py`` and are imported rather
    than retyped, so the ORM's ``CHECK`` and the migration's cannot drift apart. The
    values are library categories containing ``&`` and ``,`` but never a quote; the
    doubling is belt-and-braces on content that is a module constant, not input.
    """
    rendered = ", ".join("'" + value.replace("'", "''") + "'" for value in allowed)
    return f"{column} IN ({rendered})"


def upgrade() -> None:
    op.create_table(
        "frameworks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("code", name=op.f("uq_frameworks__code")),
    )

    op.create_table(
        "framework_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("framework_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("published_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *_timestamps(),
        # RESTRICT: a framework cannot be withdrawn while a published version exists.
        sa.ForeignKeyConstraint(
            ["framework_id"],
            ["frameworks.id"],
            name=op.f("fk_framework_versions__framework_id"),
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "framework_id", "version", name=op.f("uq_framework_versions__framework_id_version")
        ),
    )
    # Exactly one current version per framework. Partial, because the non-current
    # rows are the history and must not collide.
    op.create_index(
        "uq_framework_versions__framework_id_current",
        "framework_versions",
        ["framework_id"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )

    op.create_table(
        "requirements",
        # NEVER re-minted for a given (framework_id, code): a typo fix mutates this
        # row, so no crosswalk edge is ever orphaned by a content update.
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("framework_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        # 'SOC2:CC6.1' — the human-facing natural key, carried so exports, responses,
        # and log lines can name a requirement without a join or a uuid.
        sa.Column("requirement_key", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        # The Trust Services Category an engagement scopes on (Security,
        # Availability, Confidentiality, Processing Integrity, Privacy).
        # `category` stays the finer grouping used for display; scoping keys on
        # this, so "Security" is a value a user can actually select.
        sa.Column("trust_services_category", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # "Security is always in scope" as data: true for the 33 common criteria.
        sa.Column(
            "is_always_in_scope", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["framework_id"],
            ["frameworks.id"],
            name=op.f("fk_requirements__framework_id"),
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("requirement_key", name=op.f("uq_requirements__requirement_key")),
        sa.UniqueConstraint(
            "framework_id", "code", name=op.f("uq_requirements__framework_id_code")
        ),
    )

    op.create_table(
        "framework_version_requirements",
        # No surrogate key: the pair is the row. Version membership lives here rather
        # than on requirements, so a requirement's identity survives a version bump.
        sa.Column("framework_version_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), primary_key=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["framework_version_id"],
            ["framework_versions.id"],
            name=op.f("fk_framework_version_requirements__framework_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["requirements.id"],
            name=op.f("fk_framework_version_requirements__requirement_id"),
            ondelete="RESTRICT",
        ),
    )

    op.create_table(
        "control_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.Text(), nullable=False),
        # Deliberately NOT unique — see the index below.
        sa.Column("canonical_key", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        # D1: seeded equal to category; the same vocabulary the tenant-owned
        # `controls` table will carry, so every template is instantiable.
        sa.Column("control_type", sa.Text(), nullable=False),
        # D1: NO CHECK. No Sub-type vocabulary exists yet, and a check against an
        # empty vocabulary rejects every non-null value.
        sa.Column("control_sub_type", sa.Text(), nullable=True),
        sa.Column("importance", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("implementation_guidance", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            _in_list("control_type", _CONTROL_TYPES),
            name=op.f("ck_control_templates__control_type_valid"),
        ),
        sa.CheckConstraint(
            _in_list("importance", _TEMPLATE_IMPORTANCE),
            name=op.f("ck_control_templates__importance_valid"),
        ),
        sa.UniqueConstraint("code", name=op.f("uq_control_templates__code")),
    )
    # Non-unique on purpose: two content packs may ship two templates for one
    # concept, and the shared canonical key is what collapses them into a single
    # tenant control at instantiation instead of a twin (D7a).
    op.create_index("ix_control_templates__canonical_key", "control_templates", ["canonical_key"])

    op.create_table(
        "template_requirement_map",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("coverage", sa.Text(), server_default=sa.text("'full'"), nullable=False),
        sa.Column("weight", sa.Numeric(4, 3), server_default=sa.text("1.000"), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            _in_list("coverage", _COVERAGE_VALUES),
            name=op.f("ck_template_requirement_map__coverage_valid"),
        ),
        sa.CheckConstraint(
            "weight > 0 AND weight <= 1",
            name=op.f("ck_template_requirement_map__weight"),
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["control_templates.id"],
            name=op.f("fk_template_requirement_map__template_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["requirements.id"],
            name=op.f("fk_template_requirement_map__requirement_id"),
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "template_id",
            "requirement_id",
            name=op.f("uq_template_requirement_map__template_requirement"),
        ),
    )
    # The reverse direction, covering: "which templates satisfy these requirements"
    # is the coverage view's question and is answered index-only.
    op.create_index(
        "ix_template_requirement_map__requirement_template",
        "template_requirement_map",
        ["requirement_id", "template_id"],
    )

    # -- grants: SELECT only, no RLS (D10) ---------------------------------------
    #
    # No enable_rls() call anywhere above. Global content has no tenant_id to police,
    # and a policy here would return zero rows for every tenant. No grant_crud()
    # either: the loader runs as the owner role, so the application role gets read
    # and nothing else. The missing privilege IS the wall.
    app_role = get_settings().database.app_role
    for table in _TABLES:
        op.execute(sa.text(f"GRANT SELECT ON {table} TO {app_role}"))

    # -- permission seed (D9) -----------------------------------------------------

    op.execute(
        sa.text(
            "INSERT INTO permissions (key, module, action) "
            "VALUES ('frameworks:read', 'frameworks', 'read') ON CONFLICT (key) DO NOTHING"
        )
    )


def downgrade() -> None:
    # Destroys the shipped content library. Nothing tenant-owned references it yet;
    # once `controls.template_id` exists, the RESTRICT foreign keys refuse this while
    # any tenant has an instantiated control, which is the point of RESTRICT.
    # S608 suppressed: _PERMISSION_KEY is a module constant, never input. Same
    # pattern (and same suppression) as the iam migration's permission seeding.
    op.execute(
        sa.text(f"DELETE FROM permissions WHERE key = '{_PERMISSION_KEY}'")  # noqa: S608
    )
    for table in _TABLES:
        op.drop_table(table)
