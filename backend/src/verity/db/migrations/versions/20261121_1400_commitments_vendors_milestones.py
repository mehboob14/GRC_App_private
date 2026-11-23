"""Commitments, vendors that count per audit, milestones, engagement history, framework retirement.

Phase 3 of the guided onboarding change (tasks 3.1, 3.4, 3.6; requirements EN-1, EN-4, FS-6,
SC-8, SC-9).

* ``commitments``: what the company promises customers and where it is written (SC-8). Read by
  the SOC 2 description (principal service commitments) and the ISO context register.
* ``engagement_vendors``: a vendor marked for one audit, as a SOC 2 subservice organisation
  (carve out or included) or an ISO supplier inside the scope's dependencies (SC-9).
* ``engagement_milestones``: the dated plan of one audit, planned and actual (EN-4).
* ``engagements.is_current``: an engagement is one cycle; earlier cycles stay readable (EN-1).
  The old one per framework version uniqueness becomes one current engagement per framework
  version.
* ``tenant_frameworks``: who turned a framework off, when and why (FS-6).

All new tables are tenant owned, forced RLS in this migration, no DELETE grant (rows are retired
or stamped, never removed).

Revision ID: 438b8c525629
Revises: af53b58da5b3
Create Date: 2026-11-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.db.rls import disable_rls, enable_rls, grant_crud, revoke_delete

revision: str = "438b8c525629"
down_revision: str | None = "af53b58da5b3"
branch_labels: str | None = None
depends_on: str | None = None

_UUID = postgresql.UUID(as_uuid=True)
_MEMBERSHIPS = "tenant_memberships.id"


def _ts() -> tuple[sa.Column, sa.Column]:  # type: ignore[type-arg]
    return (
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def _tenant_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{table}__tenant_id"
    )


def _secure(table: str) -> None:
    enable_rls(table)
    grant_crud(table)
    revoke_delete(table)


def upgrade() -> None:
    # -- commitments -------------------------------------------------------------
    op.create_table(
        "commitments",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column(
            "points_at", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False
        ),
        sa.Column("owner_membership_id", _UUID, nullable=True),
        sa.Column("retired_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("retired_reason", sa.Text(), nullable=True),
        *_ts(),
        _tenant_fk("commitments"),
        sa.ForeignKeyConstraint(
            ["owner_membership_id"],
            [_MEMBERSHIPS],
            ondelete="SET NULL",
            name="fk_commitments__owner_membership_id",
        ),
        sa.CheckConstraint(
            "source_kind IN ('contract', 'service_levels', 'privacy_notice', 'website', 'other')",
            name=op.f("ck_commitments__source_kind_valid"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(points_at) = 'array'", name=op.f("ck_commitments__points_at_array")
        ),
        sa.CheckConstraint(
            "retired_at IS NULL OR length(btrim(coalesce(retired_reason, ''))) > 0",
            name=op.f("ck_commitments__retired_with_reason"),
        ),
    )
    op.create_index(
        "ix_commitments__tenant_id_created_at", "commitments", ["tenant_id", "created_at"]
    )
    _secure("commitments")

    # -- engagement_vendors ----------------------------------------------------------
    op.create_table(
        "engagement_vendors",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("engagement_id", _UUID, nullable=False),
        sa.Column("vendor_id", _UUID, nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("method", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("removed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("removed_reason", sa.Text(), nullable=True),
        *_ts(),
        _tenant_fk("engagement_vendors"),
        sa.ForeignKeyConstraint(
            ["engagement_id"],
            ["engagements.id"],
            ondelete="RESTRICT",
            name="fk_engagement_vendors__engagement_id",
        ),
        sa.ForeignKeyConstraint(
            ["vendor_id"],
            ["vendors.id"],
            ondelete="RESTRICT",
            name="fk_engagement_vendors__vendor_id",
        ),
        sa.CheckConstraint(
            "role IN ('subservice', 'supplier')", name=op.f("ck_engagement_vendors__role_valid")
        ),
        sa.CheckConstraint(
            "method IS NULL OR method IN ('carve_out', 'included')",
            name=op.f("ck_engagement_vendors__method_valid"),
        ),
        sa.CheckConstraint(
            "(role = 'subservice') = (method IS NOT NULL)",
            name=op.f("ck_engagement_vendors__method_for_subservice"),
        ),
    )
    op.create_index(
        "uq_engagement_vendors__tenant_id_engagement_id_vendor_id",
        "engagement_vendors",
        ["tenant_id", "engagement_id", "vendor_id"],
        unique=True,
    )
    _secure("engagement_vendors")

    # -- engagement_milestones ------------------------------------------------------------
    op.create_table(
        "engagement_milestones",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("engagement_id", _UUID, nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("planned_on", sa.Date(), nullable=True),
        sa.Column("actual_on", sa.Date(), nullable=True),
        *_ts(),
        _tenant_fk("engagement_milestones"),
        sa.ForeignKeyConstraint(
            ["engagement_id"],
            ["engagements.id"],
            ondelete="RESTRICT",
            name="fk_engagement_milestones__engagement_id",
        ),
    )
    op.create_index(
        "uq_engagement_milestones__tenant_id_engagement_id_kind",
        "engagement_milestones",
        ["tenant_id", "engagement_id", "kind"],
        unique=True,
    )
    _secure("engagement_milestones")

    # -- engagement history -------------------------------------------------------------------
    op.add_column(
        "engagements",
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.drop_constraint("uq_engagements__tenant_framework_version", "engagements", type_="unique")
    op.create_index(
        "uq_engagements__tenant_id_framework_version_id_current",
        "engagements",
        ["tenant_id", "framework_version_id"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )

    # -- framework retirement -----------------------------------------------------------------
    op.add_column("tenant_frameworks", sa.Column("deactivated_reason", sa.Text(), nullable=True))
    op.add_column(
        "tenant_frameworks", sa.Column("deactivated_at", sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.add_column(
        "tenant_frameworks", sa.Column("deactivated_by_membership_id", _UUID, nullable=True)
    )
    op.create_foreign_key(
        "fk_tenant_frameworks__deactivated_by_membership_id",
        "tenant_frameworks",
        "tenant_memberships",
        ["deactivated_by_membership_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_tenant_frameworks__deactivated_by_membership_id",
        "tenant_frameworks",
        type_="foreignkey",
    )
    for column in ("deactivated_by_membership_id", "deactivated_at", "deactivated_reason"):
        op.drop_column("tenant_frameworks", column)
    op.drop_index(
        "uq_engagements__tenant_id_framework_version_id_current", table_name="engagements"
    )
    # Only safe while every framework version has a single engagement (no second cycle yet).
    op.create_unique_constraint(
        "uq_engagements__tenant_framework_version",
        "engagements",
        ["tenant_id", "framework_version_id"],
    )
    op.drop_column("engagements", "is_current")
    for table in ("engagement_milestones", "engagement_vendors", "commitments"):
        disable_rls(table)
        op.drop_table(table)
