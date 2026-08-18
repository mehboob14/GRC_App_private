"""descriptions on roles and groups (D16)

Revision ID: e2a7b93c15d8
Revises: d1f4c8a9b370
Create Date: 2026-08-17 10:00:00.000000

A name alone does not say what a role is for. "Control Owner" tells an
administrator deciding who should hold it almost nothing, so both roles and
groups gain a free-text description.

Nullable rather than defaulted: the roles seeded before this migration have no
description, and inventing one for them would put words in the client's mouth.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e2a7b93c15d8"
down_revision: str | None = "d1f4c8a9b370"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("roles", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("groups", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("groups", "description")
    op.drop_column("roles", "description")
