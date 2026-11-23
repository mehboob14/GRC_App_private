"""A workspace's single sign on through Keycloak: organization, domains, enforcement.

openspec/changes/add-keycloak-sso phase B, ADR-0015. Tenant owned with forced RLS, plus a SELECT
policy for the provider plane, because sign in reads it before a tenant is known (the
``tenant_settings`` pattern). Amended in place and audited; the app role gets no DELETE.

``organization_alias`` is unique across tenants on purpose (one Keycloak organization is one
workspace), so its index does not lead with ``tenant_id``.

Revision ID: 4b8e1d6a9c27
Revises: 7e2b4d9c1f53
Create Date: 2026-11-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.db.rls import disable_rls, enable_rls, grant_crud, revoke_delete

revision: str = "4b8e1d6a9c27"
down_revision: str | None = "7e2b4d9c1f53"
branch_labels: str | None = None
depends_on: str | None = None

_T = "tenant_sso"
_UUID = postgresql.UUID(as_uuid=True)
_PROVIDER_SELECT = "NULLIF(current_setting('app.provider_plane', true), '') = 'on'"


def upgrade() -> None:
    op.create_table(
        _T,
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("organization_alias", sa.Text(), nullable=False),
        sa.Column(
            "domains",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("enforce", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("jit_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("default_role_id", _UUID, nullable=True),
        sa.Column("verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
            ["default_role_id"], ["roles.id"], ondelete="SET NULL", name=f"fk_{_T}__default_role_id"
        ),
        sa.CheckConstraint(
            "organization_alias ~ '^[a-z0-9][a-z0-9_-]{1,62}$'",
            name=op.f(f"ck_{_T}__organization_alias_format"),
        ),
        sa.CheckConstraint(
            "NOT enforce OR (enabled AND verified_at IS NOT NULL)",
            name=op.f(f"ck_{_T}__enforce_needs_a_verified_sign_in"),
        ),
        sa.UniqueConstraint("tenant_id", name=f"uq_{_T}__tenant_id"),
        sa.UniqueConstraint("organization_alias", name=f"uq_{_T}__organization_alias"),
    )
    enable_rls(_T)
    grant_crud(_T)
    revoke_delete(_T)
    op.execute(
        sa.text(f"CREATE POLICY {_T}_provider_select ON {_T} FOR SELECT USING ({_PROVIDER_SELECT})")
    )


def downgrade() -> None:
    op.execute(sa.text(f"DROP POLICY IF EXISTS {_T}_provider_select ON {_T}"))
    disable_rls(_T)
    op.drop_table(_T)
