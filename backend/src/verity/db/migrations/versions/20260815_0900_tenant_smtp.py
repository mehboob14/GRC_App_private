"""tenant smtp

Revision ID: b8e2a6d1c4f7
Revises: a1c7f3b2e9d4
Create Date: 2026-08-15 09:00:00.000000

Per-tenant outbound-email (SMTP) configuration, so a tenant can send from its
own mail server. Tenant-owned with the standard tenant policy plus a provider
SELECT policy. The password is application-layer ciphertext only —
envelope-encrypted AAD-bound to ``tenant_smtp:<tenant_id>`` before insert, never
returned. Reuses the ``tenant:manage`` permission (no new key). Downgrade drops
the table (its policies go with it).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.db.rls import enable_rls, grant_crud

revision: str = "b8e2a6d1c4f7"
down_revision: str | None = "a1c7f3b2e9d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PROVIDER_SELECT = "NULLIF(current_setting('app.provider_plane', true), '') = 'on'"


def upgrade() -> None:
    op.create_table(
        "tenant_smtp",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("host", sa.Text(), nullable=True),
        sa.Column("port", sa.Integer(), server_default=sa.text("587"), nullable=False),
        sa.Column("username", sa.Text(), nullable=True),
        # Application-layer ciphertext only, AAD-bound to 'tenant_smtp:<tenant_id>'.
        sa.Column("password_encrypted", sa.Text(), nullable=True),
        sa.Column("from_name", sa.Text(), nullable=True),
        sa.Column("from_address", sa.Text(), nullable=True),
        sa.Column("use_tls", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
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
            name=op.f("fk_tenant_smtp__tenant_id"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("tenant_id", name=op.f("pk_tenant_smtp")),
    )
    enable_rls("tenant_smtp")  # ENABLE + FORCE + tenant policy (USING/WITH CHECK)
    grant_crud("tenant_smtp")
    op.execute(
        sa.text(
            "CREATE POLICY tenant_smtp_provider_select ON tenant_smtp "
            f"FOR SELECT USING ({_PROVIDER_SELECT})"
        )
    )


def downgrade() -> None:
    op.drop_table("tenant_smtp")
