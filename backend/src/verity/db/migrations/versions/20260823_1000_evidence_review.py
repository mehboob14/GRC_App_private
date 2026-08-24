"""evidence review/approval, and drop the signed_attestation type

Revision ID: c5d9e1a72f80
Revises: b7e3a91c26d4
Create Date: 2026-08-23 10:00:00.000000

Two changes to the evidence library:

1. A review step. Evidence is a claim until someone signs off on it, so every
   item now carries ``review_status`` (pending → approved | rejected), the
   reviewer (a membership, SET NULL so a departure does not erase the record),
   when it was reviewed, and the reviewer's note. New and existing rows start
   ``pending``. Gated by a new ``evidence:review`` permission; Admin holds it
   automatically (decision 13 — Admin is every key that exists).

2. ``signed_attestation`` leaves the type vocabulary. Any existing rows of that
   type are moved to ``other`` before the CHECK is tightened. The UPDATE runs
   with FORCE ROW LEVEL SECURITY lifted, because it must touch every tenant's
   rows and the migration role is subject to the policy otherwise.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c5d9e1a72f80"
down_revision: str | None = "b7e3a91c26d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TYPES_NEW = (
    "screenshot",
    "configuration_export",
    "log_export",
    "policy_document",
    "training_record",
    "vendor_report",
    "ticket_record",
    "meeting_minutes",
    "other",
)
_TYPES_OLD = (*_TYPES_NEW, "signed_attestation")


def _type_check_sql(values: tuple[str, ...]) -> str:
    listed = ", ".join(f"'{v}'" for v in values)
    return f"evidence_type IN ({listed})"


def upgrade() -> None:
    # --- review columns ------------------------------------------------------
    op.add_column(
        "evidence",
        sa.Column(
            "review_status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
    )
    op.add_column("evidence", sa.Column("reviewed_by_membership_id", sa.Uuid(), nullable=True))
    op.add_column("evidence", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("evidence", sa.Column("review_note", sa.Text(), nullable=True))
    # Raw SQL for the named constraints: op.create_* re-applies the metadata
    # naming convention and would double-prefix these to ck_evidence__ck_...
    op.execute(
        "ALTER TABLE evidence ADD CONSTRAINT fk_evidence__reviewed_by_membership_id "
        "FOREIGN KEY (reviewed_by_membership_id) REFERENCES tenant_memberships (id) "
        "ON DELETE SET NULL"
    )
    op.execute(
        "ALTER TABLE evidence ADD CONSTRAINT ck_evidence__review_status_valid "
        "CHECK (review_status IN ('pending', 'approved', 'rejected'))"
    )

    # --- retire the signed_attestation type ----------------------------------
    op.execute("ALTER TABLE evidence NO FORCE ROW LEVEL SECURITY")
    op.execute(
        "UPDATE evidence SET evidence_type = 'other' WHERE evidence_type = 'signed_attestation'"
    )
    op.execute("ALTER TABLE evidence FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE evidence DROP CONSTRAINT ck_evidence__evidence_type_valid")
    op.execute(
        "ALTER TABLE evidence ADD CONSTRAINT ck_evidence__evidence_type_valid "
        f"CHECK ({_type_check_sql(_TYPES_NEW)})"
    )

    # --- permission ----------------------------------------------------------
    op.execute(
        sa.text(
            "INSERT INTO permissions (key, module, action) "
            "VALUES ('evidence:review', 'evidence', 'review') "
            "ON CONFLICT (key) DO NOTHING"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM role_permissions WHERE permission_key = 'evidence:review'"))
    op.execute(sa.text("DELETE FROM permissions WHERE key = 'evidence:review'"))

    op.execute("ALTER TABLE evidence DROP CONSTRAINT ck_evidence__evidence_type_valid")
    op.execute(
        "ALTER TABLE evidence ADD CONSTRAINT ck_evidence__evidence_type_valid "
        f"CHECK ({_type_check_sql(_TYPES_OLD)})"
    )

    op.execute("ALTER TABLE evidence DROP CONSTRAINT ck_evidence__review_status_valid")
    op.execute("ALTER TABLE evidence DROP CONSTRAINT fk_evidence__reviewed_by_membership_id")
    op.drop_column("evidence", "review_note")
    op.drop_column("evidence", "reviewed_at")
    op.drop_column("evidence", "reviewed_by_membership_id")
    op.drop_column("evidence", "review_status")
