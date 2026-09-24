"""Reviewing an assessment together: domains assigned, in parallel.

The questionnaire comes back as one object with ten risk domains in it, and one
person reads the lot. Security should be reading the access-control answers while
legal reads the contract ones, and each should be able to say "I am done with
mine" without either waiting for the other.

``vendor_assessment_reviewers`` is that: one row per domain handed to a person,
with its own state. It is deliberately not a column on the assessment, because
the whole point is that several of them are open at once.

Comments need no table. ``vendor_assessment_comments`` shipped in week 5 with the
visibility column the portal needs; nothing wrote to it until now.

Revision ID: 5c93b7e2a481
Revises: 8a1f4c26d05b
Create Date: 2026-09-23
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.db.rls import disable_rls, enable_rls, grant_crud

revision: str = "5c93b7e2a481"
down_revision: str | None = "8a1f4c26d05b"
branch_labels: str | None = None
depends_on: str | None = None

_UUID = postgresql.UUID(as_uuid=True)
_TABLE = "vendor_assessment_reviewers"
_STATUSES = ("assigned", "in_review", "done")


def _ts() -> tuple[sa.Column[Any], sa.Column[Any]]:
    return (
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("assessment_id", _UUID, nullable=False),
        # Null means the whole review rather than one domain, which is how a
        # small team delegates: "you take this one, all of it".
        sa.Column("domain", sa.Text(), nullable=True),
        sa.Column("reviewer_membership_id", _UUID, nullable=False),
        sa.Column("status", sa.Text(), server_default="assigned", nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("assigned_by_membership_id", _UUID, nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{_TABLE}__tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["vendor_assessments.id"],
            ondelete="CASCADE",
            name=f"fk_{_TABLE}__assessment_id",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_membership_id"],
            ["tenant_memberships.id"],
            ondelete="CASCADE",
            name=f"fk_{_TABLE}__reviewer_membership_id",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by_membership_id"],
            ["tenant_memberships.id"],
            ondelete="SET NULL",
            name=f"fk_{_TABLE}__assigned_by_membership_id",
        ),
        sa.CheckConstraint(
            "status IN ('assigned', 'in_review', 'done')",
            name=conv(f"ck_{_TABLE}__status_valid"),
        ),
        # One person, one domain, once: re-assigning the same pair is an update,
        # not a second row nobody can tell from the first.
        sa.UniqueConstraint(
            "tenant_id",
            "assessment_id",
            "domain",
            "reviewer_membership_id",
            name=f"uq_{_TABLE}__assessment_domain_reviewer",
        ),
    )
    op.create_index(f"ix_{_TABLE}__tenant_id_assessment_id", _TABLE, ["tenant_id", "assessment_id"])
    # Named by hand: the generated one is two characters past Postgres's 63.
    op.create_index(
        "ix_vendor_assessment_reviewers__tenant_id_reviewer",
        _TABLE,
        ["tenant_id", "reviewer_membership_id"],
    )
    enable_rls(_TABLE)
    grant_crud(_TABLE)


def downgrade() -> None:
    disable_rls(_TABLE)
    op.drop_table(_TABLE)
