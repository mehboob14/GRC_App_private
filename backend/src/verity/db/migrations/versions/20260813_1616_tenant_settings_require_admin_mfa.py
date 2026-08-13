"""tenant settings require admin mfa

Revision ID: 52ee27860d9e
Revises: 68050122d7e5
Create Date: 2026-08-13 16:16:10.741708

Per-tenant auth policy (one bool: ``require_admin_mfa``, default off). Tenant-owned
with the standard tenant policy plus a provider SELECT policy so login can read it
across tenants in the provider-plane scope. Also seeds the ``security:manage``
permission (Admin holds it via "every key that exists"). Downgrade drops the table
(its policies go with it) and the permission.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.db.rls import enable_rls, grant_crud

revision: str = "52ee27860d9e"
down_revision: str | None = "68050122d7e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PROVIDER_SELECT = "NULLIF(current_setting('app.provider_plane', true), '') = 'on'"


def upgrade() -> None:
    op.create_table(
        "tenant_settings",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "require_admin_mfa", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_tenant_settings__tenant_id"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("tenant_id", name=op.f("pk_tenant_settings")),
    )
    enable_rls("tenant_settings")  # ENABLE + FORCE + tenant policy (USING/WITH CHECK)
    grant_crud("tenant_settings")
    op.execute(
        sa.text(
            "CREATE POLICY tenant_settings_provider_select ON tenant_settings "
            f"FOR SELECT USING ({_PROVIDER_SELECT})"
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO permissions (key, module, action) "
            "VALUES ('security:manage', 'security', 'manage') ON CONFLICT (key) DO NOTHING"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM permissions WHERE key = 'security:manage'"))
    op.drop_table("tenant_settings")
