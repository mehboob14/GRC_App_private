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


class DiffSegmentOut(_Response):
    """A run of words, and whether it survived the edit. Text only — the diff
    path never hands the client markup to inject."""

    kind: str
    text: str


class DiffBlockOut(_Response):
    kind: str
    tag: str
    segments: list[DiffSegmentOut]


class DiffStatsOut(_Response):
    blocks_added: int
    blocks_removed: int
    blocks_changed: int
    words_added: int
    words_removed: int


class VersionDiffOut(_Response):
    """One version and what it changed, against the version before it."""

    version_id: uuid.UUID
    version_no: str
    compared_with: str | None
    created_at: UtcDateTime
    created_by_name: str | None
    summary: str | None
    blocks: list[DiffBlockOut]
    stats: DiffStatsOut
    #: False for an uploaded PDF/Word version, which has no text to compare.
    comparable: bool
    reason: str | None


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


class ApprovalTargetOut(_Response):
    target_type: str
    target_id: uuid.UUID
    target_name: str


class ApprovalAssigneeOut(_Response):
    membership_id: uuid.UUID
    name: str
    decision: str
    decided_at: UtcDateTime | None
    note: str | None


class ApprovalOut(_Response):
    tier: int
    status: str
    decided_at: UtcDateTime | None
    note: str | None
    targets: list[ApprovalTargetOut] = Field(default_factory=list)
    assignees: list[ApprovalAssigneeOut] = Field(default_factory=list)
    my_decision: str | None = None


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


class ApprovalDecision(_Request):
    decision: str = Field(pattern="^(approved|rejected)$")
    note: str | None = Field(default=None, max_length=2000)


# -- acknowledgement campaigns ----------------------------------------------


class RecipientSelectionIn(_Request):
    """A mix of individuals, roles and groups to target. Roles and groups are
    expanded to their current members when the campaign is created."""

    user_ids: list[uuid.UUID] = Field(default_factory=list)
    role_ids: list[uuid.UUID] = Field(default_factory=list)
    group_ids: list[uuid.UUID] = Field(default_factory=list)


class AssignApprovalRequest(_Request):
    """Who reviews/approves this tier: any mix of named people, roles and
    groups. Assigning tier 1 on a draft document starts the review; there is
    no separate "submit" step."""

    targets: RecipientSelectionIn


class CampaignCreate(_Request):
    title: str = Field(min_length=1, max_length=300)
    message: str | None = Field(default=None, max_length=4000)
    reviewers: RecipientSelectionIn = Field(default_factory=RecipientSelectionIn)
    approvers: RecipientSelectionIn = Field(default_factory=RecipientSelectionIn)
    due_at: UtcDateTime | None = None


class AcknowledgeCampaignRequest(_Request):
    comment: str | None = Field(default=None, max_length=2000)


class CampaignCommentCreate(_Request):
    body: str = Field(min_length=1, max_length=4000)
    mentioned_ids: list[uuid.UUID] = Field(default_factory=list)


class CampaignRecipientOut(_Response):
    membership_id: uuid.UUID
    name: str
    email: str
    kind: str
    source: str
    status: str
    acknowledged_at: UtcDateTime | None
    ack_comment: str | None


class CampaignCommentOut(_Response):
    id: uuid.UUID
    author_membership_id: uuid.UUID | None
    author_name: str
    body: str
    mentioned_ids: list[str]
    mentioned_names: list[str]
    created_at: UtcDateTime


class CampaignOut(_Response):
    id: uuid.UUID
    document_id: uuid.UUID
    document_code: str
    document_title: str
    title: str
    message: str | None
    status: str
    created_by_membership_id: uuid.UUID | None
    created_by_name: str
    due_at: UtcDateTime | None
    closed_at: UtcDateTime | None
    created_at: UtcDateTime
    total: int
    acknowledged: int
    pending: int
    recipients: list[CampaignRecipientOut]
    comments: list[CampaignCommentOut]


class CampaignSummaryOut(_Response):
    id: uuid.UUID
    document_id: uuid.UUID
    title: str
    status: str
    due_at: UtcDateTime | None
    closed_at: UtcDateTime | None
    created_at: UtcDateTime
    total: int
    acknowledged: int
    pending: int


class PendingCampaignOut(_Response):
    id: uuid.UUID
    document_id: uuid.UUID
    document_code: str
    document_title: str
    title: str
    message: str | None
    kind: str
    due_at: UtcDateTime | None
    created_at: UtcDateTime
    created_by_name: str


class PendingApprovalOut(_Response):
    document_id: uuid.UUID
    document_code: str
    document_title: str
    tier: int
