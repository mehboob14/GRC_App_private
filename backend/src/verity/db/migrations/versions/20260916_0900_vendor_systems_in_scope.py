"""vendors: systems in scope

The requirements' vendor register records "data and scope (tier, data
classification, data types, systems in scope)". Data types were there; the
systems of ours a vendor touches were not. One JSONB list of names on
``vendors``, empty for every existing row. The table already has its RLS policy,
and a new column needs no grant.

Revision ID: c4e1a7d9b203
Revises: b6d2e8f41a37
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4e1a7d9b203"
down_revision: str | None = "b6d2e8f41a37"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "vendors",
        sa.Column(
            "systems_in_scope",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("vendors", "systems_in_scope")
