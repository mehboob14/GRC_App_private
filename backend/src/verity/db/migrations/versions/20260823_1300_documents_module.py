"""documents module — library, append-only versions, links, workflow, acks

Revision ID: f3b6d20c48a1
Revises: e1a7c93d820b
Create Date: 2026-08-23 13:00:00.000000

Six tenant-owned tables, so RLS + grants land with them (rule 12).
``document_versions`` is append-only (rule 5 / ADR-0005) — revoked grant plus
the shared BEFORE UPDATE OR DELETE trigger. Seeds the four documents:* keys.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.db.rls import disable_rls, drop_append_only, enable_rls, grant_crud, make_append_only

revision: str = "f3b6d20c48a1"
down_revision: str | None = "e1a7c93d820b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DOC_TYPES = ("policy", "standard", "procedure", "guideline", "charter")
CLASSIFICATIONS = ("public", "internal", "confidential", "restricted")
LIFECYCLES = ("draft", "needs_approval", "approved", "published", "expired", "archived")
CONTENT_FORMATS = ("html", "pdf", "docx")
CHANGE_TYPES = ("major", "minor", "patch")
APPROVAL_STATUSES = ("not_started", "pending", "approved", "rejected")

_TABLES = (
    "document_acknowledgements",
    "document_approvals",
    "document_frameworks",
    "document_controls",
    "document_versions",
    "documents",
)


def _in(column: str, allowed: tuple[str, ...]) -> str:
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


def _tenant_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id"], ["tenants.id"], name=op.f(f"fk_{table}__tenant_id"), ondelete="CASCADE"
    )


def _doc_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["document_id"], ["documents.id"], name=op.f(f"fk_{table}__document_id"), ondelete="CASCADE"
    )


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("doc_type", sa.Text(), nullable=False),
        sa.Column("classification", sa.Text(), nullable=False),
        sa.Column("lifecycle", sa.Text(), nullable=False),
        sa.Column("content_format", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=True),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_membership_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_to", sa.Text(), nullable=True),
        sa.Column("renewal_date", sa.Date(), nullable=True),
        sa.Column("approved_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("published_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("archived_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("archived_reason", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("synced_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        *_timestamps(),
        _tenant_fk("documents"),
        sa.ForeignKeyConstraint(
            ["owner_membership_id"],
            ["tenant_memberships.id"],
            name=op.f("fk_documents__owner_membership_id"),
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(_in("doc_type", DOC_TYPES), name=op.f("ck_documents__doc_type_valid")),
        sa.CheckConstraint(
            _in("classification", CLASSIFICATIONS), name=op.f("ck_documents__classification_valid")
        ),
        sa.CheckConstraint(
            _in("lifecycle", LIFECYCLES), name=op.f("ck_documents__lifecycle_valid")
        ),
        sa.CheckConstraint(
            _in("content_format", CONTENT_FORMATS),
            name=op.f("ck_documents__content_format_valid"),
        ),
        sa.CheckConstraint(
            "(archived_at IS NULL) = (archived_reason IS NULL)",
            name=op.f("ck_documents__archived_has_reason"),
        ),
        sa.UniqueConstraint("tenant_id", "code", name="uq_documents__tenant_code"),
    )
    op.create_index("ix_documents__tenant_id_lifecycle", "documents", ["tenant_id", "lifecycle"])
    op.create_index(
        "ix_documents__tenant_id_renewal_date", "documents", ["tenant_id", "renewal_date"]
    )
    op.create_index(
        "uq_documents__tenant_source_external",
        "documents",
        ["tenant_id", "source", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    enable_rls("documents")
    grant_crud("documents")

    op.create_table(
        "document_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_no", sa.Text(), nullable=False),
        sa.Column("change_type", sa.Text(), nullable=False),
        sa.Column("content_format", sa.Text(), nullable=False),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("object_key", sa.Text(), nullable=True),
        sa.Column("filename", sa.Text(), nullable=True),
        sa.Column("content_type", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_by_membership_id", postgresql.UUID(as_uuid=True), nullable=True),
        *_timestamps(),
        _tenant_fk("document_versions"),
        _doc_fk("document_versions"),
        sa.ForeignKeyConstraint(
            ["created_by_membership_id"],
            ["tenant_memberships.id"],
            name=op.f("fk_document_versions__created_by_membership_id"),
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            _in("change_type", CHANGE_TYPES), name=op.f("ck_document_versions__change_type_valid")
        ),
        sa.CheckConstraint(
            _in("content_format", CONTENT_FORMATS),
            name=op.f("ck_document_versions__content_format_valid"),
        ),
        sa.UniqueConstraint(
            "tenant_id", "document_id", "version_no", name="uq_document_versions__doc_version"
        ),
    )
    op.create_index(
        "ix_document_versions__tenant_id_document_id",
        "document_versions",
        ["tenant_id", "document_id"],
    )
    enable_rls("document_versions")
    grant_crud("document_versions")
    make_append_only("document_versions")

    _link_table("document_controls", "control_id", "controls.id", "CASCADE")
    _link_table("document_frameworks", "framework_id", "frameworks.id", "RESTRICT")

    op.create_table(
        "document_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("approver_membership_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        *_timestamps(),
        _tenant_fk("document_approvals"),
        _doc_fk("document_approvals"),
        sa.ForeignKeyConstraint(
            ["approver_membership_id"],
            ["tenant_memberships.id"],
            name=op.f("fk_document_approvals__approver_membership_id"),
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            _in("status", APPROVAL_STATUSES), name=op.f("ck_document_approvals__status_valid")
        ),
        sa.UniqueConstraint("tenant_id", "document_id", "tier", name="uq_document_approvals__tier"),
    )
    op.create_index(
        "ix_document_approvals__tenant_id_document_id",
        "document_approvals",
        ["tenant_id", "document_id"],
    )
    enable_rls("document_approvals")
    grant_crud("document_approvals")

    op.create_table(
        "document_acknowledgements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("membership_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "acknowledged_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        *_timestamps(),
        _tenant_fk("document_acknowledgements"),
        _doc_fk("document_acknowledgements"),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["document_versions.id"],
            name=op.f("fk_document_acknowledgements__version_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["membership_id"],
            ["tenant_memberships.id"],
            name=op.f("fk_document_acknowledgements__membership_id"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "tenant_id", "document_id", "membership_id", name="uq_document_acknowledgements"
        ),
    )
    op.create_index(
        "ix_document_acknowledgements__tenant_id_document_id",
        "document_acknowledgements",
        ["tenant_id", "document_id"],
    )
    enable_rls("document_acknowledgements")
    grant_crud("document_acknowledgements")

    op.execute(
        "INSERT INTO permissions (key, module, action) VALUES "
        "('documents:read', 'documents', 'read'), "
        "('documents:manage', 'documents', 'manage'), "
        "('documents:approve', 'documents', 'approve'), "
        "('documents:publish', 'documents', 'publish') ON CONFLICT DO NOTHING"
    )


def _link_table(table: str, ref_col: str, ref: str, on_delete: str) -> None:
    op.create_table(
        table,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(ref_col, postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
        _tenant_fk(table),
        _doc_fk(table),
        sa.ForeignKeyConstraint(
            [ref_col], [ref], name=op.f(f"fk_{table}__{ref_col}"), ondelete=on_delete
        ),
        sa.UniqueConstraint("tenant_id", "document_id", ref_col, name=f"uq_{table}"),
    )
    op.create_index(f"ix_{table}__tenant_id_document_id", table, ["tenant_id", "document_id"])
    op.create_index(f"ix_{table}__tenant_id_{ref_col}", table, ["tenant_id", ref_col])
    enable_rls(table)
    grant_crud(table)


def downgrade() -> None:
    op.execute(
        "DELETE FROM permissions WHERE key IN "
        "('documents:read','documents:manage','documents:approve','documents:publish')"
    )
    drop_append_only("document_versions")
    for table in _TABLES:
        disable_rls(table)
        op.drop_table(table)
