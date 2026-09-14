"""Request/response contracts for the Asset module.

Response shapes mirror the frontend's `types.ts` so the mock -> real swap is a
one-file change on that side. Responses build from the service's View dataclasses
via ``from_attributes``.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from verity.modules.assets.models import ASSET_TYPES, CRITICALITY_TIERS, DATA_CLASSIFICATIONS
from verity.modules.tenancy.schemas import UtcDateTime


def _one_of(values: tuple[str, ...]) -> str:
    # The same lists the table's check constraints hold, so a bad value is a 422
    # here instead of a constraint violation (a 500) at insert.
    return f"^({'|'.join(values)})$"


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# -- responses ---------------------------------------------------------------


class MemberOut(_Response):
    membership_id: uuid.UUID
    name: str


class CriticalityOut(_Response):
    confidentiality: int | None
    integrity: int | None
    availability: int | None
    score: float | None
    tier: str | None
    tier_override: str | None
    tier_override_reason: str | None


class OwnershipOut(_Response):
    primary_owner: MemberOut | None
    secondary_owner: MemberOut | None
    business_owner: MemberOut | None
    custodian: MemberOut | None
    escalation_contact: MemberOut | None
    owning_team: str | None


class HygieneOut(_Response):
    score: int
    missing: list[str]
    is_stale: bool


class AssetOut(_Response):
    id: uuid.UUID
    name: str
    asset_type: str
    description: str
    hostname: str | None
    ip_address: str | None
    fqdn: str | None
    os_normalized: str | None
    environment: str | None
    location: str | None
    vendor_ref: str | None
    data_classification: str | None
    regulated_data_type: str | None
    compliance_scope: list[str]
    internet_facing: bool
    customer_facing: bool
    network_segment: str | None
    business_function: str | None
    criticality: CriticalityOut
    ownership: OwnershipOut
    status: str
    replaced_by_asset_id: uuid.UUID | None
    valuation: float | None
    first_seen_at: UtcDateTime | None
    last_seen_at: UtcDateTime | None
    last_reviewed_at: UtcDateTime | None
    created_at: UtcDateTime
    updated_at: UtcDateTime
    source: str
    hygiene: HygieneOut
    vuln_count: int
    link_count: int
    relationship_count: int


class DecommissionOut(_Response):
    disposal_method: str
    media_sanitised: bool
    replacement_asset_id: uuid.UUID | None
    evidence_ref: str | None
    reason: str
    decommissioned_by: str | None
    decommissioned_at: UtcDateTime


class TransitionOut(_Response):
    id: uuid.UUID
    actor: str | None
    field_changed: str
    old_value: str | None
    new_value: str | None
    note: str | None
    occurred_at: UtcDateTime


class AssetDetailOut(AssetOut):
    serial_number: str | None
    primary_mac: str | None
    cloud_resource_id: str | None
    business_impact_notes: str | None
    operational_dependency_rating: str | None
    decommission: DecommissionOut | None
    transitions: list[TransitionOut]
    watchers: list[MemberOut]
    allowed_transitions: list[str]


class AssetPageOut(_Response):
    items: list[AssetOut]
    total: int


class _TypeCount(_Response):
    type: str
    count: int


class AssetSummaryOut(_Response):
    total: int
    by_tier: dict[str, int]
    by_type: list[_TypeCount]
    by_status: dict[str, int]
    needs_cia: int
    regulated: int
    stale: int
    hygiene_avg: int


class FacetsOut(_Response):
    asset_type: dict[str, int]
    tier: dict[str, int]
    status: dict[str, int]
    environment: dict[str, int]
    needs_attention: int


class ImportResultOut(_Response):
    created: int


class SheetOut(_Response):
    """An uploaded Excel file as rows of text, header row first."""

    rows: list[list[str]]


# -- requests ----------------------------------------------------------------


class AssetWrite(_Request):
    """The create/edit payload. Criticality is derived, so the CIA inputs and the
    override come in, never the score/tier."""

    name: str = Field(min_length=1, max_length=300)
    asset_type: str = Field(default="application", pattern=_one_of(ASSET_TYPES))
    description: str | None = Field(default=None, max_length=8000)
    hostname: str | None = None
    ip_address: str | None = None
    environment: str | None = None
    location: str | None = None
    vendor_ref: str | None = None
    data_classification: str | None = Field(default=None, pattern=_one_of(DATA_CLASSIFICATIONS))
    regulated_data_type: str | None = None
    compliance_scope: list[str] = Field(default_factory=list)
    internet_facing: bool = False
    customer_facing: bool = False
    network_segment: str | None = None
    business_function: str | None = None
    confidentiality: int | None = Field(default=None, ge=1, le=5)
    integrity: int | None = Field(default=None, ge=1, le=5)
    availability: int | None = Field(default=None, ge=1, le=5)
    tier_override: str | None = Field(default=None, pattern=_one_of(CRITICALITY_TIERS))
    tier_override_reason: str | None = None
    primary_owner_membership_id: uuid.UUID | None = None
    secondary_owner_membership_id: uuid.UUID | None = None
    business_owner_membership_id: uuid.UUID | None = None
    custodian_membership_id: uuid.UUID | None = None
    escalation_contact_membership_id: uuid.UUID | None = None
    owning_team_group_id: uuid.UUID | None = None
    valuation: float | None = None
    business_impact_notes: str | None = None
    operational_dependency_rating: str | None = None


class TransitionRequest(_Request):
    to_status: str
    note: str | None = Field(default=None, max_length=2000)


class DecommissionRequest(_Request):
    disposal_method: str
    media_sanitised: bool = False
    replacement_asset_id: uuid.UUID | None = None
    evidence_ref: str | None = None
    reason: str = Field(min_length=1, max_length=2000)


class ImportRequest(_Request):
    rows: list[AssetWrite]
