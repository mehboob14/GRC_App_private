"""Declared dependencies between assets (A8).

The asset detail has had a Relationships tab since the module shipped, and
nothing behind it: "Add dependency" reached a client stub that threw, so the
screen answered a declared dependency with "try again, or contact support".

One row per edge, stored once and read from both ends. Storing the inverse as a
second row would let the two disagree, and disagreeing edges are worse than no
edges when the question is blast radius.

``source``/``external_id``/``synced_at`` are here from the first migration
because this is exactly the table a discovery connector fills (rule 9), and
``provenance`` keeps a person's claim distinguishable from a scanner's
observation.

Revision ID: b3f7c81e5d24
Revises: 9f2d1a7c6b40
Create Date: 2026-09-24
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.db.rls import disable_rls, enable_rls, grant_crud

revision: str = "b3f7c81e5d24"
down_revision: str | None = "9f2d1a7c6b40"
branch_labels: str | None = None
depends_on: str | None = None

_UUID = postgresql.UUID(as_uuid=True)
_TABLE = "asset_relationships"
_TYPES = ("depends_on", "runs_on", "contains", "connects_to", "processes_data_for")
_PROVENANCE = ("declared", "discovered")


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
        _TABLE,
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("source_asset_id", _UUID, nullable=False),
        sa.Column("target_asset_id", _UUID, nullable=False),
        sa.Column("relationship_type", sa.Text(), nullable=False),
        sa.Column("provenance", sa.Text(), server_default="declared", nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_membership_id", _UUID, nullable=True),
        sa.Column("source", sa.Text(), server_default="manual", nullable=False),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{_TABLE}__tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["source_asset_id"],
            ["assets.id"],
            ondelete="CASCADE",
            name=f"fk_{_TABLE}__source_asset_id",
        ),
        sa.ForeignKeyConstraint(
            ["target_asset_id"],
            ["assets.id"],
            ondelete="CASCADE",
            name=f"fk_{_TABLE}__target_asset_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_membership_id"],
            ["tenant_memberships.id"],
            ondelete="SET NULL",
            name=f"fk_{_TABLE}__created_by_membership_id",
        ),
        sa.CheckConstraint(
            _in("relationship_type", _TYPES), name=conv(f"ck_{_TABLE}__relationship_type_valid")
        ),
        sa.CheckConstraint(
            _in("provenance", _PROVENANCE), name=conv(f"ck_{_TABLE}__provenance_valid")
        ),
        # An asset cannot depend on itself, and the same edge is one row however
        # many times somebody declares it.
        sa.CheckConstraint(
            "source_asset_id <> target_asset_id", name=conv(f"ck_{_TABLE}__no_self_edge")
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "source_asset_id",
            "target_asset_id",
            "relationship_type",
            name=f"uq_{_TABLE}__edge",
        ),
        sa.UniqueConstraint("tenant_id", "source", "external_id", name=f"uq_{_TABLE}__external_id"),
    )
    op.create_index(
        f"ix_{_TABLE}__tenant_id_source_asset_id", _TABLE, ["tenant_id", "source_asset_id"]
    )
    op.create_index(
        f"ix_{_TABLE}__tenant_id_target_asset_id", _TABLE, ["tenant_id", "target_asset_id"]
    )
    enable_rls(_TABLE)
    grant_crud(_TABLE)


def downgrade() -> None:
    disable_rls(_TABLE)
    op.drop_table(_TABLE)
