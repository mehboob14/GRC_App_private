"""Scope: one shared list of items, in or out decided per framework.

Phase 3 of the guided onboarding change (task 3.6; requirements SC-0, SC-2; decision D-6,
checked against AICPA and ISO accreditation sources on 2026-11-21). ``scope_items`` is the
workspace's list of services, legal entities, sites, environments, systems, vendors, people
groups and data types. ``scope_decisions`` records, per item and per engagement, whether it is
in or out and why. The in or out flag is never shared between frameworks, because a SOC 2 report
describes one system while an ISO 27001 scope is often wider.

Both tables are tenant owned with forced RLS in this migration. Neither row is ever deleted:
items are retired with a reason, decisions are updated and every change is audited, so the app
role gets no DELETE. ``scope_items`` carries ``source``, ``external_id`` and ``synced_at`` (rule 9).

Revision ID: af53b58da5b3
Revises: 6b8df681a7aa
Create Date: 2026-11-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.db.rls import disable_rls, enable_rls, grant_crud, revoke_delete

revision: str = "af53b58da5b3"
down_revision: str | None = "6b8df681a7aa"
branch_labels: str | None = None
depends_on: str | None = None

_UUID = postgresql.UUID(as_uuid=True)
_MEMBERSHIPS = "tenant_memberships.id"
_KINDS = (
    "service",
    "legal_entity",
    "site",
    "environment",
    "system",
    "vendor",
    "people_group",
    "data_type",
)


def _ts() -> tuple[sa.Column, sa.Column]:  # type: ignore[type-arg]
    return (
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def upgrade() -> None:
    op.create_table(
        "scope_items",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("ref_type", sa.Text(), nullable=True),
        sa.Column("ref_id", _UUID, nullable=True),
        sa.Column("origin", sa.Text(), server_default=sa.text("'manual'"), nullable=False),
        sa.Column("retired_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("retired_reason", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), server_default=sa.text("'manual'"), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name="fk_scope_items__tenant_id"
        ),
        sa.CheckConstraint(_in("kind", _KINDS), name=op.f("ck_scope_items__kind_valid")),
        sa.CheckConstraint(
            "ref_type IS NULL OR ref_type IN ('asset', 'vendor', 'group')",
            name=op.f("ck_scope_items__ref_type_valid"),
        ),
        sa.CheckConstraint(
            "(ref_type IS NULL) = (ref_id IS NULL)", name=op.f("ck_scope_items__ref_pair")
        ),
        sa.CheckConstraint(
            "retired_at IS NULL OR length(btrim(coalesce(retired_reason, ''))) > 0",
            name=op.f("ck_scope_items__retired_with_reason"),
        ),
        sa.CheckConstraint(
            _in("origin", ("manual", "suggested")), name=op.f("ck_scope_items__origin_valid")
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "source",
            "external_id",
            name="uq_scope_items__tenant_id_source_external_id",
        ),
    )
    op.create_index(
        "uq_scope_items__tenant_id_ref_type_ref_id",
        "scope_items",
        ["tenant_id", "ref_type", "ref_id"],
        unique=True,
        postgresql_where=sa.text("ref_id IS NOT NULL"),
    )
    enable_rls("scope_items")
    grant_crud("scope_items")
    revoke_delete("scope_items")

    op.create_table(
        "scope_decisions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("scope_item_id", _UUID, nullable=False),
        sa.Column("engagement_id", _UUID, nullable=False),
        sa.Column("in_scope", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("decided_by_membership_id", _UUID, nullable=True),
        sa.Column("decided_at", sa.TIMESTAMP(timezone=True), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name="fk_scope_decisions__tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["scope_item_id"],
            ["scope_items.id"],
            ondelete="RESTRICT",
            name="fk_scope_decisions__scope_item_id",
        ),
        sa.ForeignKeyConstraint(
            ["engagement_id"],
            ["engagements.id"],
            ondelete="RESTRICT",
            name="fk_scope_decisions__engagement_id",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by_membership_id"],
            [_MEMBERSHIPS],
            ondelete="SET NULL",
            name="fk_scope_decisions__decided_by_membership_id",
        ),
        sa.CheckConstraint(
            "in_scope OR length(btrim(coalesce(reason, ''))) > 0",
            name=op.f("ck_scope_decisions__out_needs_reason"),
        ),
    )
    op.create_index(
        "uq_scope_decisions__tenant_id_scope_item_id_engagement_id",
        "scope_decisions",
        ["tenant_id", "scope_item_id", "engagement_id"],
        unique=True,
    )
    op.create_index(
        "ix_scope_decisions__tenant_id_engagement_id",
        "scope_decisions",
        ["tenant_id", "engagement_id"],
    )
    enable_rls("scope_decisions")
    grant_crud("scope_decisions")
    revoke_delete("scope_decisions")


def downgrade() -> None:
    disable_rls("scope_decisions")
    op.drop_table("scope_decisions")
    disable_rls("scope_items")
    op.drop_table("scope_items")
