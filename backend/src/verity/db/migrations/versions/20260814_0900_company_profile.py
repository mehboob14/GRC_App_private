"""company profile

Revision ID: a1c7f3b2e9d4
Revises: 52ee27860d9e
Create Date: 2026-08-14 09:00:00.000000

The tenant's self-maintained organisation profile (name, industry, website,
description, company size, privacy/terms URLs, …). Tenant-owned with the
standard tenant policy plus a provider SELECT policy, so a provider read can
see it in the provider-plane scope. Seeds the ``tenant:manage`` permission
(Admin holds it via "every key that exists"). Downgrade drops the table (its
policies go with it) and the permission.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.db.rls import enable_rls, grant_crud

revision: str = "a1c7f3b2e9d4"
down_revision: str | None = "52ee27860d9e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PROVIDER_SELECT = "NULLIF(current_setting('app.provider_plane', true), '') = 'on'"

_TEXT_COLUMNS = (
    "legal_name",
    "display_name",
    "registration_number",
    "industry",
    "company_size",
    "description",
    "website",
    "domain",
    "headquarters",
    "regulatory_scope",
    "privacy_policy_url",
    "terms_url",
)


def upgrade() -> None:
    op.create_table(
        "company_profile",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        *[sa.Column(name, sa.Text(), nullable=True) for name in _TEXT_COLUMNS],
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
            name=op.f("fk_company_profile__tenant_id"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("tenant_id", name=op.f("pk_company_profile")),
    )
    enable_rls("company_profile")  # ENABLE + FORCE + tenant policy (USING/WITH CHECK)
    grant_crud("company_profile")
    op.execute(
        sa.text(
            "CREATE POLICY company_profile_provider_select ON company_profile "
            f"FOR SELECT USING ({_PROVIDER_SELECT})"
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO permissions (key, module, action) "
            "VALUES ('tenant:manage', 'tenant', 'manage') ON CONFLICT (key) DO NOTHING"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM permissions WHERE key = 'tenant:manage'"))
    op.drop_table("company_profile")
