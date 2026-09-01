"""Document acknowledgement campaigns: a targeted read-and-sign flow.

Three tenant-owned, RLS-forced tables (rules 1, 2, 12). A campaign is raised against
a document; recipients are resolved (from users, roles and groups) into one row each,
carrying their pending/acknowledged status; comments (with @-mentions) hang off the
campaign. No new permission keys — the owner's actions are ``documents:manage``, a
recipient's acknowledgement is ``documents:read``, which the built-in Admin resolves.

Revision ID: b8c2d4e6f019
Revises: f3b9c1a20e57
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.db.rls import disable_rls, enable_rls, grant_crud

revision = "b8c2d4e6f019"
down_revision = "f3b9c1a20e57"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)

_CAMPAIGN_STATUSES = ("active", "closed")
_RECIPIENT_KINDS = ("reviewer", "approver")
_RECIPIENT_SOURCES = ("user", "role", "group")
_RECIPIENT_STATUSES = ("pending", "acknowledged")

# Dropped children-first.
_TABLES = (
    "document_ack_campaign_comments",
    "document_ack_campaign_recipients",
    "document_ack_campaigns",
)


def _ts() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def _in(table: str, column: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    joined = ", ".join(f"'{v}'" for v in values)
    return sa.CheckConstraint(f"{column} IN ({joined})", name=conv(f"ck_{table}__{column}_valid"))


def _tenant_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{table}__tenant_id"
    )


def _member_fk(table: str, column: str, *, ondelete: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], ["tenant_memberships.id"], ondelete=ondelete, name=f"fk_{table}__{column}"
    )


def upgrade() -> None:
    op.create_table(
        "document_ack_campaigns",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("document_id", _UUID, nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_by_membership_id", _UUID, nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'")),
        sa.Column("due_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_ts(),
        _tenant_fk("document_ack_campaigns"),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], ondelete="CASCADE",
            name="fk_document_ack_campaigns__document_id",
        ),
        _member_fk("document_ack_campaigns", "created_by_membership_id", ondelete="SET NULL"),
        _in("document_ack_campaigns", "status", _CAMPAIGN_STATUSES),
    )
    op.create_index(
        "ix_document_ack_campaigns__tenant_id_document_id",
        "document_ack_campaigns",
        ["tenant_id", "document_id"],
    )

    op.create_table(
        "document_ack_campaign_recipients",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("campaign_id", _UUID, nullable=False),
        sa.Column("membership_id", _UUID, nullable=False),
        sa.Column("kind", sa.Text(), nullable=False, server_default=sa.text("'reviewer'")),
        sa.Column("source", sa.Text(), nullable=False, server_default=sa.text("'user'")),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("acknowledged_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("ack_comment", sa.Text(), nullable=True),
        *_ts(),
        _tenant_fk("document_ack_campaign_recipients"),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["document_ack_campaigns.id"], ondelete="CASCADE",
            name="fk_document_ack_campaign_recipients__campaign_id",
        ),
        _member_fk("document_ack_campaign_recipients", "membership_id", ondelete="CASCADE"),
        _in("document_ack_campaign_recipients", "kind", _RECIPIENT_KINDS),
        _in("document_ack_campaign_recipients", "source", _RECIPIENT_SOURCES),
        _in("document_ack_campaign_recipients", "status", _RECIPIENT_STATUSES),
        sa.UniqueConstraint(
            "tenant_id", "campaign_id", "membership_id",
            name="uq_document_ack_campaign_recipients__member",
        ),
    )
    op.create_index(
        "ix_document_ack_campaign_recipients__tenant_id_membership_id",
        "document_ack_campaign_recipients",
        ["tenant_id", "membership_id"],
    )

    op.create_table(
        "document_ack_campaign_comments",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("campaign_id", _UUID, nullable=False),
        sa.Column("author_membership_id", _UUID, nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "mentioned_ids", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        *_ts(),
        _tenant_fk("document_ack_campaign_comments"),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["document_ack_campaigns.id"], ondelete="CASCADE",
            name="fk_document_ack_campaign_comments__campaign_id",
        ),
        _member_fk("document_ack_campaign_comments", "author_membership_id", ondelete="SET NULL"),
    )
    op.create_index(
        "ix_document_ack_campaign_comments__tenant_id_campaign_id",
        "document_ack_campaign_comments",
        ["tenant_id", "campaign_id"],
    )

    for table in reversed(_TABLES):
        enable_rls(table)
        grant_crud(table)


def downgrade() -> None:
    for table in _TABLES:
        disable_rls(table)
        op.drop_table(table)
