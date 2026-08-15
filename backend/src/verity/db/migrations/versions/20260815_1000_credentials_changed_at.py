"""credentials changed-at (session revocation primitive)

Revision ID: c3f9a1b4e2d8
Revises: b8e2a6d1c4f7
Create Date: 2026-08-15 10:00:00.000000

Adds ``credentials.credentials_changed_at``: bumped to now() on every password
change/reset. Session validation rejects any session token issued before this
instant, which is how a stateless-JWT session gets revoked and how a
password-reset link becomes single-use. ``credentials`` is a global identity
table (no tenant_id, no RLS), so this is a plain nullable column add.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3f9a1b4e2d8"
down_revision: str | None = "b8e2a6d1c4f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "credentials",
        sa.Column(
            "credentials_changed_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("credentials", "credentials_changed_at")
