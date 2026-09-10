"""vulnerabilities module — definition/instance/transition/report/sla (Week 6)

Revision ID: c9e3f5a71b20
Revises: b8c2d4e6f019
Create Date: 2026-09-01 10:00:00.000000

Five tenant-owned tables, so RLS + grants land with them (rule 12). Follows the
definition/instance model of ADR-0010: ``vuln_definitions`` (per-CVE, enriched
once), ``vuln_instances`` (per-asset stateful unit, Integratable for Phase-2
scanner sync), ``vuln_transitions`` (append-only, rule 5), ``vuln_reports``
(import provenance), ``vuln_sla_policies`` (per-severity days).

Seeds the four ``vulnerabilities:*`` permission keys — Admin resolves to every
key that exists, so it picks them up automatically; custom roles opt in through
the Roles screen. Check-constraint names use ``conv()`` so ``ck`` is not wrapped
twice.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.db.rls import disable_rls, drop_append_only, enable_rls, grant_crud, make_append_only

revision: str = "c9e3f5a71b20"
down_revision: str | None = "b8c2d4e6f019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEVERITIES = ("critical", "high", "medium", "low", "info")
INSTANCE_STATES = (
    "new",
    "active",
    "in_progress",
    "pending_retest",
    "fixed",
    "resurfaced",
    "accepted",
    "false_positive",
)
REPORT_TYPES = ("vulnerability_scan", "penetration_test", "code_review", "configuration_audit")
REPORT_STATUSES = ("uploaded", "parsing", "parsed", "failed")

# Creation order respects the foreign keys; downgrade drops the reverse.
_TABLES = (
    "vuln_definitions",
    "vuln_reports",
    "vuln_instances",
    "vuln_transitions",
    "vuln_sla_policies",
)

_UUID = postgresql.UUID(as_uuid=True)


def _check(table: str, column: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    joined = ", ".join(f"'{v}'" for v in values)
    return sa.CheckConstraint(f"{column} IN ({joined})", name=conv(f"ck_{table}__{column}_valid"))


def _ts() -> tuple[sa.Column[Any], sa.Column[Any]]:
    return (
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def _tenant_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{table}__tenant_id"
    )


def _member_fk(table: str, column: str, ondelete: str = "SET NULL") -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], ["tenant_memberships.id"], ondelete=ondelete, name=f"fk_{table}__{column}"
    )


def _integratable() -> tuple[sa.Column[Any], ...]:
    return (
        sa.Column("source", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def upgrade() -> None:
    op.create_table(
        "vuln_definitions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("definition_key", sa.Text(), nullable=False),
        sa.Column("cve_id", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.Text(), nullable=False, server_default="medium"),
        sa.Column("cvss_score", sa.Float(), nullable=True),
        sa.Column("cvss_vector", sa.Text(), nullable=True),
        sa.Column("cvss_version", sa.Text(), nullable=True),
        sa.Column("cwe_id", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("epss_score", sa.Float(), nullable=True),
        sa.Column("epss_percentile", sa.Float(), nullable=True),
        sa.Column("kev_flag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("kev_ransomware", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("kev_added_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("public_exploit_count", sa.Integer(), nullable=True),
        sa.Column(
            "exploit_refs",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("enriched_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_integratable(),
        *_ts(),
        _tenant_fk("vuln_definitions"),
        _check("vuln_definitions", "severity", SEVERITIES),
        sa.UniqueConstraint(
            "tenant_id", "definition_key", name="uq_vuln_definitions__tenant_id_key"
        ),
    )
    op.create_index(
        "ix_vuln_definitions__tenant_id_cve_id", "vuln_definitions", ["tenant_id", "cve_id"]
    )
    op.create_index(
        "ix_vuln_definitions__tenant_id_severity", "vuln_definitions", ["tenant_id", "severity"]
    )

    op.create_table(
        "vuln_reports",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("report_type", sa.Text(), nullable=False, server_default="vulnerability_scan"),
        sa.Column("scan_tool", sa.Text(), nullable=True),
        sa.Column("scan_date", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("file_key", sa.Text(), nullable=True),
        sa.Column("file_name", sa.Text(), nullable=True),
        sa.Column("file_type", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="uploaded"),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("critical_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("high_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("medium_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("low_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("info_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("uploaded_by_membership_id", _UUID, nullable=True),
        *_ts(),
        _tenant_fk("vuln_reports"),
        _member_fk("vuln_reports", "uploaded_by_membership_id"),
        _check("vuln_reports", "report_type", REPORT_TYPES),
        _check("vuln_reports", "status", REPORT_STATUSES),
    )
    op.create_index("ix_vuln_reports__tenant_id_status", "vuln_reports", ["tenant_id", "status"])

    op.create_table(
        "vuln_instances",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("definition_id", _UUID, nullable=False),
        sa.Column("asset_id", _UUID, nullable=False),
        sa.Column("report_id", _UUID, nullable=True),
        sa.Column("locator", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("component", sa.Text(), nullable=True),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("affected_url", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=False, server_default="new"),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("risk_reason", sa.Text(), nullable=True),
        sa.Column("owner_membership_id", _UUID, nullable=True),
        sa.Column("first_detected_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("sla_due_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "detected_by", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column("fixed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("fixed_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("resurfaced_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("accepted_reason", sa.Text(), nullable=True),
        sa.Column("accepted_expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("accepted_by_membership_id", _UUID, nullable=True),
        sa.Column("false_positive_reason", sa.Text(), nullable=True),
        *_integratable(),
        *_ts(),
        _tenant_fk("vuln_instances"),
        sa.ForeignKeyConstraint(
            ["definition_id"],
            ["vuln_definitions.id"],
            ondelete="CASCADE",
            name="fk_vuln_instances__definition_id",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            ondelete="CASCADE",
            name="fk_vuln_instances__asset_id",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["vuln_reports.id"],
            ondelete="SET NULL",
            name="fk_vuln_instances__report_id",
        ),
        _member_fk("vuln_instances", "owner_membership_id"),
        _member_fk("vuln_instances", "accepted_by_membership_id"),
        _check("vuln_instances", "state", INSTANCE_STATES),
        sa.UniqueConstraint(
            "tenant_id",
            "asset_id",
            "definition_id",
            "locator",
            name="uq_vuln_instances__asset_def_locator",
        ),
    )
    op.create_index(
        "ix_vuln_instances__tenant_id_asset_id", "vuln_instances", ["tenant_id", "asset_id"]
    )
    op.create_index("ix_vuln_instances__tenant_id_state", "vuln_instances", ["tenant_id", "state"])
    op.create_index(
        "ix_vuln_instances__tenant_id_owner_membership_id",
        "vuln_instances",
        ["tenant_id", "owner_membership_id"],
    )

    op.create_table(
        "vuln_transitions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("instance_id", _UUID, nullable=False),
        sa.Column("actor_membership_id", _UUID, nullable=True),
        sa.Column("from_state", sa.Text(), nullable=True),
        sa.Column("to_state", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False),
        *_ts(),
        _tenant_fk("vuln_transitions"),
        sa.ForeignKeyConstraint(
            ["instance_id"],
            ["vuln_instances.id"],
            ondelete="CASCADE",
            name="fk_vuln_transitions__instance_id",
        ),
        _member_fk("vuln_transitions", "actor_membership_id"),
    )
    op.create_index(
        "ix_vuln_transitions__tenant_id_instance_id",
        "vuln_transitions",
        ["tenant_id", "instance_id"],
    )

    op.create_table(
        "vuln_sla_policies",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        *_ts(),
        _tenant_fk("vuln_sla_policies"),
        _check("vuln_sla_policies", "severity", SEVERITIES),
        sa.UniqueConstraint(
            "tenant_id", "severity", name="uq_vuln_sla_policies__tenant_id_severity"
        ),
    )

    # RLS + grants on every table (rule 12).
    for table in _TABLES:
        enable_rls(table)
        grant_crud(table)
    # vuln_transitions is insert-only (rule 5): revoke UPDATE/DELETE + shared trigger.
    make_append_only("vuln_transitions")

    op.execute(
        "INSERT INTO permissions (key, module, action) VALUES "
        "('vulnerabilities:read', 'vulnerabilities', 'read'), "
        "('vulnerabilities:manage', 'vulnerabilities', 'manage'), "
        "('vulnerabilities:import', 'vulnerabilities', 'import'), "
        "('vulnerabilities:accept', 'vulnerabilities', 'accept') ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM permissions WHERE key IN "
        "('vulnerabilities:read', 'vulnerabilities:manage', "
        "'vulnerabilities:import', 'vulnerabilities:accept')"
    )
    drop_append_only("vuln_transitions")
    for table in reversed(_TABLES):
        disable_rls(table)
        op.drop_table(table)
