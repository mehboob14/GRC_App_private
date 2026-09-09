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


# -- lifecycle and tiering (section 2) ----------------------------------------


class TieringWrite(_Request):
    """The five factor answers, plus an optional human override of the result.

    The score and the tier are absent by design: they are computed. A client that
    could post a tier could set one the arithmetic never produced.
    """

    data_sensitivity: int = Field(default=0, ge=0, le=4)
    business_criticality: int = Field(default=0, ge=0, le=4)
    system_access: int = Field(default=0, ge=0, le=4)
    regulatory_scope: int = Field(default=0, ge=0, le=4)
    fourth_party_reliance: int = Field(default=0, ge=0, le=4)
    override_tier: str | None = None
    override_justification: str | None = Field(default=None, max_length=4000)


class AdvanceWrite(_Request):
    note: str | None = Field(default=None, max_length=4000)


class SendBackWrite(_Request):
    to_stage: str
    reason: str = Field(min_length=1, max_length=4000)


class SkipWrite(_Request):
    reason: str = Field(min_length=1, max_length=4000)


class ExitCheckOut(_Response):
    code: str
    label: str
    satisfied: bool | None
    """Three-valued. ``null`` means the module that answers this is not built yet —
    render it as pending, never as a tick and never as a failure."""
    detail: str | None
    clears_with: str | None
    clears_id: uuid.UUID | None


class StageOut(_Response):
    id: uuid.UUID
    engagement_id: uuid.UUID
    cycle: int
    stage: str
    label: str
    status: str
    is_gate: bool
    is_required: bool
    entered_at: UtcDateTime | None
    exited_at: UtcDateTime | None
    skipped_reason: str | None
    skipped_by_policy: str | None
    checks: list[ExitCheckOut]
    blockers: list[ExitCheckOut]
    pending: list[ExitCheckOut]
    allowed_transitions: list[str]


class TieringFactorOut(_Response):
    key: str
    label: str
    answer: int
    clamped: int
    weight: float
    points: float
    max_points: float


class TieringOut(_Response):
    id: uuid.UUID
    engagement_id: uuid.UUID
    cycle: int
    factors: list[TieringFactorOut]
    score: float
    computed_tier: str
    override_tier: str | None
    override_justification: str | None
    effective_tier: str
    thresholds: dict[str, float]
    points_to_higher_tier: float | None
    points_to_lower_tier: float | None
    assessed_by_name: str | None
    assessed_at: UtcDateTime | None


class VendorDetailOut(VendorOut):
    engagements: list[EngagementOut]
    contacts: list[ContactOut]
    duplicates: list[DuplicateMatchOut]
    stages: list[StageOut]
    tierings: list[TieringOut]


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
    # The lifecycle vocabulary, served rather than duplicated in TypeScript.
    stages: list[dict[str, object]]
    skip_matrix_by_tier: dict[str, list[str]]
    tiering_factors: list[dict[str, object]]
    tier_thresholds: dict[str, float]
    policy_is_customised: bool


class DuplicateCheckOut(_Response):
    matches: list[DuplicateMatchOut]
