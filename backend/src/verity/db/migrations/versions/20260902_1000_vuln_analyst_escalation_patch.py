"""vulnerabilities — analyst content, exception hardening, SLA escalation, patch intel

Revision ID: d1f4a6b82c31
Revises: c9e3f5a71b20
Create Date: 2026-09-02 10:00:00.000000

Additive columns for Deliverable 1.3 gaps (spec 126/128/130): per-instance analyst
content (evidence, reproduction_steps, resolution_notes), compensating controls +
SLA-escalation tracking on the instance, and vendor-patch-intelligence on the
definition. All nullable / defaulted — no RLS change (the tables are already
TenantScoped + forced), no backfill.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d1f4a6b82c31"
down_revision: str | None = "c9e3f5a71b20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INSTANCE_COLS = (
    "evidence",
    "reproduction_steps",
    "resolution_notes",
    "compensating_controls",
    "escalated_at",
    "escalated_to_membership_id",
    "escalation_level",
)
_DEFINITION_COLS = (
    "patch_available",
    "fixed_versions",
    "advisory_url",
    "patch_source",
    "patch_checked_at",
)


def upgrade() -> None:
    # vuln_instances: analyst content + exception + escalation
    op.add_column("vuln_instances", sa.Column("evidence", sa.Text(), nullable=True))
    op.add_column("vuln_instances", sa.Column("reproduction_steps", sa.Text(), nullable=True))
    op.add_column("vuln_instances", sa.Column("resolution_notes", sa.Text(), nullable=True))
    op.add_column("vuln_instances", sa.Column("compensating_controls", sa.Text(), nullable=True))
    op.add_column(
        "vuln_instances",
        sa.Column("escalation_level", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "vuln_instances", sa.Column("escalated_at", sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.add_column(
        "vuln_instances",
        sa.Column("escalated_to_membership_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_vuln_instances__escalated_to_membership_id",
        "vuln_instances",
        "tenant_memberships",
        ["escalated_to_membership_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # vuln_definitions: vendor patch intelligence
    op.add_column("vuln_definitions", sa.Column("patch_available", sa.Boolean(), nullable=True))
    op.add_column("vuln_definitions", sa.Column("fixed_versions", sa.Text(), nullable=True))
    op.add_column("vuln_definitions", sa.Column("advisory_url", sa.Text(), nullable=True))
    op.add_column("vuln_definitions", sa.Column("patch_source", sa.Text(), nullable=True))
    op.add_column(
        "vuln_definitions",
        sa.Column("patch_checked_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    for col in _DEFINITION_COLS:
        op.drop_column("vuln_definitions", col)
    op.drop_constraint(
        "fk_vuln_instances__escalated_to_membership_id", "vuln_instances", type_="foreignkey"
    )
    for col in _INSTANCE_COLS:
        op.drop_column("vuln_instances", col)
