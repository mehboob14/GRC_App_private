"""Request/response contracts for the vendor module.

Response shapes mirror the frontend's `types.ts` so the mock -> real swap is a
one-file change on that side. Responses build from the service's View dataclasses
via ``from_attributes``.

The cached risk columns (``tier``, ``current_residual_score``, ``current_grade``,
``annual_contract_value``) appear on responses and on **no** request: they are
derived from the vendor's engagements, so a client that could write them could
make an unscored vendor look scored.
"""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from verity.modules.tenancy.schemas import UtcDateTime


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# -- requests -----------------------------------------------------------------


class EngagementWrite(_Request):
    """One use of the vendor. Tier and status are derived, so neither comes in."""

    name: str = Field(min_length=1, max_length=300)
    service_description: str = Field(default="", max_length=8000)
    business_unit: str | None = Field(default=None, max_length=300)
    internal_owner_membership_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None


class VendorWrite(_Request):
    """The create/edit payload for the organisation itself."""

    name: str = Field(min_length=1, max_length=300)
    vendor_type: str = "vendor"
    industry: str | None = Field(default=None, max_length=300)
    website: str | None = Field(default=None, max_length=2000)
    business_unit: str | None = Field(default=None, max_length=300)
    services_provided: str = Field(default="", max_length=8000)
    stores_pii: bool = False
    data_location: str | None = Field(default=None, max_length=300)
    data_types_in_scope: list[str] = Field(default_factory=list)
    data_classification: str | None = None
    tags: list[str] = Field(default_factory=list)
    business_owner_membership_id: uuid.UUID | None = None
    security_owner_membership_id: uuid.UUID | None = None
    relationship_owner_membership_id: uuid.UUID | None = None


class VendorCreate(VendorWrite):
    """Create carries an optional first engagement.

    Omitting it creates the implicit default (V10), which is what keeps a small
    workspace from ever having to learn the word "engagement".
    """

    engagement: EngagementWrite | None = None


class ContactWrite(_Request):
    name: str = Field(min_length=1, max_length=300)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=64)
    contact_type: str = "commercial"


# -- responses ----------------------------------------------------------------


class OwnershipOut(_Response):
    business_owner_membership_id: uuid.UUID | None
    business_owner_name: str | None
    security_owner_membership_id: uuid.UUID | None
    security_owner_name: str | None
    relationship_owner_membership_id: uuid.UUID | None
    relationship_owner_name: str | None


class EngagementOut(_Response):
    id: uuid.UUID
    vendor_id: uuid.UUID
    name: str
    service_description: str
    business_unit: str | None
    internal_owner_membership_id: uuid.UUID | None
    internal_owner_name: str | None
    tier: str | None
    status: str
    start_date: date | None
    end_date: date | None
    created_at: UtcDateTime
    updated_at: UtcDateTime


class ContactOut(_Response):
    id: uuid.UUID
    vendor_id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    contact_type: str


class DuplicateMatchOut(_Response):
    id: uuid.UUID
    name: str
    reason: str


class VendorOut(_Response):
    id: uuid.UUID
    name: str
    vendor_type: str
    industry: str | None
    website: str | None
    business_unit: str | None
    services_provided: str
    stores_pii: bool
    data_location: str | None
    data_types_in_scope: list[str]
    data_classification: str | None
    lifecycle_status: str
    tier: str | None
    current_residual_score: float | None
    current_grade: str | None
    annual_contract_value: float | None
    ownership: OwnershipOut
    next_reassessment_on: date | None
    tags: list[str]
    source: str
    created_at: UtcDateTime
    updated_at: UtcDateTime
    engagement_count: int
    contact_count: int


class VendorDetailOut(VendorOut):
    engagements: list[EngagementOut]
    contacts: list[ContactOut]
    duplicates: list[DuplicateMatchOut]


class VendorPageOut(_Response):
    items: list[VendorOut]
    total: int


class VendorFacetsOut(_Response):
    vendor_types: list[str]
    statuses: list[str]
    tiers: list[str]
    classifications: list[str]
    contact_types: list[str]
    business_units: list[str]


class DuplicateCheckOut(_Response):
    matches: list[DuplicateMatchOut]
