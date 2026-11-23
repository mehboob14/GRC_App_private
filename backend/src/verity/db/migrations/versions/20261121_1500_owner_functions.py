"""Owner functions: which member holds each of the eight owner functions.

Phase 4 of the guided onboarding change (tasks 4.1 to 4.3; requirements OW-1, OW-2). Tenant owned,
forced RLS in this migration, one row per function, reassigned in place and audited; the app role
gets no DELETE.

Revision ID: 9bc3f6a9db0c
Revises: 438b8c525629
Create Date: 2026-11-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.db.rls import disable_rls, enable_rls, grant_crud, revoke_delete

revision: str = "9bc3f6a9db0c"
down_revision: str | None = "438b8c525629"
branch_labels: str | None = None
depends_on: str | None = None

_UUID = postgresql.UUID(as_uuid=True)
_KEYS = (
    "executive_sponsor",
    "security_lead",
    "engineering_lead",
    "it_lead",
    "hr_lead",
    "legal_privacy_lead",
    "vendor_lead",
    "finance_lead",
)


def upgrade() -> None:
    op.create_table(
        "owner_functions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("function_key", sa.Text(), nullable=False),
        sa.Column("membership_id", _UUID, nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name="fk_owner_functions__tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["membership_id"],
            ["tenant_memberships.id"],
            ondelete="SET NULL",
            name="fk_owner_functions__membership_id",
        ),
        sa.CheckConstraint(
            "function_key IN (" + ", ".join(repr(k) for k in _KEYS) + ")",
            name=op.f("ck_owner_functions__function_key_valid"),
        ),
    )
    op.create_index(
        "uq_owner_functions__tenant_id_function_key",
        "owner_functions",
        ["tenant_id", "function_key"],
        unique=True,
    )
    enable_rls("owner_functions")
    grant_crud("owner_functions")
    revoke_delete("owner_functions")


def downgrade() -> None:
    disable_rls("owner_functions")
    op.drop_table("owner_functions")
