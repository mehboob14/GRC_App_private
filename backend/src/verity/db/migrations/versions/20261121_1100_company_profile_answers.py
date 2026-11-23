"""Company profile: typed answers, confirmation and frozen versions.

Phase 2 of the guided onboarding change (openspec/changes/guided-onboarding, tasks 2.1 to 2.3).
``company_profile`` gains the answers to the profile questions (one JSON object, validated by
the catalogue in ``modules/tenancy/profile_questions.py``), a registered address, and a draft or
confirmed state with a version number. Every confirmation freezes a copy in
``company_profile_versions``, which is append only (revoked grant and trigger).

Additive: existing rows get empty answers, status ``draft`` and version 0, and every earlier
column keeps its value. The free text ``industry``, ``company_size``, ``headquarters`` and
``regulatory_scope`` columns stay; the form shows them as hints until the typed questions are
answered.

Revision ID: 3b03e4d1a72c
Revises: b9935aa647b2
Create Date: 2026-11-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.db.rls import disable_rls, drop_append_only, enable_rls, grant_crud, make_append_only

revision: str = "3b03e4d1a72c"
down_revision: str | None = "b9935aa647b2"
branch_labels: str | None = None
depends_on: str | None = None

_UUID = postgresql.UUID(as_uuid=True)
_MEMBERSHIPS = "tenant_memberships.id"
_PROFILE = "company_profile"
_VERSIONS = "company_profile_versions"


def upgrade() -> None:
    op.add_column(_PROFILE, sa.Column("registered_address", sa.Text(), nullable=True))
    op.add_column(
        _PROFILE,
        sa.Column(
            "answers", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
    )
    op.add_column(
        _PROFILE,
        sa.Column("answers_schema", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )
    op.add_column(
        _PROFILE,
        sa.Column("status", sa.Text(), server_default=sa.text("'draft'"), nullable=False),
    )
    op.add_column(
        _PROFILE, sa.Column("version", sa.Integer(), server_default=sa.text("0"), nullable=False)
    )
    op.add_column(_PROFILE, sa.Column("confirmed_by_membership_id", _UUID, nullable=True))
    op.add_column(_PROFILE, sa.Column("confirmed_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.create_foreign_key(
        f"fk_{_PROFILE}__confirmed_by_membership_id",
        _PROFILE,
        "tenant_memberships",
        ["confirmed_by_membership_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        op.f(f"ck_{_PROFILE}__status_valid"), _PROFILE, "status IN ('draft', 'confirmed')"
    )
    op.create_check_constraint(
        op.f(f"ck_{_PROFILE}__answers_object"), _PROFILE, "jsonb_typeof(answers) = 'object'"
    )

    op.create_table(
        _VERSIONS,
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("answers", postgresql.JSONB(), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("confirmed_by_membership_id", _UUID, nullable=True),
        sa.Column("confirmed_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{_VERSIONS}__tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_by_membership_id"],
            [_MEMBERSHIPS],
            ondelete="SET NULL",
            name=f"fk_{_VERSIONS}__confirmed_by_membership_id",
        ),
    )
    op.create_index(
        f"uq_{_VERSIONS}__tenant_id_version", _VERSIONS, ["tenant_id", "version"], unique=True
    )
    enable_rls(_VERSIONS)
    grant_crud(_VERSIONS)
    make_append_only(_VERSIONS)


def downgrade() -> None:
    drop_append_only(_VERSIONS)
    disable_rls(_VERSIONS)
    op.drop_table(_VERSIONS)
    op.drop_constraint(op.f(f"ck_{_PROFILE}__answers_object"), _PROFILE, type_="check")
    op.drop_constraint(op.f(f"ck_{_PROFILE}__status_valid"), _PROFILE, type_="check")
    op.drop_constraint(f"fk_{_PROFILE}__confirmed_by_membership_id", _PROFILE, type_="foreignkey")
    for column in (
        "confirmed_at",
        "confirmed_by_membership_id",
        "version",
        "status",
        "answers_schema",
        "answers",
        "registered_address",
    ):
        op.drop_column(_PROFILE, column)
