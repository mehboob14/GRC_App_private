"""Request/response contracts for the documents module."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from verity.modules.tenancy.schemas import UtcDateTime


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DocumentOut(_Response):
    id: uuid.UUID
    code: str
    title: str
    description: str | None
    doc_type: str
    classification: str
    lifecycle: str
    content_format: str
    filename: str | None
    version: str | None
    owner_membership_id: uuid.UUID | None
    owner_name: str | None
    assigned_to: str | None
    renewal_date: date | None
    created_at: UtcDateTime
    approved_at: UtcDateTime | None
    published_at: UtcDateTime | None
    archived_at: UtcDateTime | None
    updated_at: UtcDateTime
    frameworks: list[str]
    controls: list[str]
    attestation_pct: float | None


class DocumentVersionOut(_Response):
    id: uuid.UUID
    version_no: str
    change_type: str
    content_format: str
    filename: str | None
    size_bytes: int | None
    summary: str | None
    created_at: UtcDateTime
    created_by_name: str | None
    is_current: bool


class ApprovalOut(_Response):
    tier: int
    status: str
    approver_name: str | None
    decided_at: UtcDateTime | None
    note: str | None


class DocumentDetailOut(DocumentOut):
    content_html: str | None
    versions: list[DocumentVersionOut]
    approvals: list[ApprovalOut]
    acknowledged: int
    assigned_count: int
    acknowledged_by_me: bool


class DocumentKpisOut(_Response):
    renewal_soon: int
    renewal_past_due: int
    needs_approval: int
    ready_to_publish: int


class DocumentVocabularyOut(_Response):
    doc_types: list[str]
    classifications: list[str]
    lifecycles: list[str]


class DocumentCreate(_Request):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    doc_type: str
    classification: str = "internal"
    # Authored documents only here; a file is created via the upload route.
    content_html: str | None = Field(default=None)
    assigned_to: str | None = Field(default=None, max_length=200)
    owner_membership_id: uuid.UUID | None = None
    framework_ids: list[uuid.UUID] = Field(default_factory=list)
    control_ids: list[uuid.UUID] = Field(default_factory=list)


class DocumentUpdate(_Request):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    doc_type: str | None = None
    classification: str | None = None
    assigned_to: str | None = Field(default=None, max_length=200)
    renewal_date: date | None = None
    owner_membership_id: uuid.UUID | None = None
    clear_owner: bool = False
    framework_ids: list[uuid.UUID] | None = None
    control_ids: list[uuid.UUID] | None = None


class DocumentContentUpdate(_Request):
    content_html: str = Field(min_length=1)
    change_type: str = "minor"
    summary: str | None = Field(default=None, max_length=500)


class ArchiveRequest(_Request):
    reason: str = Field(min_length=1, max_length=500)


class SubmitRequest(_Request):
    """Approvers per tier, in order (tier 1 = reviewer, tier 2 = approver)."""

    approver_ids: list[uuid.UUID] = Field(default_factory=list)


class ApprovalDecision(_Request):
    decision: str = Field(pattern="^(approved|rejected)$")
    note: str | None = Field(default=None, max_length=2000)
