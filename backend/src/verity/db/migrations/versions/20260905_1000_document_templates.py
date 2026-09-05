"""Shipped policy templates a tenant can start a document from.

Global content, like ``control_templates`` and ``frameworks``: one row per
shipped policy, shared by every tenant, so no ``tenant_id`` and no RLS policy
(rule 1 names ``*_templates`` as an exception). Instantiating one writes an
ordinary tenant-owned ``documents`` row, which is where tenancy applies.

The provenance columns are not decoration. This text is third-party content
under Apache 2.0, which allows commercial use and redistribution but requires
the licence, the attribution and a statement of changes. Carrying the repository,
the exact commit and the licence on every row means the platform can show a
customer where its policy came from, and an auditor asking "who wrote this"
gets a real answer.

Revision ID: e8a2c5f01d73
Revises: d7f1e3a94b62
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.db.rls import grant_crud

revision = "e8a2c5f01d73"
down_revision = "d7f1e3a94b62"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)
_TABLE = "document_templates"
_DOC_TYPES = ("policy", "standard", "procedure", "guideline", "charter")


def upgrade() -> None:
    joined = ", ".join(f"'{v}'" for v in _DOC_TYPES)
    op.create_table(
        _TABLE,
        sa.Column("id", _UUID, primary_key=True),
        #: Stable slug from the source filename. The idempotent key the seed
        #: loader upserts on, so re-running the seed updates rather than
        #: duplicates.
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("doc_type", sa.Text(), nullable=False, server_default="policy"),
        sa.Column(
            "classification", sa.Text(), nullable=False, server_default="internal"
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content_html", sa.Text(), nullable=False),
        sa.Column(
            "tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        #: {"SOC 2": ["CC6.1", ...]} — which criteria this policy speaks to, so
        #: an instantiated document can be linked to the controls that carry them.
        sa.Column(
            "satisfies", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        #: [{key, count, auto_filled}] — catalogued at build time so the editor
        #: can show what still needs deciding without re-parsing the body.
        sa.Column(
            "placeholders",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("optional_markers", sa.Integer(), nullable=False, server_default="0"),
        # -- provenance (Apache 2.0 attribution) ---------------------------------
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_commit", sa.Text(), nullable=True),
        sa.Column("license", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("key", name=f"uq_{_TABLE}__key"),
        sa.CheckConstraint(f"doc_type IN ({joined})", name=conv(f"ck_{_TABLE}__doc_type_valid")),
    )
    # No enable_rls: this is global content with no tenant column. The grant is
    # still needed so the application role can read it.
    grant_crud(_TABLE)

    # Which shipped template a document was started from, if any. Deliberately a
    # plain key and not a foreign key: the tenant's copy must survive the
    # template being retired upstream, and nothing about the document depends on
    # that row still existing. It is provenance, not a relationship.
    op.add_column("documents", sa.Column("template_key", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "template_key")
    op.drop_table(_TABLE)
