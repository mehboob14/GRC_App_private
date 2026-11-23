"""Suggestions, baseline, readiness snapshots, setup state and Statement of Applicability versions.

Phase 5 of the guided onboarding change (tasks 5.3, 5.6, 5.8, 5.12). All tenant owned, forced
RLS in this migration. ``onboarding_proposal_decisions``, ``baselines``, ``baseline_answers`` and
``onboarding_state`` are amended in place and audited (no DELETE grant). ``readiness_snapshots``
and ``applicability_versions`` are append only.

Revision ID: 5d1e7c3b9a24
Revises: 9bc3f6a9db0c
Create Date: 2026-11-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.db.rls import (
    disable_rls,
    drop_append_only,
    enable_rls,
    grant_crud,
    make_append_only,
    revoke_delete,
)

revision: str = "5d1e7c3b9a24"
down_revision: str | None = "9bc3f6a9db0c"
branch_labels: str | None = None
depends_on: str | None = None

_UUID = postgresql.UUID(as_uuid=True)
_JSONB = postgresql.JSONB()


def _base(table: str) -> list[sa.SchemaItem]:
    return [
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{table}__tenant_id"
        ),
    ]


def _member(table: str, column: str) -> list[sa.SchemaItem]:
    return [
        sa.Column(column, _UUID, nullable=True),
        sa.ForeignKeyConstraint(
            [column], ["tenant_memberships.id"], ondelete="SET NULL", name=f"fk_{table}__{column}"
        ),
    ]


def upgrade() -> None:
    t = "onboarding_proposal_decisions"
    op.create_table(
        t,
        *_base(t),
        sa.Column("dedupe_key", sa.Text(), nullable=False),
        sa.Column("rule_key", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("subject_key", sa.Text(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("payload", _JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("because", sa.Text(), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=True),
        *_member(t, "decided_by_membership_id"),
        sa.CheckConstraint(
            "decision IN ('accepted', 'rejected')", name=op.f(f"ck_{t}__decision_valid")
        ),
        sa.CheckConstraint(
            "kind IN ('control_status', 'iso_applicability', 'soc2_category')",
            name=op.f(f"ck_{t}__kind_valid"),
        ),
        sa.CheckConstraint("length(btrim(reason)) > 0", name=op.f(f"ck_{t}__reason_present")),
    )
    op.create_index(f"uq_{t}__tenant_id_dedupe_key", t, ["tenant_id", "dedupe_key"], unique=True)

    t = "baselines"
    op.create_table(
        t,
        *_base(t),
        *_member(t, "taken_by_membership_id"),
        sa.Column("status", sa.Text(), server_default=sa.text("'open'"), nullable=False),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('open', 'complete')", name=op.f(f"ck_{t}__status_valid")),
    )
    op.create_index(
        f"uq_{t}__tenant_id_open",
        t,
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )

    t = "baseline_answers"
    op.create_table(
        t,
        *_base(t),
        sa.Column("baseline_id", _UUID, nullable=False),
        sa.Column("control_id", _UUID, nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        *_member(t, "answered_by_membership_id"),
        sa.ForeignKeyConstraint(
            ["baseline_id"], ["baselines.id"], ondelete="CASCADE", name=f"fk_{t}__baseline_id"
        ),
        sa.ForeignKeyConstraint(
            ["control_id"], ["controls.id"], ondelete="CASCADE", name=f"fk_{t}__control_id"
        ),
        sa.CheckConstraint(
            "answer IN ('in_place', 'partly', 'not_in_place', 'not_sure')",
            name=op.f(f"ck_{t}__answer_valid"),
        ),
    )
    op.create_index(
        f"uq_{t}__tenant_id_baseline_id_control_id",
        t,
        ["tenant_id", "baseline_id", "control_id"],
        unique=True,
    )

    t = "readiness_snapshots"
    op.create_table(
        t,
        *_base(t),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("figures", _JSONB, nullable=False),
    )
    op.create_index(f"ix_{t}__tenant_id_created_at", t, ["tenant_id", "created_at"])

    t = "onboarding_state"
    op.create_table(
        t,
        *_base(t),
        sa.Column("start_point", sa.Text(), nullable=True),
        sa.Column("setup_step", sa.Text(), nullable=True),
        sa.Column("setup_completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "start_point IS NULL OR start_point IN ('fresh', 'existing')",
            name=op.f(f"ck_{t}__start_point_valid"),
        ),
    )
    op.create_index(f"uq_{t}__tenant_id", t, ["tenant_id"], unique=True)

    t = "applicability_versions"
    op.create_table(
        t,
        *_base(t),
        sa.Column("framework_id", _UUID, nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("framework_version", sa.Text(), nullable=False),
        sa.Column("scope_statement", sa.Text(), nullable=True),
        sa.Column("rows", _JSONB, nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        *_member(t, "approved_by_membership_id"),
        sa.ForeignKeyConstraint(
            ["framework_id"], ["frameworks.id"], ondelete="RESTRICT", name=f"fk_{t}__framework_id"
        ),
        sa.CheckConstraint("number > 0", name=op.f(f"ck_{t}__number_positive")),
    )
    op.create_index(
        f"uq_{t}__tenant_id_framework_id_number",
        t,
        ["tenant_id", "framework_id", "number"],
        unique=True,
    )

    for table in (
        "onboarding_proposal_decisions",
        "baselines",
        "baseline_answers",
        "onboarding_state",
    ):
        enable_rls(table)
        grant_crud(table)
        revoke_delete(table)
    for table in ("readiness_snapshots", "applicability_versions"):
        enable_rls(table)
        grant_crud(table)
        make_append_only(table)


def downgrade() -> None:
    for table in ("applicability_versions", "readiness_snapshots"):
        drop_append_only(table)
    for table in (
        "applicability_versions",
        "onboarding_state",
        "readiness_snapshots",
        "baseline_answers",
        "baselines",
        "onboarding_proposal_decisions",
    ):
        disable_rls(table)
        op.drop_table(table)
