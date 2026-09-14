"""risk register: registers, taxonomy, risks, controls, acceptances, history, library

openspec/changes/week7-risk-register. Six tenant-owned tables with forced RLS and
their grants (rule 12), one global content table the app may only read, the four
``risks:*`` permission keys, and the foreign key the vendor-finding promotion seam
has been waiting for.

Columns are ``design.md`` §1. The ER keys the matrix by tenant; it lives on the
register here (R1), and ``risk-decisions.md`` records the other departures.

The notification kind constraint is widened in the same breath. Besides the risk
kinds it gains ``vendor_reassessment_due`` and ``vendor_document_expiring``, which
the vendor jobs already send and the original constraint refused, so those jobs
failed on their first real notice.

Revision ID: b6d2e8f41a37
Revises: f3b8d2c6a915
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.core.config import get_settings
from verity.db.rls import disable_rls, enable_rls, grant_crud

revision: str = "b6d2e8f41a37"
down_revision: str | None = "f3b8d2c6a915"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = postgresql.UUID(as_uuid=True)
_JSONB = postgresql.JSONB()

# Restated, not imported: a migration describes the schema at this revision.
REGISTER_TYPES = (
    "enterprise",
    "rcsa",
    "iso_27001",
    "soc_2",
    "pci_dss",
    "sox",
    "gdpr",
    "nist_csf",
    "sama_csf",
    "internal",
    "project",
    "third_party",
    "other",
)
REGISTER_STATUSES = ("active", "archived")
RISK_STATUSES = ("open", "in_treatment", "mitigated", "accepted", "closed")
TREATMENTS = ("mitigate", "accept", "avoid", "transfer")
ORIGINS = ("manual", "library", "import", "vendor_finding", "assessment")
ACCEPTANCE_STATUSES = ("pending", "active", "rejected", "withdrawn", "expired", "revoked")
EVENT_KINDS = (
    "created",
    "updated",
    "scored",
    "status",
    "treatment",
    "owner",
    "control_linked",
    "control_unlinked",
    "linked",
    "unlinked",
    "action_added",
    "acceptance_requested",
    "acceptance_approved",
    "acceptance_rejected",
    "acceptance_withdrawn",
    "acceptance_revoked",
    "acceptance_expired",
    "reviewed",
    "imported",
    "adopted",
    "promoted",
)

OLD_NOTIFICATION_KINDS = (
    "assigned",
    "comment",
    "status",
    "sla_breach",
    "sla_due",
    "approval",
    "recurrence",
)
NEW_NOTIFICATION_KINDS = (
    *OLD_NOTIFICATION_KINDS,
    "vendor_reassessment_due",
    "vendor_document_expiring",
    "risk_acceptance_requested",
    "risk_acceptance_decided",
    "risk_acceptance_expired",
    "risk_review_due",
)

PERMISSIONS = ("risks:read", "risks:manage", "risks:approve", "risks:configure")

_TENANT_TABLES = (
    "risk_registers",
    "risk_categories",
    "risks",
    "risk_control_map",
    "risk_acceptances",
    "risk_events",
)

_MEMBERSHIPS = "tenant_memberships.id"


def _in(column: str, values: tuple[str, ...]) -> str:
    joined = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({joined})"


def _unforced(table: str, statement: str) -> None:
    """Run a data statement as the owner past FORCE RLS, which would otherwise
    filter every row out of an owner session with no tenant bound."""
    op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.execute(statement)
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def _check(table: str, column: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    return sa.CheckConstraint(_in(column, values), name=conv(f"ck_{table}__{column}_valid"))


def _ts() -> tuple[sa.Column[Any], sa.Column[Any]]:
    return (
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def _created() -> sa.Column[Any]:
    return sa.Column(
        "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
    )


def _tenant_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{table}__tenant_id"
    )


def _member_fk(table: str, column: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [_MEMBERSHIPS], ondelete="SET NULL", name=f"fk_{table}__{column}"
    )


def _fk(table: str, column: str, target: str, ondelete: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [target], ondelete=ondelete, name=f"fk_{table}__{column}"
    )


def _create_templates() -> None:
    op.create_table(
        "risk_templates",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("sub_category", sa.Text(), nullable=True),
        sa.Column("default_likelihood", sa.SmallInteger(), nullable=False),
        sa.Column("default_impact", sa.SmallInteger(), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("consequences", sa.Text(), nullable=True),
        sa.Column("recommendations", sa.Text(), nullable=True),
        sa.Column("treatment", sa.Text(), nullable=True),
        sa.Column("control_keys", _JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("frameworks", _JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("built_in", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *_ts(),
        sa.UniqueConstraint("code", name="uq_risk_templates__code"),
        sa.CheckConstraint(
            "default_likelihood BETWEEN 1 AND 5 AND default_impact BETWEEN 1 AND 5",
            name=conv("ck_risk_templates__scores_in_range"),
        ),
    )


def _create_registers() -> None:
    op.create_table(
        "risk_registers",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("register_type", sa.Text(), nullable=False, server_default="enterprise"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_membership_id", _UUID, nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("likelihood_levels", sa.SmallInteger(), nullable=False, server_default="5"),
        sa.Column("impact_levels", sa.SmallInteger(), nullable=False, server_default="5"),
        sa.Column(
            "likelihood_scale", _JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column("impact_scale", _JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("severity_bands", _JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("review_cadence_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("created_by_membership_id", _UUID, nullable=True),
        *_ts(),
        _tenant_fk("risk_registers"),
        _member_fk("risk_registers", "owner_membership_id"),
        _member_fk("risk_registers", "created_by_membership_id"),
        _check("risk_registers", "register_type", REGISTER_TYPES),
        _check("risk_registers", "status", REGISTER_STATUSES),
        sa.CheckConstraint(
            "likelihood_levels BETWEEN 3 AND 6 AND impact_levels BETWEEN 3 AND 6",
            name=conv("ck_risk_registers__levels_in_range"),
        ),
        sa.CheckConstraint(
            "review_cadence_days BETWEEN 7 AND 730",
            name=conv("ck_risk_registers__cadence_in_range"),
        ),
    )
    op.create_index(
        "uq_risk_registers__tenant_id_default",
        "risk_registers",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_risk_registers__tenant_id_name "
        "ON risk_registers (tenant_id, lower(name))"
    )


def _create_categories() -> None:
    op.create_table(
        "risk_categories",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("register_id", _UUID, nullable=False),
        sa.Column("parent_id", _UUID, nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("archived_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_ts(),
        _tenant_fk("risk_categories"),
        _fk("risk_categories", "register_id", "risk_registers.id", "CASCADE"),
        _fk("risk_categories", "parent_id", "risk_categories.id", "CASCADE"),
    )
    op.create_index(
        "ix_risk_categories__tenant_id_register_id", "risk_categories", ["tenant_id", "register_id"]
    )
    # Siblings may not share a name. COALESCE because a unique index treats two
    # NULL parents as distinct, which would let two top-level "Technology" rows in.
    op.execute(
        "CREATE UNIQUE INDEX uq_risk_categories__tenant_id_sibling_name ON risk_categories "
        "(tenant_id, register_id, "
        "COALESCE(parent_id, '00000000-0000-0000-0000-000000000000'::uuid), lower(name))"
    )


def _create_risks() -> None:
    op.create_table(
        "risks",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("register_id", _UUID, nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("category_id", _UUID, nullable=False),
        sa.Column("sub_category_id", _UUID, nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("treatment", sa.Text(), nullable=True),
        sa.Column("inherent_likelihood", sa.SmallInteger(), nullable=True),
        sa.Column("inherent_impact", sa.SmallInteger(), nullable=True),
        sa.Column("residual_likelihood", sa.SmallInteger(), nullable=True),
        sa.Column("residual_impact", sa.SmallInteger(), nullable=True),
        sa.Column(
            "inherent_score",
            sa.Integer(),
            sa.Computed("inherent_likelihood * inherent_impact", persisted=True),
            nullable=True,
        ),
        sa.Column(
            "residual_score",
            sa.Integer(),
            sa.Computed("residual_likelihood * residual_impact", persisted=True),
            nullable=True,
        ),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("consequences", sa.Text(), nullable=True),
        sa.Column("recommendations", sa.Text(), nullable=True),
        sa.Column("treatment_plan", sa.Text(), nullable=True),
        sa.Column("owner_membership_id", _UUID, nullable=True),
        sa.Column("department_group_id", _UUID, nullable=True),
        sa.Column("treatment_due_on", sa.Date(), nullable=True),
        sa.Column("next_review_on", sa.Date(), nullable=True),
        sa.Column("last_reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("origin", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("template_id", _UUID, nullable=True),
        sa.Column("origin_ref", _UUID, nullable=True),
        sa.Column("closure_justification", sa.Text(), nullable=True),
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("closed_by_membership_id", _UUID, nullable=True),
        sa.Column("created_by_membership_id", _UUID, nullable=True),
        sa.Column("source", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_ts(),
        _tenant_fk("risks"),
        _fk("risks", "register_id", "risk_registers.id", "RESTRICT"),
        _fk("risks", "category_id", "risk_categories.id", "RESTRICT"),
        _fk("risks", "sub_category_id", "risk_categories.id", "RESTRICT"),
        _fk("risks", "department_group_id", "groups.id", "SET NULL"),
        _fk("risks", "template_id", "risk_templates.id", "SET NULL"),
        _member_fk("risks", "owner_membership_id"),
        _member_fk("risks", "closed_by_membership_id"),
        _member_fk("risks", "created_by_membership_id"),
        _check("risks", "status", RISK_STATUSES),
        _check("risks", "treatment", TREATMENTS),
        _check("risks", "origin", ORIGINS),
        sa.CheckConstraint(
            "(inherent_likelihood IS NULL) = (inherent_impact IS NULL) "
            "AND (residual_likelihood IS NULL) = (residual_impact IS NULL)",
            name=conv("ck_risks__scores_paired"),
        ),
        sa.CheckConstraint(
            "COALESCE(inherent_likelihood, 1) >= 1 AND COALESCE(inherent_impact, 1) >= 1 "
            "AND COALESCE(residual_likelihood, 1) >= 1 AND COALESCE(residual_impact, 1) >= 1",
            name=conv("ck_risks__scores_positive"),
        ),
        sa.CheckConstraint(
            "(status <> 'closed') OR (closure_justification IS NOT NULL)",
            name=conv("ck_risks__closure_justified"),
        ),
        sa.UniqueConstraint(
            "tenant_id", "source", "external_id", name="uq_risks__tenant_id_source_external_id"
        ),
    )
    op.create_index("uq_risks__tenant_id_code", "risks", ["tenant_id", "code"], unique=True)
    for column in (
        "register_id",
        "status",
        "owner_membership_id",
        "residual_score",
        "next_review_on",
        "category_id",
    ):
        op.create_index(f"ix_risks__tenant_id_{column}", "risks", ["tenant_id", column])


def _create_control_map() -> None:
    op.create_table(
        "risk_control_map",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("risk_id", _UUID, nullable=False),
        sa.Column("control_id", _UUID, nullable=False),
        sa.Column("created_by_membership_id", _UUID, nullable=True),
        _created(),
        _tenant_fk("risk_control_map"),
        _fk("risk_control_map", "risk_id", "risks.id", "CASCADE"),
        _fk("risk_control_map", "control_id", "controls.id", "RESTRICT"),
        _member_fk("risk_control_map", "created_by_membership_id"),
    )
    op.create_index(
        "uq_risk_control_map__tenant_id_risk_id_control_id",
        "risk_control_map",
        ["tenant_id", "risk_id", "control_id"],
        unique=True,
    )
    op.create_index(
        "ix_risk_control_map__tenant_id_control_id",
        "risk_control_map",
        ["tenant_id", "control_id"],
    )


def _create_acceptances() -> None:
    op.create_table(
        "risk_acceptances",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("risk_id", _UUID, nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("expires_on", sa.Date(), nullable=False),
        sa.Column("requested_by_membership_id", _UUID, nullable=True),
        sa.Column("approver_membership_id", _UUID, nullable=True),
        sa.Column("residual_score_at_request", sa.Integer(), nullable=True),
        sa.Column("decided_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_by_membership_id", _UUID, nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=True),
        *_ts(),
        _tenant_fk("risk_acceptances"),
        _fk("risk_acceptances", "risk_id", "risks.id", "CASCADE"),
        _member_fk("risk_acceptances", "requested_by_membership_id"),
        _member_fk("risk_acceptances", "approver_membership_id"),
        _member_fk("risk_acceptances", "revoked_by_membership_id"),
        _check("risk_acceptances", "status", ACCEPTANCE_STATUSES),
        sa.CheckConstraint(
            "approver_membership_id IS NULL OR requested_by_membership_id IS NULL "
            "OR approver_membership_id <> requested_by_membership_id",
            name=conv("ck_risk_acceptances__not_self_approved"),
        ),
    )
    op.create_index(
        "uq_risk_acceptances__tenant_id_risk_id_open",
        "risk_acceptances",
        ["tenant_id", "risk_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'active')"),
    )
    op.create_index(
        "ix_risk_acceptances__tenant_id_status_expires_on",
        "risk_acceptances",
        ["tenant_id", "status", "expires_on"],
    )


def _create_events() -> None:
    op.create_table(
        "risk_events",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("risk_id", _UUID, nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("from_value", sa.Text(), nullable=True),
        sa.Column("to_value", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("inherent_score", sa.Integer(), nullable=True),
        sa.Column("residual_score", sa.Integer(), nullable=True),
        sa.Column("actor_membership_id", _UUID, nullable=True),
        _created(),
        _tenant_fk("risk_events"),
        _fk("risk_events", "risk_id", "risks.id", "CASCADE"),
        _member_fk("risk_events", "actor_membership_id"),
        _check("risk_events", "kind", EVENT_KINDS),
    )
    op.create_index(
        "ix_risk_events__tenant_id_risk_id_created_at",
        "risk_events",
        ["tenant_id", "risk_id", "created_at"],
    )


def _set_notification_kinds(kinds: tuple[str, ...]) -> None:
    op.drop_constraint(conv("ck_notifications__kind_valid"), "notifications", type_="check")
    op.create_check_constraint(
        conv("ck_notifications__kind_valid"), "notifications", _in("kind", kinds)
    )


def upgrade() -> None:
    _create_templates()
    op.execute(sa.text(f"GRANT SELECT ON risk_templates TO {get_settings().database.app_role}"))

    _create_registers()
    _create_categories()
    _create_risks()
    _create_control_map()
    _create_acceptances()
    _create_events()
    for table in _TENANT_TABLES:
        enable_rls(table)
        grant_crud(table)

    # The seam vendor_findings.promoted_risk_id shipped without a target.
    op.create_foreign_key(
        "fk_vendor_findings__promoted_risk_id",
        "vendor_findings",
        "risks",
        ["promoted_risk_id"],
        ["id"],
        ondelete="SET NULL",
    )

    _set_notification_kinds(NEW_NOTIFICATION_KINDS)

    # Admin resolves to every key at check time, so no role bundle changes here.
    op.execute(
        "INSERT INTO permissions (key, module, action) VALUES "
        "('risks:read', 'risks', 'read'), "
        "('risks:manage', 'risks', 'manage'), "
        "('risks:approve', 'risks', 'approve'), "
        "('risks:configure', 'risks', 'configure') ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    keys = ", ".join(f"'{key}'" for key in PERMISSIONS)
    op.execute(f"DELETE FROM role_permissions WHERE permission_key IN ({keys})")  # noqa: S608
    op.execute(f"DELETE FROM permissions WHERE key IN ({keys})")  # noqa: S608

    new_only = tuple(k for k in NEW_NOTIFICATION_KINDS if k not in OLD_NOTIFICATION_KINDS)
    _unforced("notifications", f"DELETE FROM notifications WHERE {_in('kind', new_only)}")  # noqa: S608
    _set_notification_kinds(OLD_NOTIFICATION_KINDS)

    op.drop_constraint(
        "fk_vendor_findings__promoted_risk_id", "vendor_findings", type_="foreignkey"
    )
    _unforced("vendor_findings", "UPDATE vendor_findings SET promoted_risk_id = NULL")

    for table in reversed(_TENANT_TABLES):
        disable_rls(table)
        op.drop_table(table)
    op.drop_table("risk_templates")
