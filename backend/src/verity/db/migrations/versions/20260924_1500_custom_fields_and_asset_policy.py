"""Tenant-defined fields, and a review cadence the tenant sets.

Three things, one migration, because they ship as one settings screen:

``custom_field_definitions`` is the definition; the value lives in a
``custom_fields`` JSONB column on the record itself, so reading an asset is still
one row and a tenant that defines nothing pays nothing.

``asset_policies`` is the same shape as ``vendor_tiering_policies``: no row is
seeded, the code holds the defaults, and the row is the override. That is what
lets a review cadence be per criticality tier without a migration for every
tenant and without a nullable column on every asset.

Revision ID: d4a91c37e806
Revises: b3f7c81e5d24
Create Date: 2026-09-24
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.db.rls import disable_rls, enable_rls, grant_crud

revision: str = "d4a91c37e806"
down_revision: str | None = "b3f7c81e5d24"
branch_labels: str | None = None
depends_on: str | None = None

_UUID = postgresql.UUID(as_uuid=True)
_FIELDS = "custom_field_definitions"
_POLICY = "asset_policies"
_OBJECT_TYPES = ("asset", "vulnerability")
_FIELD_TYPES = ("text", "textarea", "number", "date", "select", "checkbox")
_VALUE_TABLES = ("assets", "vuln_instances")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def _ts() -> tuple[sa.Column[Any], sa.Column[Any]]:
    return (
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def upgrade() -> None:
    op.create_table(
        _FIELDS,
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("object_type", sa.Text(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("field_type", sa.Text(), server_default="text", nullable=False),
        sa.Column(
            "options", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False
        ),
        sa.Column("help_text", sa.Text(), nullable=True),
        sa.Column("required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("position", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("archived_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{_FIELDS}__tenant_id"
        ),
        sa.CheckConstraint(
            _in("object_type", _OBJECT_TYPES), name=conv(f"ck_{_FIELDS}__object_type_valid")
        ),
        sa.CheckConstraint(
            _in("field_type", _FIELD_TYPES), name=conv(f"ck_{_FIELDS}__field_type_valid")
        ),
        sa.CheckConstraint(
            "field_type <> 'select' OR jsonb_array_length(options) > 0",
            name=conv(f"ck_{_FIELDS}__select_has_options"),
        ),
        sa.UniqueConstraint("tenant_id", "object_type", "key", name=f"uq_{_FIELDS}__key"),
    )
    op.create_index(f"ix_{_FIELDS}__tenant_id_object_type", _FIELDS, ["tenant_id", "object_type"])
    enable_rls(_FIELDS)
    grant_crud(_FIELDS)

    for table in _VALUE_TABLES:
        op.add_column(
            table,
            sa.Column(
                "custom_fields",
                postgresql.JSONB(),
                server_default=sa.text("'{}'::jsonb"),
                nullable=False,
            ),
        )

    op.create_table(
        _POLICY,
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column(
            "review_cadence_days_by_tier",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{_POLICY}__tenant_id"
        ),
        # One policy per tenant. The override is a single row or it is nothing.
        sa.UniqueConstraint("tenant_id", name=f"uq_{_POLICY}__tenant_id"),
    )
    enable_rls(_POLICY)
    grant_crud(_POLICY)


def downgrade() -> None:
    disable_rls(_POLICY)
    op.drop_table(_POLICY)
    for table in _VALUE_TABLES:
        op.drop_column(table, "custom_fields")
    disable_rls(_FIELDS)
    op.drop_table(_FIELDS)
