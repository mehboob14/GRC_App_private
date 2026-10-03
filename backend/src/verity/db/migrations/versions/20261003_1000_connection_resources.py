"""What a connection can see, and which of it the checks look at (AU-9).

A GitHub token reaches every repository its owner can read. For a company that
is mostly the product. For a personal account it is also every fork, every piece
of coursework and every empty repository, and the control page judged all of
them: 92 repositories "failing" that nobody would ever be asked about.

``connection_resources`` is the inventory a run discovers, with the scope
decision beside each item. A person's decision is sticky; a system decision (an
archived repository, a fork) is re-derived on every run. An exclusion must carry
its reason, in the database as well as in the service, because an exclusion with
no reason is a repository quietly dropped from the audit.

``source``, ``external_id`` and ``synced_at`` are present from the first
migration (rule 9): this is the table a discovery connector fills.

Revision ID: e7b2a41c9d35
Revises: d4a91c37e806
Create Date: 2026-10-03
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.db.rls import disable_rls, enable_rls, grant_crud

revision: str = "e7b2a41c9d35"
down_revision: str | None = "d4a91c37e806"
branch_labels: str | None = None
depends_on: str | None = None

_UUID = postgresql.UUID(as_uuid=True)
_TABLE = "connection_resources"
_SCOPES = ("in_scope", "excluded")
_DECIDERS = ("system", "person")


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
        sa.Column("connection_id", _UUID, nullable=False),
        sa.Column("resource_type", sa.Text(), server_default="repository", nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column(
            "attributes", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("scope", sa.Text(), server_default="in_scope", nullable=False),
        sa.Column("scope_reason", sa.Text(), nullable=True),
        sa.Column("decided_by", sa.Text(), server_default="system", nullable=False),
        sa.Column("decided_by_membership_id", _UUID, nullable=True),
        sa.Column("decided_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "synced_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{_TABLE}__tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["connections.id"],
            ondelete="CASCADE",
            name=f"fk_{_TABLE}__connection_id",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by_membership_id"],
            ["tenant_memberships.id"],
            ondelete="SET NULL",
            name=f"fk_{_TABLE}__decided_by_membership_id",
        ),
        sa.CheckConstraint(_in("scope", _SCOPES), name=conv(f"ck_{_TABLE}__scope_valid")),
        sa.CheckConstraint(
            _in("decided_by", _DECIDERS), name=conv(f"ck_{_TABLE}__decided_by_valid")
        ),
        sa.CheckConstraint(
            "(scope <> 'excluded') OR (scope_reason IS NOT NULL)",
            name=conv(f"ck_{_TABLE}__exclusion_has_reason"),
        ),
        sa.UniqueConstraint(
            "tenant_id", "connection_id", "external_id", name=f"uq_{_TABLE}__external_id"
        ),
    )
    op.create_index(
        f"ix_{_TABLE}__tenant_id_connection_id_scope",
        _TABLE,
        ["tenant_id", "connection_id", "scope"],
    )
    enable_rls(_TABLE)
    grant_crud(_TABLE)


def downgrade() -> None:
    disable_rls(_TABLE)
    op.drop_table(_TABLE)
