"""vendor tiering and the twelve-stage lifecycle (Week 5, section 2)

Four tenant-owned tables, so RLS and the grants land with them (rule 12).
``vendor_transitions`` is append-only: the revoked grant and the trigger both,
because the revoke does not bind the table's owner and the trigger holds even for
a session that could bypass row-level security.

Two constraints in here carry policy rather than hygiene:

- ``ck_vendor_stages__gate_never_skipped`` is spec paragraph 82's "approval gates
  are never skipped" written as a CHECK. It is the one rule in this module whose
  violation is a control failure and not a bug, so the database refuses it rather
  than the service remembering to.
- ``ck_vendor_tiering_assessments__override_has_reason`` is the audit gap the
  justification column exists to close: a tier overridden with no stated reason is
  a number a reviewer cannot defend.

``vendor_tiering_policies`` is seeded with no rows, deliberately. The defaults
live in ``vendors/scoring.py`` and ``vendors/lifecycle.py``; a row here is an
override a tenant writes when they retune. That keeps a new tenant free of a
provisioning step, and keeps this migration from having to insert a tenant-owned
row it could not see through that row's own policy (FORCE binds the owner too).
What protects past assessments from a later retune is
``vendor_tiering_assessments.policy_snapshot``, not a seeded row.

Revision ID: a1c9e4f72b56
Revises: f4b7d2a90e18
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.db.rls import disable_rls, drop_append_only, enable_rls, grant_crud, make_append_only

revision: str = "a1c9e4f72b56"
down_revision: str | None = "f4b7d2a90e18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = postgresql.UUID(as_uuid=True)

# Restated rather than imported: a migration describes the schema at this
# revision, not at HEAD. The originals are Final tuples in vendors/lifecycle.py
# and vendors/models.py.
STAGES = (
    "intake",
    "tiering",
    "diligence",
    "questionnaire",
    "scoring",
    "findings",
    "contracting",
    "approval",
    "onboarding",
    "monitoring",
    "reassessment",
    "offboarding",
)
STAGE_STATUSES = ("not_started", "in_progress", "complete", "skipped")
TRANSITION_ACTIONS = ("advance", "send_back", "skip")
TIERS = ("critical", "high", "medium", "low")

# Creation order respects the foreign keys; downgrade drops the reverse.
_TABLES = (
    "vendor_tiering_policies",
    "vendor_tiering_assessments",
    "vendor_stages",
    "vendor_transitions",
)
_APPEND_ONLY = "vendor_transitions"

_MEMBERSHIPS = "tenant_memberships.id"


def _check(table: str, column: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    joined = ", ".join(f"'{v}'" for v in values)
    return sa.CheckConstraint(f"{column} IN ({joined})", name=conv(f"ck_{table}__{column}_valid"))


def _ts() -> tuple[sa.Column[Any], sa.Column[Any]]:
    return (
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def _tenant_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{table}__tenant_id"
    )


def _vendor_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["vendor_id"], ["vendors.id"], ondelete="CASCADE", name=f"fk_{table}__vendor_id"
    )


def _engagement_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["engagement_id"],
        ["vendor_engagements.id"],
        ondelete="CASCADE",
        name=f"fk_{table}__engagement_id",
    )


def _member_fk(table: str, column: str, ondelete: str = "SET NULL") -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [_MEMBERSHIPS], ondelete=ondelete, name=f"fk_{table}__{column}"
    )


def _jsonb(name: str, empty: str = "'{}'::jsonb") -> sa.Column[Any]:
    return sa.Column(name, postgresql.JSONB(), nullable=False, server_default=sa.text(empty))


def _create_policies() -> None:
    op.create_table(
        "vendor_tiering_policies",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        _jsonb("factor_weights"),
        _jsonb("tier_thresholds"),
        _jsonb("cadence_days_by_tier"),
        _jsonb("questionnaire_bundle_by_tier"),
        _jsonb("finding_sla_days_by_severity"),
        sa.Column(
            "auto_approve_low_tier", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        _jsonb("stage_skip_matrix_by_tier"),
        _jsonb("required_reviewer_roles_by_tier"),
        *_ts(),
        _tenant_fk("vendor_tiering_policies"),
        sa.UniqueConstraint("tenant_id", name="uq_vendor_tiering_policies__tenant_id"),
    )


def _create_tiering_assessments() -> None:
    op.create_table(
        "vendor_tiering_assessments",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("vendor_id", _UUID, nullable=False),
        sa.Column("engagement_id", _UUID, nullable=False),
        sa.Column("cycle", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("data_sensitivity", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "business_criticality", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("system_access", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("regulatory_scope", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "fourth_party_reliance", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("inherent_score", sa.Float(), nullable=False),
        sa.Column("computed_tier", sa.Text(), nullable=False),
        sa.Column("override_tier", sa.Text(), nullable=True),
        sa.Column("override_justification", sa.Text(), nullable=True),
        _jsonb("policy_snapshot"),
        sa.Column("assessed_by_membership_id", _UUID, nullable=True),
        sa.Column("assessed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_ts(),
        _tenant_fk("vendor_tiering_assessments"),
        _vendor_fk("vendor_tiering_assessments"),
        _engagement_fk("vendor_tiering_assessments"),
        _member_fk("vendor_tiering_assessments", "assessed_by_membership_id"),
        _check("vendor_tiering_assessments", "computed_tier", TIERS),
        _check("vendor_tiering_assessments", "override_tier", TIERS),
        # An override without a reason is the audit gap the reason exists to close.
        sa.CheckConstraint(
            "(override_tier IS NULL) OR (override_justification IS NOT NULL)",
            name=conv("ck_vendor_tiering_assessments__override_has_reason"),
        ),
        sa.CheckConstraint(
            "data_sensitivity BETWEEN 0 AND 4 AND business_criticality BETWEEN 0 AND 4 AND "
            "system_access BETWEEN 0 AND 4 AND regulatory_scope BETWEEN 0 AND 4 AND "
            "fourth_party_reliance BETWEEN 0 AND 4",
            name=conv("ck_vendor_tiering_assessments__factor_range"),
        ),
    )
    op.create_index(
        "ix_vendor_tiering_assessments__tenant_id_vendor_id",
        "vendor_tiering_assessments",
        ["tenant_id", "vendor_id"],
    )
    op.create_index(
        "ix_vendor_tiering_assessments__tenant_id_engagement_id_cycle",
        "vendor_tiering_assessments",
        ["tenant_id", "engagement_id", "cycle"],
    )


def _create_stages() -> None:
    op.create_table(
        "vendor_stages",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("vendor_id", _UUID, nullable=False),
        sa.Column("engagement_id", _UUID, nullable=False),
        sa.Column("cycle", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="not_started"),
        sa.Column("is_gate", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        _jsonb("checklist", "'[]'::jsonb"),
        sa.Column("entered_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("exited_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("skipped_by_membership_id", _UUID, nullable=True),
        sa.Column("skipped_reason", sa.Text(), nullable=True),
        sa.Column("skipped_by_policy", sa.Text(), nullable=True),
        *_ts(),
        _tenant_fk("vendor_stages"),
        _vendor_fk("vendor_stages"),
        _engagement_fk("vendor_stages"),
        _member_fk("vendor_stages", "skipped_by_membership_id"),
        _check("vendor_stages", "stage", STAGES),
        _check("vendor_stages", "status", STAGE_STATUSES),
        # Spec paragraph 82, as a constraint rather than a convention.
        sa.CheckConstraint(
            "NOT (is_gate AND status = 'skipped')",
            name=conv("ck_vendor_stages__gate_never_skipped"),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "engagement_id",
            "cycle",
            "stage",
            name="uq_vendor_stages__engagement_cycle_stage",
        ),
    )
    op.create_index(
        "ix_vendor_stages__tenant_id_vendor_id", "vendor_stages", ["tenant_id", "vendor_id"]
    )
    op.create_index(
        "ix_vendor_stages__tenant_id_engagement_id_cycle",
        "vendor_stages",
        ["tenant_id", "engagement_id", "cycle"],
    )
    op.create_index("ix_vendor_stages__tenant_id_status", "vendor_stages", ["tenant_id", "status"])


def _create_transitions() -> None:
    op.create_table(
        "vendor_transitions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("vendor_id", _UUID, nullable=False),
        sa.Column("engagement_id", _UUID, nullable=False),
        sa.Column("stage_id", _UUID, nullable=True),
        sa.Column("cycle", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("from_stage", sa.Text(), nullable=True),
        sa.Column("to_stage", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor_membership_id", _UUID, nullable=True),
        # Append-only: occurred_at alone. An updated_at on a table that refuses
        # UPDATE could only ever lie (docs/conventions/database.md).
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False),
        _tenant_fk("vendor_transitions"),
        _vendor_fk("vendor_transitions"),
        _engagement_fk("vendor_transitions"),
        # NO ACTION, not SET NULL. SET NULL issues an UPDATE, the append-only
        # trigger refuses it, and the membership delete fails with it.
        sa.ForeignKeyConstraint(
            ["stage_id"],
            ["vendor_stages.id"],
            ondelete="NO ACTION",
            name="fk_vendor_transitions__stage_id",
        ),
        _member_fk("vendor_transitions", "actor_membership_id", ondelete="NO ACTION"),
        _check("vendor_transitions", "action", TRANSITION_ACTIONS),
    )
    op.create_index(
        "ix_vendor_transitions__tenant_id_vendor_id",
        "vendor_transitions",
        ["tenant_id", "vendor_id"],
    )
    op.create_index(
        "ix_vendor_transitions__tenant_id_engagement_id_cycle",
        "vendor_transitions",
        ["tenant_id", "engagement_id", "cycle"],
    )


def upgrade() -> None:
    _create_policies()
    _create_tiering_assessments()
    _create_stages()
    _create_transitions()

    for table in _TABLES:
        enable_rls(table)
        grant_crud(table)
    # After grant_crud: it revokes on top of the grant.
    make_append_only(_APPEND_ONLY)


def downgrade() -> None:
    drop_append_only(_APPEND_ONLY)
    for table in reversed(_TABLES):
        disable_rls(table)
        op.drop_table(table)
