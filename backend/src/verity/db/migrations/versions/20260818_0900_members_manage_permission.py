"""seed the members:manage permission

Revision ID: a4c8e2f60b13
Revises: f3b7c1d9a204
Create Date: 2026-08-18 09:00:00.000000

Editing a member's details is its own capability. The existing member keys read
as lifecycle steps — ``members:invite`` adds a person, ``members:disable``
removes them — and neither implies "may correct someone's name", so renaming
gets a key of its own rather than being smuggled onto one of those.

Admin holds it automatically: the built-in Admin role resolves to "every key
that exists" at check time, so no role bundle changes here. The same shape as
``security:manage`` (20260813_1616).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a4c8e2f60b13"
down_revision: str | None = "f3b7c1d9a204"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO permissions (key, module, action) "
            "VALUES ('members:manage', 'members', 'manage') ON CONFLICT (key) DO NOTHING"
        )
    )


def downgrade() -> None:
    # role_permissions rows referencing it go first, or the FK refuses the delete.
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_key = 'members:manage'"
        )
    )
    op.execute(sa.text("DELETE FROM permissions WHERE key = 'members:manage'"))
