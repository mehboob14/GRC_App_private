"""A second framework beside SOC 2: how scope is chosen, which frameworks a workspace
runs, and the Statement of Applicability.

``frameworks.scope_model`` says how a framework's scope is chosen: ``categories`` (SOC 2:
the workspace elects Trust Services Categories) or ``applicability`` (ISO 27001: every
requirement is in unless excluded with a reason). ``frameworks.position`` orders the
catalogue so SOC 2 stays first when a second framework is loaded; both columns default to
what SOC 2 needs, so existing rows and the SOC 2 pack are unchanged.

``tenant_frameworks`` replaces "SOC 2 is implied" with a row: every workspace that exists
gets one for SOC 2 here, and signup writes one from now on. ``requirement_applicability``
holds a workspace's decisions about requirements (the Statement of Applicability). Neither
table is ever deleted from (rule 6), so the application role loses ``DELETE``.

``engagements`` was one per tenant. It becomes one per framework version, its audit type
accepts the certification audits, and it gains the management system scope statement, the
certification body and the audit date.

Revision ID: c5d8a2f7e91b
Revises: 7c3e91d2a8f4
Create Date: 2026-10-10
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.db.rls import disable_rls, enable_rls, grant_crud, revoke_delete

revision: str = "c5d8a2f7e91b"
down_revision: str | None = "7c3e91d2a8f4"
branch_labels: str | None = None
depends_on: str | None = None

_UUID = postgresql.UUID(as_uuid=True)
_MEMBERSHIPS = "tenant_memberships.id"
_OLD_AUDIT_TYPES = ("type_1", "type_2")
_NEW_AUDIT_TYPES = (*_OLD_AUDIT_TYPES, "initial_certification", "surveillance", "recertification")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


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
    # -- frameworks: how scope is chosen, and the order they are listed in
    op.add_column(
        "frameworks",
        sa.Column("scope_model", sa.Text(), server_default=sa.text("'categories'"), nullable=False),
    )
    op.add_column(
        "frameworks",
        sa.Column("position", sa.Integer(), server_default=sa.text("100"), nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_frameworks__scope_model_valid"),
        "frameworks",
        _in("scope_model", ("categories", "applicability")),
    )

    # -- engagements: one per framework version, certification audits, scope statement
    op.drop_constraint(op.f("uq_engagements__tenant"), "engagements", type_="unique")
    op.create_unique_constraint(
        op.f("uq_engagements__tenant_framework_version"),
        "engagements",
        ["tenant_id", "framework_version_id"],
    )
    op.drop_constraint(op.f("ck_engagements__audit_type_valid"), "engagements", type_="check")
    op.create_check_constraint(
        op.f("ck_engagements__audit_type_valid"),
        "engagements",
        _in("audit_type", _NEW_AUDIT_TYPES),
    )
    op.add_column("engagements", sa.Column("scope_statement", sa.Text(), nullable=True))
    op.add_column("engagements", sa.Column("certification_body", sa.Text(), nullable=True))
    op.add_column("engagements", sa.Column("audit_on", sa.Date(), nullable=True))

    # -- tenant_frameworks
    op.create_table(
        "tenant_frameworks",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("framework_id", _UUID, nullable=False),
        sa.Column("framework_version_id", _UUID, nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
        sa.Column("activated_by_membership_id", _UUID, nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
            name="fk_tenant_frameworks__tenant_id",
        ),
        sa.ForeignKeyConstraint(
            ["framework_id"],
            ["frameworks.id"],
            ondelete="RESTRICT",
            name="fk_tenant_frameworks__framework_id",
        ),
        sa.ForeignKeyConstraint(
            ["framework_version_id"],
            ["framework_versions.id"],
            ondelete="RESTRICT",
            name="fk_tenant_frameworks__framework_version_id",
        ),
        sa.ForeignKeyConstraint(
            ["activated_by_membership_id"],
            [_MEMBERSHIPS],
            ondelete="SET NULL",
            name="fk_tenant_frameworks__activated_by_membership_id",
        ),
        sa.CheckConstraint(
            _in("status", ("active", "inactive")),
            name=op.f("ck_tenant_frameworks__status_valid"),
        ),
    )
    op.create_index(
        "uq_tenant_frameworks__tenant_id_framework_id",
        "tenant_frameworks",
        ["tenant_id", "framework_id"],
        unique=True,
    )
    # Every workspace that exists is on SOC 2: that is what "implied" meant. Written
    # before the policy exists, because the table is forced and a policy hides these
    # rows from the owner this migration runs as.
    op.execute(
        """
        INSERT INTO tenant_frameworks
            (id, tenant_id, framework_id, framework_version_id, status, created_at, updated_at)
        SELECT gen_random_uuid(), t.id, f.id, v.id, 'active', now(), now()
        FROM tenants t
        CROSS JOIN frameworks f
        JOIN framework_versions v ON v.framework_id = f.id AND v.is_current
        WHERE f.code = 'SOC2'
        """
    )
    enable_rls("tenant_frameworks")
    grant_crud("tenant_frameworks")
    revoke_delete("tenant_frameworks")

    # -- requirement_applicability
    op.create_table(
        "requirement_applicability",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("requirement_id", _UUID, nullable=False),
        sa.Column("applicable", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column(
            "provided_by", sa.Text(), server_default=sa.text("'organization'"), nullable=False
        ),
        sa.Column("owner_membership_id", _UUID, nullable=True),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
            name="fk_requirement_applicability__tenant_id",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["requirements.id"],
            ondelete="RESTRICT",
            name="fk_requirement_applicability__requirement_id",
        ),
        sa.ForeignKeyConstraint(
            ["owner_membership_id"],
            [_MEMBERSHIPS],
            ondelete="SET NULL",
            name="fk_requirement_applicability__owner_membership_id",
        ),
        sa.CheckConstraint(
            _in("provided_by", ("organization", "supplier")),
            name=op.f("ck_requirement_applicability__provided_by_valid"),
        ),
        sa.CheckConstraint(
            "applicable OR (justification IS NOT NULL AND length(btrim(justification)) > 0)",
            name=op.f("ck_requirement_applicability__exclusion_justified"),
        ),
    )
    op.create_index(
        "uq_requirement_applicability__tenant_id_requirement_id",
        "requirement_applicability",
        ["tenant_id", "requirement_id"],
        unique=True,
    )
    enable_rls("requirement_applicability")
    grant_crud("requirement_applicability")
    revoke_delete("requirement_applicability")


def downgrade() -> None:
    disable_rls("requirement_applicability")
    op.drop_table("requirement_applicability")
    disable_rls("tenant_frameworks")
    op.drop_table("tenant_frameworks")

    # Certification engagements cannot exist under the old rules: one per tenant and
    # SOC 2 audit types only. FORCE is lifted for the delete and restored, as the
    # earlier cross tenant data migrations do.
    op.execute("ALTER TABLE engagements NO FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        DELETE FROM engagements e
        USING framework_versions v, frameworks f
        WHERE v.id = e.framework_version_id AND f.id = v.framework_id AND f.code <> 'SOC2'
        """
    )
    op.execute("ALTER TABLE engagements FORCE ROW LEVEL SECURITY")
    op.drop_column("engagements", "audit_on")
    op.drop_column("engagements", "certification_body")
    op.drop_column("engagements", "scope_statement")
    op.drop_constraint(op.f("ck_engagements__audit_type_valid"), "engagements", type_="check")
    op.create_check_constraint(
        op.f("ck_engagements__audit_type_valid"), "engagements", _in("audit_type", _OLD_AUDIT_TYPES)
    )
    op.drop_constraint(
        op.f("uq_engagements__tenant_framework_version"), "engagements", type_="unique"
    )
    op.create_unique_constraint(op.f("uq_engagements__tenant"), "engagements", ["tenant_id"])

    op.drop_constraint(op.f("ck_frameworks__scope_model_valid"), "frameworks", type_="check")
    op.drop_column("frameworks", "position")
    op.drop_column("frameworks", "scope_model")
