"""vulnerabilities — remediation plans (one audited fix plan per finding)

Revision ID: e2a5c7d93f42
Revises: d1f4a6b82c31
Create Date: 2026-09-02 14:00:00.000000

One tenant-owned, RLS-forced table (rules 1, 2, 12): a generated/approvable/
verifiable remediation plan, 1:1 with a vuln_instance. Closure still routes
through the instance state machine; this records the fix trail (who approved,
when applied, what verified it). The executor is simulated (rule 11 AI draft).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.db.rls import disable_rls, enable_rls, grant_crud

revision: str = "e2a5c7d93f42"
down_revision: str | None = "d1f4a6b82c31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FIX_TYPES = ("patch", "config", "script", "mitigation")
PLAN_STATUSES = ("recommended", "approved", "applied", "verified", "failed", "cancelled")

_UUID = postgresql.UUID(as_uuid=True)


def _check(column: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    joined = ", ".join(f"'{v}'" for v in values)
    return sa.CheckConstraint(
        f"{column} IN ({joined})", name=conv(f"ck_vuln_remediation_plans__{column}_valid")
    )


def upgrade() -> None:
    op.create_table(
        "vuln_remediation_plans",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("instance_id", _UUID, nullable=False),
        sa.Column("fix_type", sa.Text(), nullable=False, server_default="patch"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("fix_artifact", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("rollback_plan", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False, server_default="heuristic"),
        sa.Column("status", sa.Text(), nullable=False, server_default="recommended"),
        sa.Column(
            "triggers", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column("risk_score_before", sa.Float(), nullable=True),
        sa.Column("risk_score_after", sa.Float(), nullable=True),
        sa.Column("change_window_start", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("change_window_end", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("approved_by_membership_id", _UUID, nullable=True),
        sa.Column("approved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("applied_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("execution_log", sa.Text(), nullable=True),
        sa.Column("verification_evidence", sa.Text(), nullable=True),
        sa.Column("verified_by_membership_id", _UUID, nullable=True),
        sa.Column("verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("cancelled_reason", sa.Text(), nullable=True),
        sa.Column("cancelled_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
            name="fk_vuln_remediation_plans__tenant_id",
        ),
        sa.ForeignKeyConstraint(
            ["instance_id"],
            ["vuln_instances.id"],
            ondelete="CASCADE",
            name="fk_vuln_remediation_plans__instance_id",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_membership_id"],
            ["tenant_memberships.id"],
            ondelete="SET NULL",
            name="fk_vuln_remediation_plans__approved_by_membership_id",
        ),
        sa.ForeignKeyConstraint(
            ["verified_by_membership_id"],
            ["tenant_memberships.id"],
            ondelete="SET NULL",
            name="fk_vuln_remediation_plans__verified_by_membership_id",
        ),
        _check("fix_type", FIX_TYPES),
        _check("status", PLAN_STATUSES),
        sa.UniqueConstraint("tenant_id", "instance_id", name="uq_vuln_remediation_plans__instance"),
    )
    op.create_index(
        "ix_vuln_remediation_plans__tenant_id_instance_id",
        "vuln_remediation_plans",
        ["tenant_id", "instance_id"],
    )
    enable_rls("vuln_remediation_plans")
    grant_crud("vuln_remediation_plans")


def downgrade() -> None:
    disable_rls("vuln_remediation_plans")
    op.drop_table("vuln_remediation_plans")
