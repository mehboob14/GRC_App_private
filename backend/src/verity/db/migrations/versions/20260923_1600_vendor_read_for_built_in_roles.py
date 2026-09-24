"""The built-in roles can see the vendor register.

Week 5 shipped the four ``vendors:*`` keys and granted none of them to the roles
every tenant starts with, so a Security Officer opening Vendors saw nothing until
an admin edited their role. Reading the register is the least a person
accountable for security, privacy or spend needs, and it matches what those roles
already hold elsewhere: read their area, change nothing.

The three write keys stay off. ``vendors:assess``, ``:manage`` and ``:approve``
are granted deliberately, in the Roles screen, because approving a vendor is a
signature.

Revision ID: 9f2d1a7c6b40
Revises: 5c93b7e2a481
Create Date: 2026-09-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "9f2d1a7c6b40"
down_revision: str | None = "5c93b7e2a481"
branch_labels: str | None = None
depends_on: str | None = None

_ROLES = ("Security Officer", "Privacy Officer", "Business Operations/Finance Lead")
_KEY = "vendors:read"


def _unforced(table: str, statement: sa.TextClause) -> None:
    """Run a data statement as the owner past FORCE RLS, which would otherwise
    filter every row out of an owner session with no tenant bound."""
    op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.execute(statement)
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    _unforced(
        "role_permissions",
        sa.text(
            "INSERT INTO role_permissions (role_id, permission_key) "
            "SELECT r.id, :key FROM roles r "
            "WHERE r.built_in AND r.name = ANY(:names) ON CONFLICT DO NOTHING"
        ).bindparams(key=_KEY, names=list(_ROLES)),
    )


def downgrade() -> None:
    _unforced(
        "role_permissions",
        sa.text(
            "DELETE FROM role_permissions rp USING roles r "
            "WHERE rp.role_id = r.id AND rp.permission_key = :key "
            "AND r.built_in AND r.name = ANY(:names)"
        ).bindparams(key=_KEY, names=list(_ROLES)),
    )
