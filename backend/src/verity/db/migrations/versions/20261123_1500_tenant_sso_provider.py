"""A workspace's identity provider in Keycloak, and proven domain ownership.

openspec/changes/add-keycloak-sso phase C. ``provider`` and ``idp_alias`` name the identity provider
Verity set up in Keycloak for the workspace; ``idp_alias`` is unique because an identity provider
serves one workspace. ``verified_domains`` are the domains a DNS TXT record carrying
``domain_token`` proved; only they route sign in.

Revision ID: 9c3e5a7b2d14
Revises: 3f6a8c2d7e91
Create Date: 2026-11-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9c3e5a7b2d14"
down_revision: str | None = "3f6a8c2d7e91"
branch_labels: str | None = None
depends_on: str | None = None

_T = "tenant_sso"


def upgrade() -> None:
    op.add_column(_T, sa.Column("provider", sa.Text(), nullable=True))
    op.add_column(_T, sa.Column("idp_alias", sa.Text(), nullable=True))
    op.add_column(
        _T,
        sa.Column(
            "verified_domains",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )
    op.add_column(
        _T,
        sa.Column(
            "domain_token",
            sa.Text(),
            server_default=sa.text("replace(gen_random_uuid()::text, '-', '')"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "provider_valid",
        _T,
        "provider IS NULL OR provider IN ('entra', 'okta', 'google', 'oidc', 'saml')",
    )
    op.create_unique_constraint(f"uq_{_T}__idp_alias", _T, ["idp_alias"])


def downgrade() -> None:
    op.drop_constraint(f"uq_{_T}__idp_alias", _T, type_="unique")
    op.drop_constraint(op.f(f"ck_{_T}__provider_valid"), _T, type_="check")
    op.drop_column(_T, "domain_token")
    op.drop_column(_T, "verified_domains")
    op.drop_column(_T, "idp_alias")
    op.drop_column(_T, "provider")
