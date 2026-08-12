"""create identity and access tables — people become real

Revision ID: 8f2c5d1b9a47
Revises: 07847268b761
Create Date: 2026-08-12 23:40:00.000000

Everything openspec/changes/add-identity-and-access needs ships in this one
migration: the ten tables of design.md, every unique and leading-``tenant_id``
index, ``ENABLE`` + ``FORCE`` row-level security with the tenant policy on every
tenant-owned table, the identity-resolution policies (below), the application
role's grants, and the Week 1 permission seed (decision 14).

Row-level security, per design.md's table plus one addition:

    users, credentials, user_identities, permissions, role_permissions
        no RLS — global identity / global content plane
    tenant_memberships, groups, group_members, roles, role_assignments
        tenant policy (USING + WITH CHECK on tenant_id), ENABLE + FORCE

The addition: ``tenant_memberships``, ``group_members``, ``roles``, and
``role_assignments`` also carry a **SELECT-only** policy keyed on
``app.provider_plane`` — the same dual-plane mechanism ``audit_log`` uses. It
exists because authentication must resolve a membership *before* any tenant can
be bound: a login knows an email, a session or invite token knows a membership
id, and only the membership row knows its tenant. Those identity-plane reads run
inside ``core.db.provider_session_scope``; every write still requires the bound
tenant, which is why signup binds both settings in one transaction. ``groups``
needs no such policy — nothing on the identity plane reads group names.

This migration also amends ``tenant_registration_keys`` for self-service signup
(decision 7): ``platform_admin_id`` becomes nullable (NULL = no operator acted),
with a partial unique index deduplicating the self-service keys that a UNIQUE
constraint over a nullable column would treat as always-distinct.

The **downgrade is destructive in the real sense**: it is mechanically
reversible, and it DESTROYS EVERY USER, CREDENTIAL, MEMBERSHIP, GROUP, ROLE, AND
ROLE ASSIGNMENT on the deployment — every person on the platform, in every
tenant. The audit trail survives; nothing else here does. Run it against a
database that matters only if that is genuinely the intent.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.core.config import get_settings
from verity.core.rls import PROVIDER_PLANE_ON, PROVIDER_PLANE_SETTING
from verity.db.rls import enable_rls, grant_crud

revision: str = "8f2c5d1b9a47"
down_revision: str | None = "07847268b761"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PROVIDER_PREDICATE = (
    f"NULLIF(current_setting('{PROVIDER_PLANE_SETTING}', true), '') = '{PROVIDER_PLANE_ON}'"
)

_TENANT_TABLES = ("tenant_memberships", "groups", "group_members", "roles", "role_assignments")

# Identity-resolution reads: memberships (whose tenant is this token?), the RBAC
# tables that answer "does this membership hold Admin" before a session exists.
_IDENTITY_RESOLUTION_TABLES = (
    "tenant_memberships",
    "group_members",
    "roles",
    "role_assignments",
)

# Decision 14: the Week 1 keys are seeded here, idempotently. Later modules seed
# their own keys in their own migrations; Admin picks them up at check time.
_WEEK1_PERMISSIONS = (
    ("tenant:read", "tenant", "read"),
    ("members:read", "members", "read"),
    ("members:invite", "members", "invite"),
    ("members:disable", "members", "disable"),
    ("groups:read", "groups", "read"),
    ("groups:manage", "groups", "manage"),
    ("roles:read", "roles", "read"),
    ("roles:manage", "roles", "manage"),
    ("audit:read", "audit", "read"),
)


def _timestamps() -> tuple[sa.Column[Any], sa.Column[Any]]:
    return (
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
    )


def upgrade() -> None:
    # -- global identity (no tenant_id, no RLS) --------------------------------

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("mfa_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("status IN ('active', 'disabled')", name=op.f("ck_users__status_valid")),
        # Email is unique globally (ADR-0011): the row is the person.
        sa.UniqueConstraint("email", name=op.f("uq_users__email")),
    )

    op.create_table(
        "credentials",
        # The primary key IS the user: one credential record per person.
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        # argon2id via core/security.py; the MFA secret is envelope ciphertext
        # AAD-bound to 'credentials:<user_id>'; the recovery codes are argon2id
        # hashes of single-use codes. Plaintext never reaches these columns.
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("mfa_secret_encrypted", sa.Text(), nullable=True),
        sa.Column("recovery_codes_encrypted", postgresql.JSONB(), nullable=True),
        sa.Column("last_login_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("mfa_enrolled_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        # TOTP replay protection — approved derived column (decision 11).
        sa.Column("last_totp_counter", sa.BigInteger(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_credentials__user_id"), ondelete="CASCADE"
        ),
    )

    op.create_table(
        "user_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        # Approved derived column (decision 11): ADR-0006 needs OIDC vs SAML.
        sa.Column("provider_type", sa.Text(), nullable=False),
        sa.Column("external_subject_id", sa.Text(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "provider_type IN ('oidc', 'saml')",
            name=op.f("ck_user_identities__provider_type_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_identities__user_id"),
            ondelete="CASCADE",
        ),
        # The federation seam's identity: one external subject maps to one user.
        sa.UniqueConstraint(
            "provider", "external_subject_id", name=op.f("uq_user_identities__provider_subject")
        ),
        # One link per provider per user.
        sa.UniqueConstraint(
            "user_id", "provider", name=op.f("uq_user_identities__user_id_provider")
        ),
    )

    # -- global content ----------------------------------------------------------

    op.create_table(
        "permissions",
        # The key IS the identity: 'module:action', composed by roles.
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("module", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        *_timestamps(),
    )

    # -- tenant plane -------------------------------------------------------------

    op.create_table(
        "tenant_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("invited_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("accepted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("disabled_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('invited', 'active', 'disabled')",
            name=op.f("ck_tenant_memberships__status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_tenant_memberships__tenant_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_tenant_memberships__user_id")
        ),
        # A person is in a tenant once; a second tenant is a second row.
        sa.UniqueConstraint(
            "tenant_id", "user_id", name=op.f("uq_tenant_memberships__tenant_id_user_id")
        ),
    )
    op.create_index(
        "ix_tenant_memberships__tenant_id_status", "tenant_memberships", ["tenant_id", "status"]
    )

    op.create_table(
        "groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("fk_groups__tenant_id"), ondelete="CASCADE"
        ),
        sa.UniqueConstraint("tenant_id", "name", name=op.f("uq_groups__tenant_id_name")),
    )

    op.create_table(
        "group_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # Denormalised onto the join (design.md): the RLS policy is a direct
        # column comparison, and a cross-tenant (group, membership) pair fails
        # WITH CHECK before the FKs are considered.
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_membership_id", postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_group_members__tenant_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
            name=op.f("fk_group_members__group_id"),
            ondelete="CASCADE",
        ),
        # The member is the membership, never the user — the schema-level wall
        # of ADR-0011. CASCADE so tenant teardown needs no ordering.
        sa.ForeignKeyConstraint(
            ["tenant_membership_id"],
            ["tenant_memberships.id"],
            name=op.f("fk_group_members__tenant_membership_id"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "group_id", "tenant_membership_id", name=op.f("uq_group_members__group_id_membership")
        ),
    )
    op.create_index(
        "ix_group_members__tenant_id_membership",
        "group_members",
        ["tenant_id", "tenant_membership_id"],
    )

    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("built_in", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("fk_roles__tenant_id"), ondelete="CASCADE"
        ),
        sa.UniqueConstraint("tenant_id", "name", name=op.f("uq_roles__tenant_id_name")),
    )

    op.create_table(
        "role_permissions",
        # No tenant_id: reachable only through roles, which is RLS-protected.
        sa.Column("role_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("permission_key", sa.Text(), primary_key=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name=op.f("fk_role_permissions__role_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["permission_key"],
            ["permissions.key"],
            name=op.f("fk_role_permissions__permission_key"),
        ),
    )

    op.create_table(
        "role_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Polymorphic with assignee_type (membership | group) — no FK possible,
        # same reasoning as audit_log.actor_id. The service validates the target
        # lives in this tenant; the RLS policy still bounds every row.
        sa.Column("assignee_type", sa.Text(), nullable=False),
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Deliberately NO foreign key: engagements land with the compliance
        # module, which adds the constraint then (proposal.md).
        sa.Column("engagement_id", postgresql.UUID(as_uuid=True), nullable=True),
        # The auditor time-box lives here, on the grant — not on the membership
        # (ADR-0011 as amended). Dates, not timestamps: the window is a calendar
        # agreement, not an instant.
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "assignee_type IN ('membership', 'group')",
            name=op.f("ck_role_assignments__assignee_type_valid"),
        ),
        sa.CheckConstraint(
            "valid_from IS NULL OR valid_until IS NULL OR valid_from <= valid_until",
            name=op.f("ck_role_assignments__window_order"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_role_assignments__tenant_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name=op.f("fk_role_assignments__role_id"),
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_role_assignments__tenant_id_assignee",
        "role_assignments",
        ["tenant_id", "assignee_type", "assignee_id"],
    )
    op.create_index(
        "ix_role_assignments__tenant_id_engagement",
        "role_assignments",
        ["tenant_id", "engagement_id"],
        postgresql_where=sa.text("engagement_id IS NOT NULL"),
    )

    # -- row-level security and grants ---------------------------------------------

    for table in _TENANT_TABLES:
        enable_rls(table)  # ENABLE + FORCE + the tenant policy, USING and WITH CHECK
        grant_crud(table)
    for table in _IDENTITY_RESOLUTION_TABLES:
        op.execute(
            sa.text(
                f"CREATE POLICY {table}_identity_select ON {table} "
                f"FOR SELECT USING ({_PROVIDER_PREDICATE})"
            )
        )
    for table in ("users", "credentials", "user_identities", "role_permissions"):
        grant_crud(table)
    # The application reads permission keys; only migrations write them.
    op.execute(sa.text(f"GRANT SELECT ON permissions TO {get_settings().database.app_role}"))

    # -- Week 1 permission seed (decision 14) ----------------------------------------

    values = ", ".join(
        f"('{key}', '{module}', '{action}')" for key, module, action in _WEEK1_PERMISSIONS
    )
    op.execute(
        # S608: built entirely from the compile-time constant tuple above —
        # nothing user-supplied can reach this statement.
        sa.text(
            f"INSERT INTO permissions (key, module, action) VALUES {values} "  # noqa: S608
            "ON CONFLICT (key) DO NOTHING"
        )
    )

    # -- self-service registration keys (decision 7) ----------------------------------

    op.alter_column(
        "tenant_registration_keys",
        "platform_admin_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    # NULL = self-service. A UNIQUE constraint treats NULLs as distinct, so the
    # self-service population is deduplicated by this partial index instead.
    op.create_index(
        "uq_tenant_registration_keys__self_service_key",
        "tenant_registration_keys",
        ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text("platform_admin_id IS NULL"),
    )


def downgrade() -> None:
    # THIS DESTROYS EVERY PERSON ON THE PLATFORM: all users, credentials,
    # memberships, groups, roles, and assignments, in every tenant. The audit
    # trail survives — that is its point. Dropping each table takes its
    # policies and indexes with it.
    op.drop_index(
        "uq_tenant_registration_keys__self_service_key", table_name="tenant_registration_keys"
    )
    # Self-service rows cannot survive the column going NOT NULL again.
    op.execute(sa.text("DELETE FROM tenant_registration_keys WHERE platform_admin_id IS NULL"))
    op.alter_column(
        "tenant_registration_keys",
        "platform_admin_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )

    op.drop_table("role_assignments")
    op.drop_table("role_permissions")
    op.drop_table("roles")
    op.drop_table("group_members")
    op.drop_table("groups")
    op.drop_table("tenant_memberships")
    op.drop_table("permissions")
    op.drop_table("user_identities")
    op.drop_table("credentials")
    op.drop_table("users")
