"""Assurance records and findings; documents approved outside Verity.

Phase 7 of the guided onboarding change (tasks 7.1, 7.2, 7.5; EN-9, EN-10, CN-5, EX-2, EX-4,
RD-4, D-11). Both new tables are tenant owned with forced RLS in this migration, amended in place
and audited, no DELETE grant. ``documents`` gains two nullable columns.

Revision ID: 2c7d9e4f6a18
Revises: 8a4f2c6e1b37
Create Date: 2026-11-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.db.rls import disable_rls, enable_rls, grant_crud, revoke_delete

revision: str = "2c7d9e4f6a18"
down_revision: str | None = "8a4f2c6e1b37"
branch_labels: str | None = None
depends_on: str | None = None

_UUID = postgresql.UUID(as_uuid=True)
_KINDS = (
    "internal_audit",
    "management_review",
    "external_stage",
    "prior_report",
    "prior_certificate",
)
_STATUSES = ("planned", "held", "closed")
_GRADES = ("major", "minor", "observation", "exception")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN (" + ", ".join(repr(v) for v in values) + ")"


def _base(table: str) -> list[sa.SchemaItem]:
    return [
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{table}__tenant_id"
        ),
    ]


def _fk(table: str, column: str, target: str, ondelete: str = "SET NULL") -> sa.SchemaItem:
    return sa.ForeignKeyConstraint(
        [column], [f"{target}.id"], ondelete=ondelete, name=f"fk_{table}__{column}"
    )


def upgrade() -> None:
    t = "assurance_records"
    op.create_table(
        t,
        *_base(t),
        sa.Column("engagement_id", _UUID, nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("performed_by_membership_id", _UUID, nullable=True),
        sa.Column("performed_by_name", sa.Text(), nullable=True),
        sa.Column("performed_by_firm", sa.Text(), nullable=True),
        sa.Column("independence_confirmed_by_membership_id", _UUID, nullable=True),
        sa.Column("scope_note", sa.Text(), nullable=True),
        sa.Column("document_id", _UUID, nullable=True),
        sa.Column(
            "inputs", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("status", sa.Text(), server_default=sa.text("'planned'"), nullable=False),
        _fk(t, "engagement_id", "engagements", "RESTRICT"),
        _fk(t, "performed_by_membership_id", "tenant_memberships"),
        _fk(t, "independence_confirmed_by_membership_id", "tenant_memberships"),
        _fk(t, "document_id", "documents"),
        sa.CheckConstraint(_in("kind", _KINDS), name=op.f(f"ck_{t}__kind_valid")),
        sa.CheckConstraint(_in("status", _STATUSES), name=op.f(f"ck_{t}__status_valid")),
    )
    op.create_index(
        f"ix_{t}__tenant_id_engagement_id_kind", t, ["tenant_id", "engagement_id", "kind"]
    )

    t = "assurance_findings"
    op.create_table(
        t,
        *_base(t),
        sa.Column("record_id", _UUID, nullable=False),
        sa.Column("grade", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("owner_membership_id", _UUID, nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("task_id", _UUID, nullable=True),
        sa.Column("closed_on", sa.Date(), nullable=True),
        sa.Column("closure_evidence_id", _UUID, nullable=True),
        sa.Column("verified_on", sa.Date(), nullable=True),
        sa.Column("verified_by_membership_id", _UUID, nullable=True),
        _fk(t, "record_id", "assurance_records", "RESTRICT"),
        _fk(t, "owner_membership_id", "tenant_memberships"),
        _fk(t, "task_id", "tasks"),
        _fk(t, "closure_evidence_id", "evidence"),
        _fk(t, "verified_by_membership_id", "tenant_memberships"),
        sa.CheckConstraint(_in("grade", _GRADES), name=op.f(f"ck_{t}__grade_valid")),
        sa.CheckConstraint("length(btrim(summary)) > 0", name=op.f(f"ck_{t}__summary_present")),
    )
    op.create_index(f"ix_{t}__tenant_id_record_id", t, ["tenant_id", "record_id"])

    for table in ("assurance_records", "assurance_findings"):
        enable_rls(table)
        grant_crud(table)
        revoke_delete(table)

    op.add_column("documents", sa.Column("approved_elsewhere_on", sa.Date(), nullable=True))
    op.add_column(
        "documents", sa.Column("approved_elsewhere_by_membership_id", _UUID, nullable=True)
    )
    op.create_foreign_key(
        "fk_documents__approved_elsewhere_by_membership_id",
        "documents",
        "tenant_memberships",
        ["approved_elsewhere_by_membership_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_documents__approved_elsewhere_by_membership_id", "documents", type_="foreignkey"
    )
    op.drop_column("documents", "approved_elsewhere_by_membership_id")
    op.drop_column("documents", "approved_elsewhere_on")
    for table in ("assurance_findings", "assurance_records"):
        disable_rls(table)
        op.drop_table(table)
