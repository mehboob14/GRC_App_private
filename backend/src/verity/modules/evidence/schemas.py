"""Request and response models for the evidence library."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from verity.modules.tenancy.schemas import UtcDateTime


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EvidenceControlLinkOut(_Response):
    """A linked control: its platform code and the criteria it satisfies."""

    code: str
    criteria: list[str]


class EvidenceOut(_Response):
    id: uuid.UUID
    title: str
    description: str | None
    evidence_type: str
    kind: str
    source_label: str | None
    owner_membership_id: uuid.UUID | None
    owner_name: str | None
    collected_at: date
    renewal_date: date | None
    # Derived at read time from renewal_date, never stored (D14).
    freshness: str
    filename: str | None
    content_type: str | None
    size_bytes: int | None
    sha256: str | None
    link_url: str | None
    # Rule 9: the connector that produced this item. Null for hand-uploaded
    # evidence, which is all of it until connectors land.
    source: str | None
    # Review / approval — pending until a reviewer signs off.
    review_status: str
    review_required: bool
    reviewed_by_membership_id: uuid.UUID | None
    reviewed_by_name: str | None
    reviewed_at: UtcDateTime | None
    review_note: str | None
    control_ids: list[uuid.UUID]
    control_codes: list[str]
    control_links: list[EvidenceControlLinkOut]


class EvidenceReviewRequest(_Request):
    decision: str = Field(pattern="^(approved|rejected)$")
    note: str | None = Field(default=None, max_length=2000)


class EvidenceLinkCreate(_Request):
    title: str = Field(min_length=1, max_length=300)
    link_url: str = Field(min_length=1, max_length=2000)
    evidence_type: str
    collected_at: date
    description: str | None = Field(default=None, max_length=4000)
    source_label: str | None = Field(default=None, max_length=200)
    owner_membership_id: uuid.UUID | None = None
    # Omit to accept the type's default validity; send a date to override it.
    renewal_date: date | None = None
    control_ids: list[uuid.UUID] = Field(default_factory=list)


class EvidenceUpdate(_Request):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    evidence_type: str | None = None
    source_label: str | None = Field(default=None, max_length=200)
    owner_membership_id: uuid.UUID | None = None
    clear_owner: bool = False
    collected_at: date | None = None
    renewal_date: date | None = None
    control_ids: list[uuid.UUID] | None = None


class EvidenceTypeOut(_Response):
    """A shipped type and the validity period it suggests. The period only
    pre-fills a renewal date — the user may always override it (D13)."""

    value: str
    label: str
    default_validity_days: int


class EvidenceVocabularyOut(_Response):
    types: list[EvidenceTypeOut]
    freshness_states: list[str]


class MappingSuggestionOut(_Response):
    """A suggested control mapping — a draft a person approves (rule 11)."""

    control_id: uuid.UUID
    code: str
    name: str
    criteria: list[str]
    coverage: str
    confidence: float
    rationale: str
    maturity: int | None = None
    verdict: str | None = None
    gaps: str = ""
    requirements: list[str] = []


class MaturityRequest(_Request):
    control_id: uuid.UUID


class RequirementVerdictOut(_Response):
    code: str
    verdict: str
    note: str


class MaturityOut(_Response):
    """A draft judgement of how well an item proves a control (rule 11)."""

    available: bool
    #: Why there is no judgement: "no_key" or "failed" (the model's reply could not be used).
    reason: str = ""
    control_id: uuid.UUID
    code: str = ""
    name: str = ""
    maturity: int | None = None
    verdict: str | None = None
    summary: str = ""
    strengths: list[str] = []
    gaps: list[str] = []
    requirements: list[RequirementVerdictOut] = []


class MappingSuggestionsOut(_Response):
    # "ai" when a model produced these, "heuristic" for the offline matcher.
    source: str
    suggestions: list[MappingSuggestionOut]


class ApproveMappingRequest(_Request):
    control_id: uuid.UUID


class LinkedRecordOut(_Response):
    """A record this evidence is linked to, in one shape for every module."""

    link_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    code: str
    title: str
    status: str
    detail: str | None


class LinkRecordRequest(_Request):
    target_type: str
    target_id: uuid.UUID
