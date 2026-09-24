"""Asset management — the security asset inventory (Week 6 / Deliverable 1.3).

One unified record per asset. Criticality is **derived and stored** (D-crit): the
CIA ratings drive a computed ``criticality_score`` and ``tier``, while
``tier_override`` is kept separately so the record always shows both what the
system derived and what a person chose. Nothing here defaults criticality — a
NULL score/tier means "not assessed", never a laundered "medium".

Correlation keys (``fqdn``, ``primary_mac``, ``serial_number``,
``cloud_resource_id``, ``os_normalized``) and the ``Integratable`` mixin ride the
record now so Phase-2 connector sync and dedup need no schema change (the
"design the schema for all three phases" rule, docs/product/delivery-plan.md).

Lifecycle transitions are enforced in the service; decommissioning writes a
``DecommissionRecord`` and (once vulns exist) closes the asset's open findings.
``asset_transitions`` is the immutable, columnar history — separate from and
additional to the platform ``audit_log`` (rule 5).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Final

from sqlalchemy import CheckConstraint, Float, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.elements import conv

from verity.db.base import (
    Base,
    Integratable,
    TenantScoped,
    Timestamped,
    UUIDPrimaryKey,
    integration_unique,
    status_check,
    tenant_index,
)

ASSET_TYPES: Final[tuple[str, ...]] = (
    "application",
    "infrastructure",
    "data",
    "cloud",
    "third_party",
    "business_service",
)
ASSET_STATUSES: Final[tuple[str, ...]] = (
    "planned",
    "active",
    "in_maintenance",
    "decommissioned",
    "retired",
)
DATA_CLASSIFICATIONS: Final[tuple[str, ...]] = ("public", "internal", "confidential", "restricted")
CRITICALITY_TIERS: Final[tuple[str, ...]] = ("critical", "high", "medium", "low")
ENVIRONMENTS: Final[tuple[str, ...]] = ("prod", "staging", "dev", "test", "dr")

_MEMBERSHIP_FK = "tenant_memberships.id"


# How long an asset of each criticality may go unreviewed before the inventory
# hygiene panel calls it stale. The tenant overrides these in ``asset_policies``;
# "unrated" covers an asset with no tier yet, which is the one most worth chasing.
DEFAULT_REVIEW_DAYS_BY_TIER: Final[dict[str, int]] = {
    "critical": 90,
    "high": 90,
    "medium": 90,
    "low": 90,
    "unrated": 90,
}

RELATIONSHIP_TYPES: Final[tuple[str, ...]] = (
    "depends_on",
    "runs_on",
    "contains",
    "connects_to",
    "processes_data_for",
)
RELATIONSHIP_PROVENANCE: Final[tuple[str, ...]] = ("declared", "discovered")


class Asset(UUIDPrimaryKey, TenantScoped, Timestamped, Integratable, Base):
    """One asset in the inventory."""

    __tablename__ = "assets"

    # identity
    name: Mapped[str]
    description: Mapped[str | None] = mapped_column(default=None)
    asset_type: Mapped[str] = mapped_column(default="application")
    hostname: Mapped[str | None] = mapped_column(default=None)
    ip_address: Mapped[str | None] = mapped_column(default=None)
    location: Mapped[str | None] = mapped_column(default=None)
    # Free text until the vendors module lands; then it becomes a link.
    vendor_ref: Mapped[str | None] = mapped_column(default=None)

    # correlation keys — populated by Phase-2 connectors; carried now so dedup and
    # the Phase-3 CIS benchmarks (which key off os_normalized) need no migration.
    fqdn: Mapped[str | None] = mapped_column(default=None)
    primary_mac: Mapped[str | None] = mapped_column(default=None)
    serial_number: Mapped[str | None] = mapped_column(default=None)
    cloud_resource_id: Mapped[str | None] = mapped_column(default=None)
    os_normalized: Mapped[str | None] = mapped_column(default=None)
    environment: Mapped[str | None] = mapped_column(default=None)

    # classification & exposure
    data_classification: Mapped[str | None] = mapped_column(default=None)
    regulated_data_type: Mapped[str | None] = mapped_column(default=None)
    compliance_scope: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    internet_facing: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    customer_facing: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    network_segment: Mapped[str | None] = mapped_column(default=None)
    business_function: Mapped[str | None] = mapped_column(default=None)

    # business context
    valuation: Mapped[float | None] = mapped_column(Float, default=None)
    business_impact_notes: Mapped[str | None] = mapped_column(default=None)
    operational_dependency_rating: Mapped[str | None] = mapped_column(default=None)

    # Tenant-defined extras (``customfields``). Validated against the definitions
    # before it lands here, so this is a blob with a schema, not a free-for-all.
    custom_fields: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )

    # ownership chain — every person a membership (rule 3); the team a group.
    primary_owner_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    secondary_owner_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    business_owner_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    custodian_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    escalation_contact_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    owning_team_group_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("groups.id", ondelete="SET NULL"), default=None
    )

    # criticality — nullable, NO default: NULL means "not assessed".
    confidentiality: Mapped[int | None] = mapped_column(default=None)
    integrity: Mapped[int | None] = mapped_column(default=None)
    availability: Mapped[int | None] = mapped_column(default=None)
    criticality_score: Mapped[float | None] = mapped_column(Float, default=None)
    tier: Mapped[str | None] = mapped_column(default=None)
    tier_override: Mapped[str | None] = mapped_column(default=None)
    tier_override_reason: Mapped[str | None] = mapped_column(default=None)

    # lifecycle
    status: Mapped[str] = mapped_column(default="planned")
    replaced_by_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), default=None
    )

    # freshness — first/last seen exist for Phase-2 connector staleness; reviewed
    # is the inventory-attestation timestamp (ISO 27001 A.5.9).
    first_seen_at: Mapped[datetime | None] = mapped_column(default=None)
    last_seen_at: Mapped[datetime | None] = mapped_column(default=None)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("assets", "asset_type", ASSET_TYPES),
        status_check("assets", "status", ASSET_STATUSES),
        # Nullable columns: NULL passes an IN(...) check, so "not set" stays legal.
        status_check("assets", "data_classification", DATA_CLASSIFICATIONS),
        status_check("assets", "environment", ENVIRONMENTS),
        status_check("assets", "tier", CRITICALITY_TIERS),
        status_check("assets", "tier_override", CRITICALITY_TIERS),
        CheckConstraint(
            "(confidentiality IS NULL OR confidentiality BETWEEN 1 AND 5) AND "
            "(integrity IS NULL OR integrity BETWEEN 1 AND 5) AND "
            "(availability IS NULL OR availability BETWEEN 1 AND 5)",
            name=conv("ck_assets__cia_range"),
        ),
        # An override without a reason is the audit gap the reason exists to close.
        CheckConstraint(
            "(tier_override IS NULL) OR (tier_override_reason IS NOT NULL)",
            name=conv("ck_assets__override_has_reason"),
        ),
        integration_unique("assets"),
        tenant_index("assets", "status"),
        tenant_index("assets", "asset_type"),
        tenant_index("assets", "tier_override"),
        tenant_index("assets", "primary_owner_membership_id"),
    )

    def __repr__(self) -> str:
        return f"Asset(id={self.id!r}, tenant_id={self.tenant_id!r}, name={self.name!r})"


class DecommissionRecord(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """The disposal record written when an asset is decommissioned — auditors test
    that retirement followed policy, so the method and sanitisation are kept."""

    __tablename__ = "decommission_records"

    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"))
    disposal_method: Mapped[str]
    media_sanitised: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    replacement_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), default=None
    )
    evidence_ref: Mapped[str | None] = mapped_column(default=None)
    reason: Mapped[str]
    decommissioned_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    decommissioned_at: Mapped[datetime] = mapped_column()

    __table_args__ = (
        # One decommission per asset.
        UniqueConstraint("tenant_id", "asset_id", name="uq_decommission_records__asset"),
        tenant_index("decommission_records", "asset_id"),
    )


class AssetPolicy(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """Per-tenant inventory settings. One row, and only if it was customised.

    The same arrangement the vendor tiering policy uses: ``DEFAULT_*`` in code is
    the default and this row is the override, so a new tenant needs no
    provisioning step and no migration has to insert a tenant-owned row it cannot
    see through that row's own RLS policy.
    """

    __tablename__ = "asset_policies"

    review_cadence_days_by_tier: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )

    __table_args__ = (UniqueConstraint("tenant_id", name="uq_asset_policies__tenant_id"),)


class AssetRelationship(UUIDPrimaryKey, TenantScoped, Timestamped, Integratable, Base):
    """One directed dependency between two assets (A8).

    Stored once and read from both ends. A second row for the inverse would let
    the two disagree, and disagreeing edges are worse than no edges when the
    question being asked is what else goes down with this.

    ``provenance`` keeps a person's claim distinguishable from a scanner's
    observation, which is the same distinction the subprocessor register draws
    and for the same reason.
    """

    __tablename__ = "asset_relationships"

    source_asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"))
    target_asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"))
    relationship_type: Mapped[str] = mapped_column(default="depends_on")
    provenance: Mapped[str] = mapped_column(default="declared", server_default="declared")
    note: Mapped[str | None] = mapped_column(default=None)
    created_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )

    __table_args__ = (
        status_check("asset_relationships", "relationship_type", RELATIONSHIP_TYPES),
        status_check("asset_relationships", "provenance", RELATIONSHIP_PROVENANCE),
        CheckConstraint(
            "source_asset_id <> target_asset_id",
            name=conv("ck_asset_relationships__no_self_edge"),
        ),
        UniqueConstraint(
            "tenant_id",
            "source_asset_id",
            "target_asset_id",
            "relationship_type",
            name="uq_asset_relationships__edge",
        ),
        integration_unique("asset_relationships"),
        tenant_index("asset_relationships", "source_asset_id"),
        tenant_index("asset_relationships", "target_asset_id"),
    )


class AssetTransition(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """Immutable, columnar lifecycle history. One row per changed field, so "who
    changed criticality, and when" is a WHERE clause. Append-only: insert only,
    enforced by revoked grant + trigger."""

    __tablename__ = "asset_transitions"

    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"))
    actor_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    field_changed: Mapped[str]  # "status", "criticality", "owner", "created", …
    old_value: Mapped[str | None] = mapped_column(default=None)
    new_value: Mapped[str | None] = mapped_column(default=None)
    note: Mapped[str | None] = mapped_column(default=None)
    occurred_at: Mapped[datetime] = mapped_column()

    __table_args__ = (tenant_index("asset_transitions", "asset_id"),)
