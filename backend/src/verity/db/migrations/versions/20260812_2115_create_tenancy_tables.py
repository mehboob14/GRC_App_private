"""create tenancy tables — the provider plane becomes real

Revision ID: 07847268b761
Revises: ddd9734e6c34
Create Date: 2026-08-12 21:15:44.637637

Everything the provider plane needs ships in this one migration
(openspec/changes/add-provider-plane): ``platform_admins``, ``tenants``,
``tenant_branding``, ``tenant_provisioning``, the ``tenant_registration_keys``
idempotency record, every unique and leading-``tenant_id`` index, ``ENABLE`` and
``FORCE`` row-level security with every policy from design.md, and the application
role's grants — full CRUD on all five, because RLS is the wall, not the grant.

The policy table, exactly as approved:

    platform_admins           tenant plane: no policy (invisible)   provider: full
    tenants                   tenant plane: SELECT own row by PK    provider: full
    tenant_branding           tenant plane: SELECT own row          provider: full
    tenant_provisioning       tenant plane: SELECT own rows         provider: full
    tenant_registration_keys  tenant plane: no policy (invisible)   provider: full

``tenants`` is policed on its own primary key (week1-review-decisions.md, item 9): a
strengthening of ADR-0007, because a missing WHERE clause in any tenant-plane query
against the register would otherwise list every customer company by legal name. The
tenant plane gets SELECT only, everywhere — lifecycle, plan, branding, and
provisioning are written from the provider plane.

The **downgrade is destructive in the real sense**: it is mechanically reversible,
and it DROPS EVERY TENANT on the deployment, with branding, provisioning, and the
operators' accounts. The audit trail survives — that is its point. Run this against
a database that matters only if destroying every tenant is genuinely the intent.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.core.rls import PROVIDER_PLANE_ON, PROVIDER_PLANE_SETTING, TENANT_ID_SETTING
from verity.db.rls import grant_crud, tenant_policy_predicate

revision: str = "07847268b761"
down_revision: str | None = "ddd9734e6c34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PROVIDER_PREDICATE = (
    f"NULLIF(current_setting('{PROVIDER_PLANE_SETTING}', true), '') = '{PROVIDER_PLANE_ON}'"
)
_TENANT_PREDICATE = tenant_policy_predicate()
# tenants has no tenant_id; its policy keys on the primary key itself (decision 9).
_TENANT_SELF_PREDICATE = f"id = NULLIF(current_setting('{TENANT_ID_SETTING}', true), '')::uuid"

_TABLES = (
    "platform_admins",
    "tenants",
    "tenant_branding",
    "tenant_provisioning",
    "tenant_registration_keys",
)

_POLICIES = (
    # Provider plane: full access to all five, keyed on the GUC that only
    # core.db.provider_session_scope sets.
    *(
        f"CREATE POLICY {table}_provider_all ON {table} FOR ALL "
        f"USING ({_PROVIDER_PREDICATE}) WITH CHECK ({_PROVIDER_PREDICATE})"
        for table in _TABLES
    ),
    # Tenant plane: SELECT only, where a tenant has anything to see at all. No
    # INSERT/UPDATE/DELETE policy exists, so writes match nothing / are refused.
    f"CREATE POLICY tenants_tenant_select ON tenants FOR SELECT USING ({_TENANT_SELF_PREDICATE})",
    "CREATE POLICY tenant_branding_tenant_select ON tenant_branding FOR SELECT "
    f"USING ({_TENANT_PREDICATE})",
    "CREATE POLICY tenant_provisioning_tenant_select ON tenant_provisioning FOR SELECT "
    f"USING ({_TENANT_PREDICATE})",
)


def upgrade() -> None:
    op.create_table(
        "platform_admins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("mfa_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        # Credentials live on the row (week1-review-decisions.md, decision 5). The
        # hash is argon2id; the MFA secret is envelope ciphertext AAD-bound to
        # 'platform_admin:<id>'; the recovery codes are argon2id hashes of
        # single-use codes. Plaintext never reaches these columns.
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("mfa_secret_encrypted", sa.Text(), nullable=True),
        sa.Column("recovery_codes_encrypted", postgresql.JSONB(), nullable=True),
        # TOTP replay protection, parallel to credentials.last_totp_counter
        # (week1-review-decisions.md, item 11): a code at or before this counter
        # is refused even inside its validity window.
        sa.Column("last_totp_counter", sa.BigInteger(), nullable=True),
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
        sa.CheckConstraint(
            "role IN ('super_admin', 'onboarding', 'support')",
            name=op.f("ck_platform_admins__role_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled')",
            name=op.f("ck_platform_admins__status_valid"),
        ),
        sa.UniqueConstraint("email", name=op.f("uq_platform_admins__email")),
    )

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("legal_name", sa.Text(), nullable=False),
        sa.Column("trading_name", sa.Text(), nullable=True),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("industry", sa.Text(), nullable=True),
        sa.Column("registration_number", sa.Text(), nullable=True),
        sa.Column("address_line1", sa.Text(), nullable=True),
        sa.Column("address_line2", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("state_region", sa.Text(), nullable=True),
        sa.Column("postal_code", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("primary_contact_name", sa.Text(), nullable=True),
        sa.Column("primary_contact_email", sa.Text(), nullable=True),
        sa.Column("primary_contact_phone", sa.Text(), nullable=True),
        sa.Column("plan", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        # NULL for self-service signup (decision 7); no ON DELETE action, because
        # operators are disabled, not deleted.
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("onboarded_at", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('provisioning', 'active', 'suspended', 'terminated')",
            name=op.f("ck_tenants__status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["platform_admins.id"], name=op.f("fk_tenants__created_by")
        ),
        sa.UniqueConstraint("slug", name=op.f("uq_tenants__slug")),
    )
    # The provider register's default filter. No tenant_id exists on this table.
    op.create_index("ix_tenants__status", "tenants", ["status"])

    op.create_table(
        "tenant_branding",
        # The primary key IS the tenant: one branding record per tenant, per the ER.
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("logo_ref", sa.Text(), nullable=True),
        sa.Column("primary_color", sa.Text(), nullable=True),
        sa.Column("secondary_color", sa.Text(), nullable=True),
        sa.Column("custom_domain", sa.Text(), nullable=True),
        sa.Column("email_from_name", sa.Text(), nullable=True),
        sa.Column("email_from_address", sa.Text(), nullable=True),
        # Application-layer ciphertext only, AAD-bound to 'tenant_branding:<tenant_id>'.
        sa.Column("smtp_config_ref", sa.Text(), nullable=True),
        sa.Column("document_footer", sa.Text(), nullable=True),
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
            name=op.f("fk_tenant_branding__tenant_id"),
            ondelete="CASCADE",
        ),
    )
    # Partial: many tenants have no custom domain, and NULLs must not collide.
    op.create_index(
        "uq_tenant_branding__custom_domain",
        "tenant_branding",
        ["custom_domain"],
        unique=True,
        postgresql_where=sa.text("custom_domain IS NOT NULL"),
    )

    op.create_table(
        "tenant_provisioning",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "step IN ('create_tenant', 'seed_content', 'invite_admin', 'verify')",
            name=op.f("ck_tenant_provisioning__step_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'done')",
            name=op.f("ck_tenant_provisioning__status_valid"),
        ),
        # No 'failed' status (decision 8): a failing step stays pending and is
        # retried. This CHECK keeps status and completed_at from disagreeing.
        sa.CheckConstraint(
            "(status = 'done') = (completed_at IS NOT NULL)",
            name=op.f("ck_tenant_provisioning__done_has_completed_at"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_tenant_provisioning__tenant_id"),
            ondelete="CASCADE",
        ),
        # What makes provisioning idempotent: a step is a row, not a log entry.
        sa.UniqueConstraint(
            "tenant_id", "step", name=op.f("uq_tenant_provisioning__tenant_id_step")
        ),
    )
    op.create_index(
        "ix_tenant_provisioning__tenant_id_status",
        "tenant_provisioning",
        ["tenant_id", "status"],
    )

    op.create_table(
        "tenant_registration_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("request_hash", sa.Text(), nullable=False),
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
            ["platform_admin_id"],
            ["platform_admins.id"],
            name=op.f("fk_tenant_registration_keys__platform_admin_id"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_tenant_registration_keys__tenant_id"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "platform_admin_id",
            "idempotency_key",
            name=op.f("uq_tenant_registration_keys__platform_admin_id_idempotency_key"),
        ),
    )
    # Serves the ON DELETE CASCADE from tenants at teardown; Postgres does not
    # index the referencing side of a foreign key by itself.
    op.create_index(
        "ix_tenant_registration_keys__tenant_id", "tenant_registration_keys", ["tenant_id"]
    )

    for table in _TABLES:
        op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        grant_crud(table)
    for policy in _POLICIES:
        op.execute(sa.text(policy))


def downgrade() -> None:
    # THIS DESTROYS EVERY TENANT ON THE DEPLOYMENT — branding, provisioning, the
    # idempotency records, and every platform admin account. Dropping each table
    # takes its policies and indexes with it. The audit trail survives, by design.
    op.drop_table("tenant_registration_keys")
    op.drop_table("tenant_provisioning")
    op.drop_table("tenant_branding")
    op.drop_table("tenants")
    op.drop_table("platform_admins")
