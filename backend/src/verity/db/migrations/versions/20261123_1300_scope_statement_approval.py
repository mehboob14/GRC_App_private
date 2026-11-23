"""Scope statement approval and its AI draft mark (guided onboarding EN-11, AI-2).

Three nullable or defaulted columns on ``engagements``; no new table, RLS unchanged.

Revision ID: 3f6a8c2d7e91
Revises: 4b8e1d6a9c27
Create Date: 2026-11-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "3f6a8c2d7e91"
down_revision: str | None = "4b8e1d6a9c27"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "engagements",
        sa.Column(
            "scope_statement_ai", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    )
    op.add_column(
        "engagements",
        sa.Column("scope_statement_approved_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "engagements",
        sa.Column(
            "scope_statement_approved_by_membership_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_engagements__scope_statement_approved_by_membership_id",
        "engagements",
        "tenant_memberships",
        ["scope_statement_approved_by_membership_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_engagements__scope_statement_approved_by_membership_id",
        "engagements",
        type_="foreignkey",
    )
    op.drop_column("engagements", "scope_statement_approved_by_membership_id")
    op.drop_column("engagements", "scope_statement_approved_at")
    op.drop_column("engagements", "scope_statement_ai")
