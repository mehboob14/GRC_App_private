"""assets module — inventory, decommission records, lifecycle history

Revision ID: a7d2e9f10b34
Revises: e4a9c7d21f08
Create Date: 2026-08-25 10:00:00.000000

Three tenant-owned tables, so RLS + grants land with them (rule 12).
``asset_transitions`` is append-only (rule 5 / ADR-0005): revoked UPDATE/DELETE
plus the shared BEFORE UPDATE OR DELETE trigger. Seeds the four ``assets:*``
permission keys — Admin resolves to every key that exists, so it picks them up
automatically; custom roles opt in through the Roles screen.

Criticality columns carry NO default: a NULL score/tier means "not assessed".
Correlation keys and the ``source``/``external_id``/``synced_at`` triple ride the
row now so Phase-2 connector sync needs no schema change. Relationships, groups
and inventory reviews are a later migration (stage B6), not here.

Check-constraint names use ``conv()`` so the ``ck`` naming convention does not
wrap them a second time (the model does the same via ``status_check``).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.db.rls import disable_rls, drop_append_only, enable_rls, grant_crud, make_append_only

revision: str = "a7d2e9f10b34"
down_revision: str | None = "e4a9c7d21f08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ASSET_TYPES = ("application", "infrastructure", "data", "cloud", "third_party", "business_service")
ASSET_STATUSES = ("planned", "active", "in_maintenance", "decommissioned", "retired")
DATA_CLASSIFICATIONS = ("public", "internal", "confidential", "restricted")
CRITICALITY_TIERS = ("critical", "high", "medium", "low")
ENVIRONMENTS = ("prod", "staging", "dev", "test", "dr")

# Creation order respects the foreign keys; downgrade drops the reverse.
_TABLES = ("assets", "decommission_records", "asset_transitions")

_UUID = postgresql.UUID(as_uuid=True)


def _check(table: str, column: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    joined = ", ".join(f"'{v}'" for v in values)
    return sa.CheckConstraint(f"{column} IN ({joined})", name=conv(f"ck_{table}__{column}_valid"))


def _ts() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def _member_fk(table: str, column: str, ondelete: str = "SET NULL") -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], ["tenant_memberships.id"], ondelete=ondelete, name=f"fk_{table}__{column}"
    )


def _tenant_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{table}__tenant_id"
    )


def _asset_fk(
    table: str, column: str = "asset_id", ondelete: str = "CASCADE"
) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], ["assets.id"], ondelete=ondelete, name=f"fk_{table}__{column}"
    )


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        # identity
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("asset_type", sa.Text(), nullable=False, server_default="application"),
        sa.Column("hostname", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("vendor_ref", sa.Text(), nullable=True),
        # correlation keys (Phase-2 connectors populate these)
        sa.Column("fqdn", sa.Text(), nullable=True),
        sa.Column("primary_mac", sa.Text(), nullable=True),
        sa.Column("serial_number", sa.Text(), nullable=True),
        sa.Column("cloud_resource_id", sa.Text(), nullable=True),
        sa.Column("os_normalized", sa.Text(), nullable=True),
        sa.Column("environment", sa.Text(), nullable=True),
        # classification & exposure
        sa.Column("data_classification", sa.Text(), nullable=True),
        sa.Column("regulated_data_type", sa.Text(), nullable=True),
        sa.Column(
            "compliance_scope",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("internet_facing", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("customer_facing", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("network_segment", sa.Text(), nullable=True),
        sa.Column("business_function", sa.Text(), nullable=True),
        # business context
        sa.Column("valuation", sa.Float(), nullable=True),
        sa.Column("business_impact_notes", sa.Text(), nullable=True),
        sa.Column("operational_dependency_rating", sa.Text(), nullable=True),
        # ownership chain
        sa.Column("primary_owner_membership_id", _UUID, nullable=True),
        sa.Column("secondary_owner_membership_id", _UUID, nullable=True),
        sa.Column("business_owner_membership_id", _UUID, nullable=True),
        sa.Column("custodian_membership_id", _UUID, nullable=True),
        sa.Column("escalation_contact_membership_id", _UUID, nullable=True),
        sa.Column("owning_team_group_id", _UUID, nullable=True),
        # criticality — nullable, no default
        sa.Column("confidentiality", sa.Integer(), nullable=True),
        sa.Column("integrity", sa.Integer(), nullable=True),
        sa.Column("availability", sa.Integer(), nullable=True),
        sa.Column("criticality_score", sa.Float(), nullable=True),
        sa.Column("tier", sa.Text(), nullable=True),
        sa.Column("tier_override", sa.Text(), nullable=True),
        sa.Column("tier_override_reason", sa.Text(), nullable=True),
        # lifecycle
        sa.Column("status", sa.Text(), nullable=False, server_default="planned"),
        sa.Column("replaced_by_asset_id", _UUID, nullable=True),
        # freshness
        sa.Column("first_seen_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        # Integratable
        sa.Column("source", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_ts(),
        _tenant_fk("assets"),
        _member_fk("assets", "primary_owner_membership_id"),
        _member_fk("assets", "secondary_owner_membership_id"),
        _member_fk("assets", "business_owner_membership_id"),
        _member_fk("assets", "custodian_membership_id"),
        _member_fk("assets", "escalation_contact_membership_id"),
        sa.ForeignKeyConstraint(
            ["owning_team_group_id"],
            ["groups.id"],
            ondelete="SET NULL",
            name="fk_assets__owning_team_group_id",
        ),
        sa.ForeignKeyConstraint(
            ["replaced_by_asset_id"],
            ["assets.id"],
            ondelete="SET NULL",
            name="fk_assets__replaced_by_asset_id",
        ),
        _check("assets", "asset_type", ASSET_TYPES),
        _check("assets", "status", ASSET_STATUSES),
        _check("assets", "data_classification", DATA_CLASSIFICATIONS),
        _check("assets", "environment", ENVIRONMENTS),
        _check("assets", "tier", CRITICALITY_TIERS),
        _check("assets", "tier_override", CRITICALITY_TIERS),
        sa.CheckConstraint(
            "(confidentiality IS NULL OR confidentiality BETWEEN 1 AND 5) AND "
            "(integrity IS NULL OR integrity BETWEEN 1 AND 5) AND "
            "(availability IS NULL OR availability BETWEEN 1 AND 5)",
            name=conv("ck_assets__cia_range"),
        ),
        sa.CheckConstraint(
            "(tier_override IS NULL) OR (tier_override_reason IS NOT NULL)",
            name=conv("ck_assets__override_has_reason"),
        ),
        sa.UniqueConstraint(
            "tenant_id", "source", "external_id", name="uq_assets__tenant_id_source_external_id"
        ),
    )
    op.create_index("ix_assets__tenant_id_status", "assets", ["tenant_id", "status"])
    op.create_index("ix_assets__tenant_id_asset_type", "assets", ["tenant_id", "asset_type"])
    op.create_index("ix_assets__tenant_id_tier_override", "assets", ["tenant_id", "tier_override"])
    op.create_index(
        "ix_assets__tenant_id_primary_owner_membership_id",
        "assets",
        ["tenant_id", "primary_owner_membership_id"],
    )

    op.create_table(
        "decommission_records",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("asset_id", _UUID, nullable=False),
        sa.Column("disposal_method", sa.Text(), nullable=False),
        sa.Column("media_sanitised", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("replacement_asset_id", _UUID, nullable=True),
        sa.Column("evidence_ref", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("decommissioned_by_membership_id", _UUID, nullable=True),
        sa.Column("decommissioned_at", sa.TIMESTAMP(timezone=True), nullable=False),
        *_ts(),
        _tenant_fk("decommission_records"),
        _asset_fk("decommission_records"),
        sa.ForeignKeyConstraint(
            ["replacement_asset_id"],
            ["assets.id"],
            ondelete="SET NULL",
            name="fk_decommission_records__replacement_asset_id",
        ),
        _member_fk("decommission_records", "decommissioned_by_membership_id"),
        sa.UniqueConstraint("tenant_id", "asset_id", name="uq_decommission_records__asset"),
    )
    op.create_index(
        "ix_decommission_records__tenant_id_asset_id",
        "decommission_records",
        ["tenant_id", "asset_id"],
    )

    op.create_table(
        "asset_transitions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("asset_id", _UUID, nullable=False),
        sa.Column("actor_membership_id", _UUID, nullable=True),
        sa.Column("field_changed", sa.Text(), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False),
        *_ts(),
        _tenant_fk("asset_transitions"),
        _asset_fk("asset_transitions"),
        _member_fk("asset_transitions", "actor_membership_id"),
    )
    op.create_index(
        "ix_asset_transitions__tenant_id_asset_id", "asset_transitions", ["tenant_id", "asset_id"]
    )

    # RLS + grants on every table (rule 12).
    for table in _TABLES:
        enable_rls(table)
        grant_crud(table)
    # asset_transitions is insert-only (rule 5 / ADR-0005): revoke UPDATE/DELETE and
    # attach the shared trigger, on top of the grant above.
    make_append_only("asset_transitions")

    op.execute(
        "INSERT INTO permissions (key, module, action) VALUES "
        "('assets:read', 'assets', 'read'), "
        "('assets:manage', 'assets', 'manage'), "
        "('assets:import', 'assets', 'import'), "
        "('assets:decommission', 'assets', 'decommission') ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM permissions WHERE key IN "
        "('assets:read', 'assets:manage', 'assets:import', 'assets:decommission')"
    )
    drop_append_only("asset_transitions")
    for table in reversed(_TABLES):
        disable_rls(table)
        op.drop_table(table)
