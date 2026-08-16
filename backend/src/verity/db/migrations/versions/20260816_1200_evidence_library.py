"""evidence library — items, their file/link payload, and control mappings

Revision ID: c9e3a7b52f41
Revises: b4d8f16c2e07
Create Date: 2026-08-16 12:00:00.000000

Two tenant-owned tables, so RLS and grants land here with them (rule 12).

No ``is_stale`` column, deliberately (D14): freshness is derived from
``renewal_date`` at read time. A stored flag is wrong within a day of the job
that wrote it, and would have to be recomputed on a schedule to stay honest.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.db.rls import enable_rls, grant_crud

revision: str = "c9e3a7b52f41"
down_revision: str | None = "b4d8f16c2e07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EVIDENCE_KINDS = ("file", "link")
EVIDENCE_TYPES = (
    "screenshot",
    "configuration_export",
    "log_export",
    "policy_document",
    "signed_attestation",
    "training_record",
    "vendor_report",
    "ticket_record",
    "meeting_minutes",
    "other",
)


def _in_list(column: str, allowed: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in allowed)})"


def _timestamps() -> tuple[sa.Column[Any], sa.Column[Any]]:
    return (
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def upgrade() -> None:
    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("evidence_type", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("source_label", sa.Text(), nullable=True),
        sa.Column("owner_membership_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("collected_at", sa.Date(), nullable=False),
        sa.Column("renewal_date", sa.Date(), nullable=True),
        sa.Column("object_key", sa.Text(), nullable=True),
        sa.Column("filename", sa.Text(), nullable=True),
        sa.Column("content_type", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.Text(), nullable=True),
        sa.Column("link_url", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("synced_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("fk_evidence__tenant_id"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["owner_membership_id"],
            ["tenant_memberships.id"],
            name=op.f("fk_evidence__owner_membership_id"),
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(_in_list("kind", EVIDENCE_KINDS), name=op.f("ck_evidence__kind_valid")),
        sa.CheckConstraint(
            _in_list("evidence_type", EVIDENCE_TYPES), name=op.f("ck_evidence__evidence_type_valid")
        ),
        # A file must hold its bytes and their hash; a link must hold its URL.
        sa.CheckConstraint(
            "(kind = 'file') = (object_key IS NOT NULL AND sha256 IS NOT NULL)",
            name="ck_evidence__file_has_object_and_hash",
        ),
        sa.CheckConstraint(
            "(kind = 'link') = (link_url IS NOT NULL)", name="ck_evidence__link_has_url"
        ),
        sa.CheckConstraint(
            "renewal_date IS NULL OR renewal_date >= collected_at",
            name="ck_evidence__renewal_after_collection",
        ),
    )
    op.create_index(
        "ix_evidence__tenant_id_renewal_date", "evidence", ["tenant_id", "renewal_date"]
    )
    op.create_index(
        "ix_evidence__tenant_id_evidence_type", "evidence", ["tenant_id", "evidence_type"]
    )
    op.create_index(
        "uq_evidence__tenant_source_external",
        "evidence",
        ["tenant_id", "source", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    enable_rls("evidence")
    grant_crud("evidence")

    op.create_table(
        "evidence_controls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("control_id", postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_evidence_controls__tenant_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.id"],
            name=op.f("fk_evidence_controls__evidence_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["control_id"],
            ["controls.id"],
            name=op.f("fk_evidence_controls__control_id"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("tenant_id", "evidence_id", "control_id", name="uq_evidence_controls"),
    )
    op.create_index(
        "ix_evidence_controls__tenant_id_control_id",
        "evidence_controls",
        ["tenant_id", "control_id"],
    )
    op.create_index(
        "ix_evidence_controls__tenant_id_evidence_id",
        "evidence_controls",
        ["tenant_id", "evidence_id"],
    )
    enable_rls("evidence_controls")
    grant_crud("evidence_controls")

    op.execute(
        "INSERT INTO permissions (key, module, action) VALUES "
        "('evidence:read', 'evidence', 'read'), "
        "('evidence:manage', 'evidence', 'manage') ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DELETE FROM permissions WHERE key IN ('evidence:read','evidence:manage')")
    op.drop_table("evidence_controls")
    op.drop_table("evidence")
