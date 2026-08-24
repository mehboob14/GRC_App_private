"""control_type is optional, and never asserted for shipped framework controls

Revision ID: b7e3a91c26d4
Revises: a4c8e2f60b13
Create Date: 2026-08-18 12:00:00.000000

Preventive / Detective / Corrective is a statement about how *an organisation*
designed a control. It is not part of the SOC 2 Trust Services Criteria and the
AICPA does not classify the criteria that way, so asserting it on the 114
shipped templates put a claim in front of an auditor that no source supports.

The column stays — a tenant classifying its own internal or custom controls is
exactly what it is for — but it becomes nullable and is cleared on the shipped
content and on every control instantiated from it.

The existing CHECK needs no change: ``control_type IN (...)`` evaluates to NULL
for a NULL column, and a CHECK passes unless it is false.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7e3a91c26d4"
down_revision: str | None = "a4c8e2f60b13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("control_templates", "control_type", existing_type=sa.String(), nullable=True)
    op.alter_column("controls", "control_type", existing_type=sa.String(), nullable=True)
    # Shipped content carries no type.
    op.execute("UPDATE control_templates SET control_type = NULL WHERE built_in IS TRUE")
    # `controls` is tenant-owned with FORCE row-level security and neither
    # verity_owner nor verity_app holds BYPASSRLS, so a bare UPDATE here matches
    # zero rows and still reports success — worse than failing. The provider
    # policies are SELECT-only, so lift FORCE for the statement instead: the
    # owner then bypasses RLS, and FORCE goes straight back on.
    op.execute("ALTER TABLE controls NO FORCE ROW LEVEL SECURITY")
    op.execute("UPDATE controls SET control_type = NULL WHERE origin = 'template'")
    op.execute("ALTER TABLE controls FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    # NOT NULL cannot come back while rows hold NULL. 'Preventive' is the modal
    # value of the classification this migration removed — restoring it is
    # lossy by nature, which is the point: the data was not real.
    op.execute(
        "UPDATE control_templates SET control_type = 'Preventive' WHERE control_type IS NULL"
    )
    op.execute("ALTER TABLE controls NO FORCE ROW LEVEL SECURITY")
    op.execute("UPDATE controls SET control_type = 'Preventive' WHERE control_type IS NULL")
    op.execute("ALTER TABLE controls FORCE ROW LEVEL SECURITY")
    op.alter_column("controls", "control_type", existing_type=sa.String(), nullable=False)
    op.alter_column("control_templates", "control_type", existing_type=sa.String(), nullable=False)
