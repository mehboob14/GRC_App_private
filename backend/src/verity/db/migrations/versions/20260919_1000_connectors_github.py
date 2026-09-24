"""connectors: check content, connections, runs, results, integration requests

Week 7 of the build plan: connect GitHub and watch controls marked pass or fail
from real repository data (openspec/changes/common-control-framework).

Global content (no tenant_id, SELECT only for the application role):
``integration_capabilities``, ``checks``, ``control_template_checks``. Loaded by
``seed-content`` from the automation pack.

Tenant plane (forced RLS, grants in this migration): ``connections``,
``check_runs``, ``integration_requests``, and ``check_results``.

``check_results`` is append only (rule 3) and range partitioned by month on
``observed_at`` from this first migration (ER 5.9). Monthly partitions are
created through December 2028; the default partition catches anything later so
an insert never fails, and a follow up migration extends the range well before
then (``tests/unit/test_check_result_partitions.py`` fails once fewer than six
months remain). Partitions get no grants of their own: the application reaches
rows only through the parent, where RLS and the append only trigger apply.

Revision ID: 63ac7a1e3c8f
Revises: c4e1a7d9b203
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Final

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.core.config import get_settings
from verity.db.rls import disable_rls, drop_append_only, enable_rls, grant_crud, make_append_only

revision: str = "63ac7a1e3c8f"
down_revision: str | None = "c4e1a7d9b203"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = postgresql.UUID(as_uuid=True)
_JSONB = postgresql.JSONB()
_TS = sa.TIMESTAMP(timezone=True)
_MEMBERSHIPS = "tenant_memberships.id"

# Restated, not imported: a migration describes the schema at this revision.
PROVIDERS = ("github",)
ACCOUNT_TYPES = ("organization", "user")
CONNECTION_STATUSES = ("active", "disconnected")
RUN_TRIGGERS = ("manual", "schedule")
RUN_STATUSES = ("running", "completed", "failed")
OUTCOMES = ("pass", "fail", "error", "not_applicable")
COVERAGE = ("full", "partial")
FREQUENCIES = ("daily", "weekly")
REQUEST_STATUSES = ("open", "planned", "available", "declined")
PERMISSIONS = ("connectors:read", "connectors:manage")

FIRST_PARTITION: Final = (2026, 9)
LAST_PARTITION: Final = (2028, 12)

_GLOBAL_TABLES = ("integration_capabilities", "checks", "control_template_checks")
_TENANT_TABLES = ("connections", "check_runs", "integration_requests")


def _in(column: str, values: tuple[str, ...]) -> str:
    joined = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({joined})"


def _check(table: str, column: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    return sa.CheckConstraint(_in(column, values), name=conv(f"ck_{table}__{column}_valid"))


def _ts() -> tuple[sa.Column[Any], sa.Column[Any]]:
    return (
        sa.Column("created_at", _TS, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", _TS, server_default=sa.func.now(), nullable=False),
    )


def _tenant(table: str) -> sa.Column[Any]:
    return sa.Column(
        "tenant_id",
        _UUID,
        sa.ForeignKey("tenants.id", ondelete="CASCADE", name=f"fk_{table}__tenant_id"),
        nullable=False,
    )


def _member(table: str, column: str) -> sa.Column[Any]:
    return sa.Column(
        column,
        _UUID,
        sa.ForeignKey(_MEMBERSHIPS, ondelete="SET NULL", name=f"fk_{table}__{column}"),
        nullable=True,
    )


def _json_list(name: str) -> sa.Column[Any]:
    return sa.Column(name, _JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"))


def _months() -> list[tuple[int, int]]:
    year, month = FIRST_PARTITION
    months = []
    while (year, month) <= LAST_PARTITION:
        months.append((year, month))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)  # noqa: PLR2004
    return months


def _create_content() -> None:
    op.create_table(
        "integration_capabilities",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        _json_list("providers"),
        *_ts(),
        sa.UniqueConstraint("key", name="uq_integration_capabilities__key"),
    )
    op.create_table(
        "checks",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        _json_list("capabilities"),
        _json_list("implementations"),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("frequency", sa.Text(), nullable=False, server_default=sa.text("'daily'")),
        sa.Column("remediation", sa.Text(), nullable=False),
        *_ts(),
        sa.UniqueConstraint("key", name="uq_checks__key"),
        _check("checks", "frequency", FREQUENCIES),
    )
    op.create_table(
        "control_template_checks",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column(
            "template_id",
            _UUID,
            sa.ForeignKey(
                "control_templates.id",
                ondelete="CASCADE",
                name="fk_control_template_checks__template_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "check_id",
            _UUID,
            sa.ForeignKey(
                "checks.id", ondelete="CASCADE", name="fk_control_template_checks__check_id"
            ),
            nullable=False,
        ),
        sa.Column("coverage", sa.Text(), nullable=False, server_default=sa.text("'partial'")),
        *_ts(),
        sa.UniqueConstraint("template_id", "check_id", name="uq_control_template_checks__pair"),
        _check("control_template_checks", "coverage", COVERAGE),
    )


def _create_tenant_tables() -> None:
    op.create_table(
        "connections",
        sa.Column("id", _UUID, primary_key=True),
        _tenant("connections"),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("account_login", sa.Text(), nullable=False),
        sa.Column("account_type", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'")),
        sa.Column("credential_ciphertext", sa.Text(), nullable=True),
        sa.Column("credential_hint", sa.Text(), nullable=True),
        sa.Column("credential_expires_at", _TS, nullable=True),
        sa.Column("last_run_at", _TS, nullable=True),
        sa.Column("last_success_at", _TS, nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("error_streak", sa.Integer(), nullable=False, server_default=sa.text("0")),
        _member("connections", "created_by_membership_id"),
        sa.Column("disconnected_at", _TS, nullable=True),
        sa.Column("disconnected_reason", sa.Text(), nullable=True),
        *_ts(),
        _check("connections", "provider", PROVIDERS),
        _check("connections", "account_type", ACCOUNT_TYPES),
        _check("connections", "status", CONNECTION_STATUSES),
        sa.CheckConstraint(
            "(status = 'active') = (credential_ciphertext IS NOT NULL)",
            name=conv("ck_connections__credential_only_while_active"),
        ),
    )
    op.create_index(
        "uq_connections__tenant_id_provider_account_login",
        "connections",
        ["tenant_id", "provider", "account_login"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "check_runs",
        sa.Column("id", _UUID, primary_key=True),
        _tenant("check_runs"),
        sa.Column(
            "connection_id",
            _UUID,
            sa.ForeignKey("connections.id", name="fk_check_runs__connection_id"),
            nullable=False,
        ),
        sa.Column("trigger", sa.Text(), nullable=False),
        _member("check_runs", "triggered_by_membership_id"),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'running'")),
        sa.Column("started_at", _TS, nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", _TS, nullable=True),
        sa.Column("resources", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("passed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("failed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("errored", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("results_digest", sa.Text(), nullable=True),
        sa.Column(
            "evidence_id",
            _UUID,
            sa.ForeignKey("evidence.id", ondelete="SET NULL", name="fk_check_runs__evidence_id"),
            nullable=True,
        ),
        *_ts(),
        _check("check_runs", "trigger", RUN_TRIGGERS),
        _check("check_runs", "status", RUN_STATUSES),
    )
    op.create_index(
        "ix_check_runs__tenant_id_connection_id_started_at",
        "check_runs",
        ["tenant_id", "connection_id", "started_at"],
    )

    op.create_table(
        "integration_requests",
        sa.Column("id", _UUID, primary_key=True),
        _tenant("integration_requests"),
        sa.Column("provider_name", sa.Text(), nullable=False),
        sa.Column("capability_key", sa.Text(), nullable=True),
        sa.Column(
            "control_id",
            _UUID,
            sa.ForeignKey(
                "controls.id", ondelete="SET NULL", name="fk_integration_requests__control_id"
            ),
            nullable=True,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'open'")),
        _member("integration_requests", "requested_by_membership_id"),
        *_ts(),
        _check("integration_requests", "status", REQUEST_STATUSES),
    )
    op.create_index(
        "ix_integration_requests__tenant_id_created_at",
        "integration_requests",
        ["tenant_id", "created_at"],
    )


def _create_results() -> None:
    op.create_table(
        "check_results",
        sa.Column("id", _UUID, nullable=False),
        sa.Column("observed_at", _TS, nullable=False, server_default=sa.func.now()),
        _tenant("check_results"),
        sa.Column(
            "run_id",
            _UUID,
            sa.ForeignKey("check_runs.id", name="fk_check_results__run_id"),
            nullable=False,
        ),
        sa.Column(
            "connection_id",
            _UUID,
            sa.ForeignKey("connections.id", name="fk_check_results__connection_id"),
            nullable=False,
        ),
        sa.Column(
            "check_id",
            _UUID,
            sa.ForeignKey("checks.id", name="fk_check_results__check_id"),
            nullable=False,
        ),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.Text(), nullable=False),
        sa.Column("resource_name", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("detail", _JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("id", "observed_at", name="pk_check_results"),
        _check("check_results", "outcome", OUTCOMES),
        postgresql_partition_by="RANGE (observed_at)",
    )
    op.create_index(
        "ix_check_results__tenant_id_check_id_observed_at",
        "check_results",
        ["tenant_id", "check_id", "observed_at"],
    )
    op.create_index("ix_check_results__tenant_id_run_id", "check_results", ["tenant_id", "run_id"])

    for year, month in _months():
        after = (year + 1, 1) if month == 12 else (year, month + 1)  # noqa: PLR2004
        op.execute(
            f"CREATE TABLE check_results_y{year}m{month:02d} PARTITION OF check_results "
            f"FOR VALUES FROM ('{year}-{month:02d}-01 00:00:00+00') "
            f"TO ('{after[0]}-{after[1]:02d}-01 00:00:00+00')"
        )
    op.execute("CREATE TABLE check_results_default PARTITION OF check_results DEFAULT")

    enable_rls("check_results")
    # grant_crud then make_append_only nets to SELECT + INSERT, as on audit_log.
    grant_crud("check_results")
    make_append_only("check_results")


def upgrade() -> None:
    _create_content()
    role = get_settings().database.app_role
    for table in _GLOBAL_TABLES:
        op.execute(sa.text(f"GRANT SELECT ON {table} TO {role}"))

    _create_tenant_tables()
    for table in _TENANT_TABLES:
        enable_rls(table)
        grant_crud(table)
    _create_results()

    # Admin resolves to every key at check time, so no role bundle changes here.
    op.execute(
        "INSERT INTO permissions (key, module, action) VALUES "
        "('connectors:read', 'connectors', 'read'), "
        "('connectors:manage', 'connectors', 'manage') ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    keys = ", ".join(f"'{key}'" for key in PERMISSIONS)
    op.execute(f"DELETE FROM role_permissions WHERE permission_key IN ({keys})")  # noqa: S608
    op.execute(f"DELETE FROM permissions WHERE key IN ({keys})")  # noqa: S608

    drop_append_only("check_results")
    disable_rls("check_results")
    op.drop_table("check_results")  # drops every partition with it
    for table in reversed(_TENANT_TABLES):
        disable_rls(table)
        op.drop_table(table)
    for table in reversed(_GLOBAL_TABLES):
        op.drop_table(table)
