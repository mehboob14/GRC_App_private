"""Assessment objectives: not applicable decisions and evidence tagged to artifacts.

Guided onboarding content package O1 (AO-1 to AO-4). Both tables are tenant owned with forced
RLS in this migration, amended in place and audited; the app role gets no DELETE.

Revision ID: 7e2b4d9c1f53
Revises: 2c7d9e4f6a18
Create Date: 2026-11-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.db.rls import disable_rls, enable_rls, grant_crud, revoke_delete

revision: str = "7e2b4d9c1f53"
down_revision: str | None = "2c7d9e4f6a18"
branch_labels: str | None = None
depends_on: str | None = None

_UUID = postgresql.UUID(as_uuid=True)


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
    t = "objective_decisions"
    op.create_table(
        t,
        *_base(t),
        sa.Column("objective_code", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        *_member(t, "decided_by_membership_id"),
        sa.Column("withdrawn_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_member(t, "withdrawn_by_membership_id"),
        sa.CheckConstraint("length(btrim(reason)) > 0", name=op.f(f"ck_{t}__reason_present")),
    )
    op.create_index(
        f"uq_{t}__tenant_id_objective_code_open",
        t,
        ["tenant_id", "objective_code"],
        unique=True,
        postgresql_where=sa.text("withdrawn_at IS NULL"),
    )

    t = "evidence_artifacts"
    op.create_table(
        t,
        *_base(t),
        sa.Column("evidence_id", _UUID, nullable=False),
        sa.Column("artifact_key", sa.Text(), nullable=False),
        *_member(t, "tagged_by_membership_id"),
        sa.Column("removed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["evidence_id"], ["evidence.id"], ondelete="CASCADE", name=f"fk_{t}__evidence_id"
        ),
    )
    op.create_index(
        f"uq_{t}__tenant_id_evidence_id_artifact_key_open",
        t,
        ["tenant_id", "evidence_id", "artifact_key"],
        unique=True,
        postgresql_where=sa.text("removed_at IS NULL"),
    )
    op.create_index(f"ix_{t}__tenant_id_artifact_key", t, ["tenant_id", "artifact_key"])

    for table in ("objective_decisions", "evidence_artifacts"):
        enable_rls(table)
        grant_crud(table)
        revoke_delete(table)


def downgrade() -> None:
    for table in ("evidence_artifacts", "objective_decisions"):
        disable_rls(table)
        op.drop_table(table)
