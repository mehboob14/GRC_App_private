"""Regulation decisions: the workspace's own call on each law the country panel shows.

Phase 6 of the guided onboarding change (task 6.4; JC-6, J5). Tenant owned, forced RLS in this
migration, amended in place and audited; the app role gets no DELETE.

Revision ID: 8a4f2c6e1b37
Revises: 5d1e7c3b9a24
Create Date: 2026-11-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.db.rls import disable_rls, enable_rls, grant_crud, revoke_delete

revision: str = "8a4f2c6e1b37"
down_revision: str | None = "5d1e7c3b9a24"
branch_labels: str | None = None
depends_on: str | None = None

_UUID = postgresql.UUID(as_uuid=True)
_T = "regulation_decisions"


def upgrade() -> None:
    op.create_table(
        _T,
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("regulation_key", sa.Text(), nullable=False),
        sa.Column("relevance", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("decided_by_membership_id", _UUID, nullable=True),
        sa.Column("register_row_added_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("profile_version", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{_T}__tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["decided_by_membership_id"],
            ["tenant_memberships.id"],
            ondelete="SET NULL",
            name=f"fk_{_T}__decided_by_membership_id",
        ),
        sa.CheckConstraint(
            "relevance IN ('relevant', 'not_relevant')", name=op.f(f"ck_{_T}__relevance_valid")
        ),
    )
    op.create_index(
        f"uq_{_T}__tenant_id_regulation_key", _T, ["tenant_id", "regulation_key"], unique=True
    )
    enable_rls(_T)
    grant_crud(_T)
    revoke_delete(_T)


def downgrade() -> None:
    disable_rls(_T)
    op.drop_table(_T)
