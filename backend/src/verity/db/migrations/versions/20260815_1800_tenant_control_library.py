"""tenant control library — controls and their criterion mappings

Revision ID: a7c2e5f81b93
Revises: e6b1d97c4a52
Create Date: 2026-08-15 18:00:00.000000

Layer C of openspec/changes/week2-compliance-engine/design.md: the tenant's own
working library, instantiated from the shipped templates.

Two tenant-owned tables, so both get RLS in this same migration (rule 12) and
``tenant_id`` leads every composite index (rule 1).

This migration also repoints the Type axis. Until now ``control_templates.
control_type`` held the same 11 values as ``category`` (decision D1, taken when
no Type vocabulary existed). It now holds Preventive / Detective / Corrective,
and ``control_sub_type`` — previously null on all 114 rows and deliberately
unconstrained — holds Manual / Automated / Hybrid. The three CHECKs are
rewritten to match, and the data is re-seeded from the content pack, so the
column that used to duplicate Category now carries information of its own.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.db.rls import enable_rls, grant_crud

revision: str = "a7c2e5f81b93"
down_revision: str | None = "e6b1d97c4a52"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONTROL_CATEGORIES = (
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
CONTROL_TYPES = ("Preventive", "Detective", "Corrective")
CONTROL_SUB_TYPES = ("Manual", "Automated", "Hybrid")
CONTROL_STATUSES = ("not_started", "in_progress", "implemented", "not_applicable")
CONTROL_ORIGINS = ("template", "custom")


def _in_list(column: str, allowed: tuple[str, ...]) -> str:
    joined = ", ".join(f"'{value}'" for value in allowed)
    return f"{column} IN ({joined})"


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


def upgrade() -> None:
    # -- Type / Sub-type vocabulary -------------------------------------------
    # The old CHECK allowed the 11 category values; the new one allows the three
    # Type values, so it has to be dropped before the data is rewritten.
    op.drop_constraint("control_type_valid", "control_templates", type_="check")
    op.execute(
        "UPDATE control_templates SET control_type = 'Preventive', "
        "control_sub_type = 'Manual' WHERE control_type IS NOT NULL"
    )
    op.create_check_constraint(
        "category_valid",
        "control_templates",
        _in_list("category", CONTROL_CATEGORIES),
    )
    op.create_check_constraint(
        "control_type_valid",
        "control_templates",
        _in_list("control_type", CONTROL_TYPES),
    )
    op.create_check_constraint(
        "control_sub_type_valid",
        "control_templates",
        _in_list("control_sub_type", CONTROL_SUB_TYPES),
    )

    # -- controls --------------------------------------------------------------
    op.create_table(
        "controls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("implementation_guidance", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("control_type", sa.Text(), nullable=False),
        sa.Column("control_sub_type", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'not_started'"), nullable=False),
        sa.Column("owner_membership_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("origin", sa.Text(), server_default=sa.text("'template'"), nullable=False),
        sa.Column("disabled_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("disabled_reason", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("synced_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_controls__tenant_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["control_templates.id"],
            name=op.f("fk_controls__template_id"),
            ondelete="RESTRICT",
        ),
        # Rule 3: an in-tenant person is a membership, never a global user id.
        sa.ForeignKeyConstraint(
            ["owner_membership_id"],
            ["tenant_memberships.id"],
            name=op.f("fk_controls__owner_membership_id"),
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            _in_list("category", CONTROL_CATEGORIES),
            name=op.f("ck_controls__category_valid"),
        ),
        sa.CheckConstraint(
            _in_list("control_type", CONTROL_TYPES),
            name=op.f("ck_controls__control_type_valid"),
        ),
        sa.CheckConstraint(
            _in_list("control_sub_type", CONTROL_SUB_TYPES),
            name=op.f("ck_controls__control_sub_type_valid"),
        ),
        sa.CheckConstraint(
            _in_list("status", CONTROL_STATUSES), name=op.f("ck_controls__status_valid")
        ),
        sa.CheckConstraint(
            _in_list("origin", CONTROL_ORIGINS), name=op.f("ck_controls__origin_valid")
        ),
        # Retiring a control records why; the two columns cannot disagree.
        sa.CheckConstraint(
            "(disabled_at IS NULL) = (disabled_reason IS NULL)",
            name="ck_controls__disabled_has_reason",
        ),
        # Adopting the library twice must not double it.
        sa.UniqueConstraint("tenant_id", "template_id", name="uq_controls__tenant_template"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_controls__tenant_code"),
    )
    op.create_index("ix_controls__tenant_id_status", "controls", ["tenant_id", "status"])
    op.create_index("ix_controls__tenant_id_category", "controls", ["tenant_id", "category"])
    op.create_index(
        "uq_controls__tenant_source_external",
        "controls",
        ["tenant_id", "source", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    enable_rls("controls")
    grant_crud("controls")

    # -- control_requirements ---------------------------------------------------
    op.create_table(
        "control_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("control_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_control_requirements__tenant_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["control_id"],
            ["controls.id"],
            name=op.f("fk_control_requirements__control_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["requirements.id"],
            name=op.f("fk_control_requirements__requirement_id"),
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "tenant_id", "control_id", "requirement_id", name="uq_control_requirements"
        ),
    )
    op.create_index(
        "ix_control_requirements__tenant_id_requirement_id",
        "control_requirements",
        ["tenant_id", "requirement_id"],
    )
    op.create_index(
        "ix_control_requirements__tenant_id_control_id",
        "control_requirements",
        ["tenant_id", "control_id"],
    )
    enable_rls("control_requirements")
    grant_crud("control_requirements")


def downgrade() -> None:
    op.drop_table("control_requirements")
    op.drop_table("controls")

    op.drop_constraint("control_sub_type_valid", "control_templates", type_="check")
    op.drop_constraint("control_type_valid", "control_templates", type_="check")
    op.drop_constraint("category_valid", "control_templates", type_="check")
    # Back to D1: Type mirrors Category, Sub-type is null and unconstrained.
    op.execute("UPDATE control_templates SET control_type = category, control_sub_type = NULL")
    op.create_check_constraint(
        "control_type_valid",
        "control_templates",
        _in_list("control_type", CONTROL_CATEGORIES),
    )
