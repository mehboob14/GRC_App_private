"""per-tenant password policy, and the history needed to enforce reuse

Revision ID: f3b7c1d9a204
Revises: e2a7b93c15d8
Create Date: 2026-08-17 14:00:00.000000

Two changes, one intent.

``tenant_settings`` gains the policy itself. It already holds the tenant's other
auth policy (``require_admin_mfa``), is one row per tenant, and is already read
on the provider plane during login — which is exactly when a password is
checked — so the policy belongs here rather than in a second settings table.

``credentials`` gains ``previous_password_hashes``: the last N argon2 digests
for that user, newest first. It lives on the credential rather than in its own
table because a password is a property of the *user* (global identity), not of
a tenant — a person in two workspaces has one password — and ``credentials`` is
already the row that carries it under the same protections. The column name
contains "hash", which is what puts it inside the audit-snapshot and logging
deny-lists (``core.logging``) without a second registration.

Defaults are the recommended posture, not the loosest one: 12 characters with
all four character classes, and the last 5 passwords blocked. ``0`` disables a
numeric check. The three columns that are stored but not yet enforced
(``password_max_age_days``, ``lockout_*``, ``idle_timeout_minutes``) default to
0/off precisely so nothing claims a control the platform does not yet apply.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f3b7c1d9a204"
down_revision: str | None = "e2a7b93c15d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Each entry is the column name, its type, and its server-side default.
# `TypeEngine` is invariant in its Python type, so the parameter has to be `Any`
# for a tuple that mixes Integer (int) and Boolean (bool) entries.
_POLICY_COLUMNS: tuple[tuple[str, sa.types.TypeEngine[Any], str], ...] = (
    ("password_min_length", sa.Integer(), "12"),
    ("password_require_upper", sa.Boolean(), "true"),
    ("password_require_lower", sa.Boolean(), "true"),
    ("password_require_digit", sa.Boolean(), "true"),
    ("password_require_symbol", sa.Boolean(), "true"),
    ("password_history_depth", sa.Integer(), "5"),
    # Stored, surfaced, and explicitly not enforced yet.
    ("password_max_age_days", sa.Integer(), "0"),
    ("lockout_threshold", sa.Integer(), "0"),
    ("lockout_duration_minutes", sa.Integer(), "30"),
    ("idle_timeout_minutes", sa.Integer(), "0"),
)

# Bounds live in the database as well as the schema: the API is one writer, and
# a policy that could be set to min_length 0 would silently disable the control.
_CHECKS: tuple[tuple[str, str], ...] = (
    ("ck_tenant_settings__password_min_length", "password_min_length BETWEEN 8 AND 128"),
    ("ck_tenant_settings__password_history_depth", "password_history_depth BETWEEN 0 AND 24"),
    ("ck_tenant_settings__password_max_age_days", "password_max_age_days BETWEEN 0 AND 3650"),
    ("ck_tenant_settings__lockout_threshold", "lockout_threshold BETWEEN 0 AND 100"),
    ("ck_tenant_settings__lockout_duration", "lockout_duration_minutes BETWEEN 0 AND 10080"),
    ("ck_tenant_settings__idle_timeout", "idle_timeout_minutes BETWEEN 0 AND 10080"),
)


def upgrade() -> None:
    for name, type_, default in _POLICY_COLUMNS:
        op.add_column(
            "tenant_settings",
            sa.Column(name, type_, server_default=sa.text(default), nullable=False),
        )
    for name, condition in _CHECKS:
        op.create_check_constraint(name, "tenant_settings", condition)

    op.add_column(
        "credentials",
        sa.Column("previous_password_hashes", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("credentials", "previous_password_hashes")
    for name, _ in _CHECKS:
        op.drop_constraint(name, "tenant_settings", type_="check")
    for name, _, _ in reversed(_POLICY_COLUMNS):
        op.drop_column("tenant_settings", name)
