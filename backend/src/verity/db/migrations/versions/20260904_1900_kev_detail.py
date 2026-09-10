"""Keep the KEV facts CISA already hands us.

``_fetch_kev`` downloads the whole known-exploited catalogue and keeps two fields
out of each row — the date added and the ransomware flag — then discards the
vendor, the product, the required action and the remediation due date. Those are
exactly the details that let a reader verify a KEV claim instead of taking the
badge on trust, and they cost nothing extra to store: the feed is already being
fetched and parsed.

``kev_due_at`` is stored and displayed only. It is CISA's own remediation
deadline for federal agencies, which is a second clock alongside ``sla_due_at``
and would change what "overdue" means on the register — that is a product
decision, so nothing computes against this column yet.

No new table, so no RLS policy: ``vuln_definitions`` already carries one.

Revision ID: d7f1e3a94b62
Revises: c5d92a68b31f
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d7f1e3a94b62"
down_revision = "c5d92a68b31f"
branch_labels = None
depends_on = None

_TABLE = "vuln_definitions"
_COLUMNS = ("kev_vendor", "kev_product", "kev_required_action")


def upgrade() -> None:
    for name in _COLUMNS:
        op.add_column(_TABLE, sa.Column(name, sa.Text(), nullable=True))
    op.add_column(_TABLE, sa.Column("kev_due_at", sa.TIMESTAMP(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column(_TABLE, "kev_due_at")
    for name in reversed(_COLUMNS):
        op.drop_column(_TABLE, name)
