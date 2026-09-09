"""vendors register — vendors, engagements, contacts (Week 5, section 1)

The first slice of openspec/changes/week5-vendor-risk. Three tenant-owned tables,
so RLS and the grants land with them (rule 12), plus the module's four permission
keys.

Columns are transcribed from the ER's section-3.7 diagrams via that change's
design.md §1. Two departures from the diagram, both recorded there: person
references carry the `_membership_id` suffix and point at `tenant_memberships`
(rule 3 — the ER writes a bare `_id` and the reference product pointed those at
`users`), and `vendors` composes the integration triple because
docs/conventions/database.md names this table by name.

No unique constraint on `vendors.name` or `website` (ER ¶90): two real
subsidiaries share a trading name, so duplicate detection warns on save in the
service rather than the database refusing a legitimate record.

Revision ID: f4b7d2a90e18
Revises: e8a2c5f01d73
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.db.rls import disable_rls, enable_rls, grant_crud

revision: str = "f4b7d2a90e18"
down_revision: str | None = "e8a2c5f01d73"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = postgresql.UUID(as_uuid=True)

# Restated rather than imported: Alembic must not import a model (the migration
# has to describe the schema at this revision, not at HEAD). The originals are
# module-level Final tuples in verity.modules.vendors.models.
VENDOR_TYPES = ("vendor", "supplier", "contractor", "partner")
LIFECYCLE_STATUSES = (
    "requested",
    "under_review",
    "approved",
    "active",
    "flagged",
    "on_hold",
    "offboarding",
    "terminated",
    "archived",
)
TIERS = ("critical", "high", "medium", "low")
DATA_CLASSIFICATIONS = ("public", "internal", "confidential", "restricted")
CONTACT_TYPES = ("security", "privacy", "commercial", "portal")

PERMISSIONS = ("vendors:read", "vendors:manage", "vendors:assess", "vendors:approve")

# Creation order respects the foreign keys; downgrade drops the reverse.
_TABLES = ("vendors", "vendor_engagements", "vendor_contacts")

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


def _member_fk(table: str, column: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [_MEMBERSHIPS], ondelete="SET NULL", name=f"fk_{table}__{column}"
    )


def _integratable() -> tuple[sa.Column[Any], ...]:
    return (
        sa.Column("source", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def _create_vendors() -> None:
    op.create_table(
        "vendors",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("vendor_type", sa.Text(), nullable=False, server_default="vendor"),
        sa.Column("industry", sa.Text(), nullable=True),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column("business_unit", sa.Text(), nullable=True),
        sa.Column("services_provided", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("stores_pii", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("data_location", sa.Text(), nullable=True),
        sa.Column(
            "data_types_in_scope",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("data_classification", sa.Text(), nullable=True),
        sa.Column("lifecycle_status", sa.Text(), nullable=False, server_default="requested"),
        # Cached from the worst engagement (V10) — derived, never authoritative.
        # Nullable with no default: NULL is "not scored yet", not a middle value.
        sa.Column("tier", sa.Text(), nullable=True),
        sa.Column("current_residual_score", sa.Float(), nullable=True),
        sa.Column("current_grade", sa.Text(), nullable=True),
        sa.Column("annual_contract_value", sa.Float(), nullable=True),
        sa.Column("business_owner_membership_id", _UUID, nullable=True),
        sa.Column("security_owner_membership_id", _UUID, nullable=True),
        sa.Column("relationship_owner_membership_id", _UUID, nullable=True),
        sa.Column("next_reassessment_on", sa.Date(), nullable=True),
        sa.Column(
            "tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        *_integratable(),
        *_ts(),
        _tenant_fk("vendors"),
        _member_fk("vendors", "business_owner_membership_id"),
        _member_fk("vendors", "security_owner_membership_id"),
        _member_fk("vendors", "relationship_owner_membership_id"),
        _check("vendors", "vendor_type", VENDOR_TYPES),
        _check("vendors", "lifecycle_status", LIFECYCLE_STATUSES),
        _check("vendors", "data_classification", DATA_CLASSIFICATIONS),
        _check("vendors", "tier", TIERS),
        sa.UniqueConstraint(
            "tenant_id", "source", "external_id", name="uq_vendors__tenant_id_source_external_id"
        ),
    )
    op.create_index(
        "ix_vendors__tenant_id_lifecycle_status", "vendors", ["tenant_id", "lifecycle_status"]
    )
    op.create_index("ix_vendors__tenant_id_tier", "vendors", ["tenant_id", "tier"])
    op.create_index(
        "ix_vendors__tenant_id_business_owner_membership_id",
        "vendors",
        ["tenant_id", "business_owner_membership_id"],
    )
    op.create_index(
        "ix_vendors__tenant_id_next_reassessment_on",
        "vendors",
        ["tenant_id", "next_reassessment_on"],
    )


def _create_engagements() -> None:
    op.create_table(
        "vendor_engagements",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("vendor_id", _UUID, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("service_description", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("business_unit", sa.Text(), nullable=True),
        sa.Column("internal_owner_membership_id", _UUID, nullable=True),
        sa.Column("tier", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="requested"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        *_ts(),
        _tenant_fk("vendor_engagements"),
        _vendor_fk("vendor_engagements"),
        _member_fk("vendor_engagements", "internal_owner_membership_id"),
        _check("vendor_engagements", "status", LIFECYCLE_STATUSES),
        _check("vendor_engagements", "tier", TIERS),
        sa.CheckConstraint(
            "(start_date IS NULL) OR (end_date IS NULL) OR (end_date >= start_date)",
            name=conv("ck_vendor_engagements__dates_ordered"),
        ),
    )
    op.create_index(
        "ix_vendor_engagements__tenant_id_vendor_id",
        "vendor_engagements",
        ["tenant_id", "vendor_id"],
    )
    op.create_index(
        "ix_vendor_engagements__tenant_id_status", "vendor_engagements", ["tenant_id", "status"]
    )
    op.create_index(
        "ix_vendor_engagements__tenant_id_tier", "vendor_engagements", ["tenant_id", "tier"]
    )


def _create_contacts() -> None:
    op.create_table(
        "vendor_contacts",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("vendor_id", _UUID, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("contact_type", sa.Text(), nullable=False, server_default="commercial"),
        *_ts(),
        _tenant_fk("vendor_contacts"),
        _vendor_fk("vendor_contacts"),
        _check("vendor_contacts", "contact_type", CONTACT_TYPES),
        # A portal contact is written to, so it has to be reachable.
        sa.CheckConstraint(
            "(contact_type <> 'portal') OR (email IS NOT NULL)",
            name=conv("ck_vendor_contacts__portal_has_email"),
        ),
    )
    op.create_index(
        "ix_vendor_contacts__tenant_id_vendor_id", "vendor_contacts", ["tenant_id", "vendor_id"]
    )
    op.create_index(
        "ix_vendor_contacts__tenant_id_contact_type",
        "vendor_contacts",
        ["tenant_id", "contact_type"],
    )


def upgrade() -> None:
    _create_vendors()
    _create_engagements()
    _create_contacts()

    for table in _TABLES:
        enable_rls(table)
        grant_crud(table)

    # Admin holds these automatically: the built-in Admin role resolves to "every
    # key that exists" at check time, so no role bundle changes here.
    op.execute(
        "INSERT INTO permissions (key, module, action) VALUES "
        "('vendors:read', 'vendors', 'read'), "
        "('vendors:manage', 'vendors', 'manage'), "
        "('vendors:assess', 'vendors', 'assess'), "
        "('vendors:approve', 'vendors', 'approve') ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    keys = ", ".join(f"'{key}'" for key in PERMISSIONS)
    # role_permissions rows referencing them go first, or the FK refuses the delete.
    op.execute(f"DELETE FROM role_permissions WHERE permission_key IN ({keys})")  # noqa: S608
    op.execute(f"DELETE FROM permissions WHERE key IN ({keys})")  # noqa: S608
    for table in reversed(_TABLES):
        disable_rls(table)
        op.drop_table(table)
