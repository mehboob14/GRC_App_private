"""SSO lifecycle: session epoch, group to role map, sync markers.

openspec/changes/add-keycloak-sso phase D, ADR-0015 decision 4.

- ``users.sessions_revoked_at``: back-channel logout moves it forward; older sessions stop working.
- ``role_assignments.source``: 'sso_group' marks a role the directory sync granted, so it only ever
  takes back its own grants.
- ``tenant_sso.synced_at``: when the sync last read the organization.
- ``sso_group_roles``: tenant owned, forced RLS, policy in this migration (rule 12).

Revision ID: 5d2f8a1c7b63
Revises: 9c3e5a7b2d14
Create Date: 2026-11-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.db.rls import disable_rls, enable_rls, grant_crud

revision: str = "5d2f8a1c7b63"
down_revision: str | None = "9c3e5a7b2d14"
branch_labels: str | None = None
depends_on: str | None = None

_T = "sso_group_roles"
_UUID = postgresql.UUID(as_uuid=True)
_TS = sa.TIMESTAMP(timezone=True)


def upgrade() -> None:
    op.add_column("users", sa.Column("sessions_revoked_at", _TS, nullable=True))
    op.add_column("role_assignments", sa.Column("source", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_role_assignments__source_valid",
        "role_assignments",
        "source IS NULL OR source = 'sso_group'",
    )
    op.add_column("tenant_sso", sa.Column("synced_at", _TS, nullable=True))
    op.create_table(
        _T,
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("group_name", sa.Text(), nullable=False),
        sa.Column("role_id", _UUID, nullable=False),
        sa.Column("created_at", _TS, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", _TS, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{_T}__tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], ondelete="CASCADE", name=f"fk_{_T}__role_id"
        ),
        sa.CheckConstraint(
            "length(group_name) BETWEEN 1 AND 255", name=op.f(f"ck_{_T}__group_name_length")
        ),
        sa.UniqueConstraint(
            "tenant_id", "group_name", "role_id", name=f"uq_{_T}__tenant_id_group_role"
        ),
    )
    enable_rls(_T)
    grant_crud(_T)


def downgrade() -> None:
    disable_rls(_T)
    op.drop_table(_T)
    op.drop_column("tenant_sso", "synced_at")
    op.drop_constraint("ck_role_assignments__source_valid", "role_assignments", type_="check")
    op.drop_column("role_assignments", "source")
    op.drop_column("users", "sessions_revoked_at")
