"""Get Started: a person's decision to skip a step, with a reason.

Phase 1 of the guided onboarding change (openspec/changes/guided-onboarding, task 1.7).
Get Started computes every step's state from the records it counts and stores nothing
else, so this table holds only skips. Reopening a step stamps ``reopened_at``; the row is
kept as history, so the application role gets no DELETE.

Tenant owned: forced row level security in this migration (rule 1), ``tenant_id`` first in
the partial unique index that allows one open skip per step.

Revision ID: b9935aa647b2
Revises: f6c2b8e4a915
Create Date: 2026-11-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.db.rls import disable_rls, enable_rls, grant_crud, revoke_delete

revision: str = "b9935aa647b2"
down_revision: str | None = "f6c2b8e4a915"
branch_labels: str | None = None
depends_on: str | None = None

_UUID = postgresql.UUID(as_uuid=True)
_MEMBERSHIPS = "tenant_memberships.id"
_TABLE = "onboarding_step_skips"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("step_key", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("skipped_by_membership_id", _UUID, nullable=True),
        sa.Column("reopened_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("reopened_by_membership_id", _UUID, nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{_TABLE}__tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["skipped_by_membership_id"],
            [_MEMBERSHIPS],
            ondelete="SET NULL",
            name=f"fk_{_TABLE}__skipped_by_membership_id",
        ),
        sa.ForeignKeyConstraint(
            ["reopened_by_membership_id"],
            [_MEMBERSHIPS],
            ondelete="SET NULL",
            name=f"fk_{_TABLE}__reopened_by_membership_id",
        ),
        sa.CheckConstraint("length(btrim(reason)) > 0", name=op.f(f"ck_{_TABLE}__reason_present")),
    )
    op.create_index(
        f"uq_{_TABLE}__tenant_id_step_key_open",
        _TABLE,
        ["tenant_id", "step_key"],
        unique=True,
        postgresql_where=sa.text("reopened_at IS NULL"),
    )
    enable_rls(_TABLE)
    grant_crud(_TABLE)
    revoke_delete(_TABLE)


def downgrade() -> None:
    disable_rls(_TABLE)
    op.drop_table(_TABLE)
