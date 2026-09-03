"""Vulnerability assignment targets: assign a finding to users, roles or groups.

A finding could previously only inherit an owner from its asset — there was no
way to (re)assign one at all, which quietly blocked remediation-plan approval
and SLA escalation. ``vuln_instances.owner_membership_id`` stays the single
accountable owner; this table records the additional people, roles and groups a
triager put on the finding, mirroring ``document_approval_targets``.

Revision ID: b3c81f47a205
Revises: afedee6a313a
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.db.rls import disable_rls, enable_rls, grant_crud

revision = "b3c81f47a205"
down_revision = "afedee6a313a"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)
_TARGET_TYPES = ("user", "role", "group")
_TABLE = "vuln_assignment_targets"


def _ts() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def upgrade() -> None:
    joined = ", ".join(f"'{v}'" for v in _TARGET_TYPES)
    op.create_table(
        _TABLE,
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("instance_id", _UUID, nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", _UUID, nullable=False),
        sa.Column("target_name", sa.Text(), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{_TABLE}__tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["instance_id"],
            ["vuln_instances.id"],
            ondelete="CASCADE",
            name=f"fk_{_TABLE}__instance_id",
        ),
        sa.CheckConstraint(
            f"target_type IN ({joined})", name=conv(f"ck_{_TABLE}__target_type_valid")
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "instance_id",
            "target_type",
            "target_id",
            name=f"uq_{_TABLE}__target",
        ),
    )
    op.create_index(
        f"ix_{_TABLE}__tenant_id_instance_id", _TABLE, ["tenant_id", "instance_id"]
    )
    enable_rls(_TABLE)
    grant_crud(_TABLE)


def downgrade() -> None:
    disable_rls(_TABLE)
    op.drop_index(f"ix_{_TABLE}__tenant_id_instance_id", table_name=_TABLE)
    op.drop_table(_TABLE)
