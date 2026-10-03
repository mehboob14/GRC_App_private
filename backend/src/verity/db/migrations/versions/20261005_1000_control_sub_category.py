"""The Sub-type column on control templates.

The signed spec gives every control a Type and a Sub-type. Type is the existing
``category``; Sub-type is ``sub_category``, a finer area inside it (CI/CD under
Development, for example). ``controls.sub_category`` has existed since
20260823_1100; the shipped templates had nowhere to carry it. Only the column is
added here. The values are shipped content and a later migration backfills the
controls a workspace already adopted.

Revision ID: d5c2e8a41f07
Revises: a7d3f19e2c58
Create Date: 2026-10-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "d5c2e8a41f07"
down_revision: str | None = "a7d3f19e2c58"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("control_templates", sa.Column("sub_category", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("control_templates", "sub_category")
