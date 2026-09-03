"""Documents & Policies — the tenant's policy library.

A ``documents`` row is the living document; its text lives in
``document_versions``, which is **append-only** (rule 5 / ADR-0005): a new edit
or a new uploaded file writes a new version, never an overwrite, so an auditor
can always see what a version said when it was approved. ``current_version_id``
points at the version a reader sees.

Content is held two ways (ADR-0012): authored policies as sanitised HTML in
``content_html``; uploaded PDF/Word as an object-store key. A version carries one
or the other, per ``content_format``.

Framework/control links (``document_frameworks`` / ``document_controls``) let a
policy satisfy a control the way evidence does. Approvals and acknowledgements
carry the workflow: tiered sign-off, then an attestation campaign.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Final

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.elements import conv

from verity.db.base import (
    Base,
    TenantScoped,
    Timestamped,
    UUIDPrimaryKey,
    status_check,
    tenant_index,
)

DOC_TYPES: Final[tuple[str, ...]] = ("policy", "standard", "procedure", "guideline", "charter")
"""What kind of document this is. Drives the code prefix (POL/STD/PRC/GDL/CHT)."""

CLASSIFICATIONS: Final[tuple[str, ...]] = ("public", "internal", "confidential", "restricted")
"""Handling sensitivity, coarsest to strictest."""

LIFECYCLES: Final[tuple[str, ...]] = (
    "draft",
    "needs_approval",
    "approved",
    "published",
    "expired",
    "archived",
)
"""Where the document is in its life. ``expired`` = renewal lapsed; ``archived``
= retired (rule 6, never hard-deleted for a published document)."""

CONTENT_FORMATS: Final[tuple[str, ...]] = ("html", "pdf", "docx")
"""Authored HTML, or an uploaded file of the given type."""

CHANGE_TYPES: Final[tuple[str, ...]] = ("major", "minor", "patch")

APPROVAL_STATUSES: Final[tuple[str, ...]] = ("not_started", "pending", "approved", "rejected")

APPROVAL_TARGET_TYPES: Final[tuple[str, ...]] = ("user", "role", "group")
"""What the owner picked for a tier: a named person, a role, or a group."""

ASSIGNEE_DECISIONS: Final[tuple[str, ...]] = ("pending", "approved", "rejected")
"""One resolved person's own answer on a tier they were assigned to."""

# Acknowledgement campaigns: a targeted read-and-sign against a document.
CAMPAIGN_STATUSES: Final[tuple[str, ...]] = ("active", "closed")
RECIPIENT_KINDS: Final[tuple[str, ...]] = ("reviewer", "approver")
RECIPIENT_SOURCES: Final[tuple[str, ...]] = ("user", "role", "group")
RECIPIENT_STATUSES: Final[tuple[str, ...]] = ("pending", "acknowledged")

TYPE_PREFIX: Final[dict[str, str]] = {
    "policy": "POL",
    "standard": "STD",
    "procedure": "PRC",
    "guideline": "GDL",
    "charter": "CHT",
}


class Document(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One document in a tenant's library."""

    __tablename__ = "documents"

    code: Mapped[str]
    title: Mapped[str]
    description: Mapped[str | None] = mapped_column(default=None)
    doc_type: Mapped[str]
    classification: Mapped[str] = mapped_column(default="internal")
    lifecycle: Mapped[str] = mapped_column(default="draft")
    content_format: Mapped[str] = mapped_column(default="html")
    filename: Mapped[str | None] = mapped_column(default=None)

    # The version a reader sees. A plain pointer, not an FK: documents and
    # document_versions reference each other, and a hard FK either way needs a
    # deferrable/use_alter dance for no real gain — the service keeps it honest.
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(default=None)

    owner_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )
    assigned_to: Mapped[str | None] = mapped_column(default=None)
    renewal_date: Mapped[date | None] = mapped_column(default=None)

    approved_at: Mapped[datetime | None] = mapped_column(default=None)
    published_at: Mapped[datetime | None] = mapped_column(default=None)
    archived_at: Mapped[datetime | None] = mapped_column(default=None)
    archived_reason: Mapped[str | None] = mapped_column(default=None)

    # Rule 9 — anything that could arrive from a connector carries these.
    source: Mapped[str | None] = mapped_column(default=None)
    external_id: Mapped[str | None] = mapped_column(default=None)
    synced_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("documents", "doc_type", DOC_TYPES),
        status_check("documents", "classification", CLASSIFICATIONS),
        status_check("documents", "lifecycle", LIFECYCLES),
        status_check("documents", "content_format", CONTENT_FORMATS),
        CheckConstraint(
            "(archived_at IS NULL) = (archived_reason IS NULL)",
            name=conv("ck_documents__archived_has_reason"),
        ),
        UniqueConstraint("tenant_id", "code", name="uq_documents__tenant_code"),
        tenant_index("documents", "lifecycle"),
        tenant_index("documents", "renewal_date"),
        Index(
            "uq_documents__tenant_source_external",
            "tenant_id",
            "source",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
    )

    def __repr__(self) -> str:
        return f"Document(id={self.id!r}, tenant_id={self.tenant_id!r}, code={self.code!r})"


class DocumentVersion(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """An immutable snapshot of a document's content. Append-only (trigger)."""

    __tablename__ = "document_versions"

    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    version_no: Mapped[str]
    change_type: Mapped[str] = mapped_column(default="minor")
    content_format: Mapped[str] = mapped_column(default="html")
    content_html: Mapped[str | None] = mapped_column(default=None)
    object_key: Mapped[str | None] = mapped_column(default=None)
    filename: Mapped[str | None] = mapped_column(default=None)
    content_type: Mapped[str | None] = mapped_column(default=None)
    size_bytes: Mapped[int | None] = mapped_column(default=None)
    sha256: Mapped[str | None] = mapped_column(default=None)
    summary: Mapped[str | None] = mapped_column(default=None)
    created_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )

    __table_args__ = (
        status_check("document_versions", "change_type", CHANGE_TYPES),
        status_check("document_versions", "content_format", CONTENT_FORMATS),
        UniqueConstraint(
            "tenant_id", "document_id", "version_no", name="uq_document_versions__doc_version"
        ),
        tenant_index("document_versions", "document_id"),
    )

    def __repr__(self) -> str:
        return f"DocumentVersion(document_id={self.document_id!r}, version_no={self.version_no!r})"


class DocumentControl(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A document satisfies a control (many-to-many)."""

    __tablename__ = "document_controls"

    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    control_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("controls.id", ondelete="CASCADE"))

    __table_args__ = (
        UniqueConstraint("tenant_id", "document_id", "control_id", name="uq_document_controls"),
        tenant_index("document_controls", "control_id"),
        tenant_index("document_controls", "document_id"),
    )


class DocumentFramework(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A document is scoped to a framework (many-to-many)."""

    __tablename__ = "document_frameworks"

    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    framework_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("frameworks.id", ondelete="RESTRICT")
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "document_id", "framework_id", name="uq_document_frameworks"),
        tenant_index("document_frameworks", "document_id"),
    )


class DocumentApproval(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One tier of a document's sign-off. Rows for every tier are created the
    first time any tier is assigned, so tier 2 always has somewhere to stage
    its targets while tier 1 is still open (rule: assignment and gating live
    beside the resolved people in ``DocumentApprovalTarget`` /
    ``DocumentApprovalAssignee`` below, this row only tracks the tier's own
    settled status). ``decided_at``/``note`` are the tier's OWN settling —
    when it was approved, or the note attached to the rejection that closed
    it — not any one assignee's decision."""

    __tablename__ = "document_approvals"

    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    tier: Mapped[int]
    status: Mapped[str] = mapped_column(default="not_started")
    decided_at: Mapped[datetime | None] = mapped_column(default=None)
    note: Mapped[str | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("document_approvals", "status", APPROVAL_STATUSES),
        UniqueConstraint("tenant_id", "document_id", "tier", name="uq_document_approvals__tier"),
        tenant_index("document_approvals", "document_id"),
    )


class DocumentApprovalTarget(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One thing the owner picked for a tier: a named person, a role, or a
    group. ``target_name`` is a snapshot label so the picker still reads
    sensibly if the role is later renamed or the person leaves — the tenant's
    own row of truth for "who does the owner mean" is IAM, this is a record of
    what was asked for. Roles and groups are expanded to the people who
    satisfy them in ``DocumentApprovalAssignee`` at the moment the tier is
    (re)assigned."""

    __tablename__ = "document_approval_targets"

    approval_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_approvals.id", ondelete="CASCADE")
    )
    target_type: Mapped[str]
    target_id: Mapped[uuid.UUID]
    target_name: Mapped[str]

    __table_args__ = (
        status_check("document_approval_targets", "target_type", APPROVAL_TARGET_TYPES),
        UniqueConstraint(
            "tenant_id", "approval_id", "target_type", "target_id",
            name="uq_document_approval_targets__target",
        ),
        tenant_index("document_approval_targets", "approval_id"),
    )


class DocumentApprovalAssignee(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One resolved person on a tier, and their own decision. A person can
    satisfy more than one target at once (named directly AND pulled in by a
    role they hold) — they still get exactly one row here, with every target
    they satisfy recorded in ``source_target_ids``, so a tier that requires
    "every named person, and at least one from each role/group" can be
    checked without a many-to-many join table."""

    __tablename__ = "document_approval_assignees"

    approval_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_approvals.id", ondelete="CASCADE")
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="CASCADE")
    )
    source_target_ids: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    decision: Mapped[str] = mapped_column(default="pending", server_default=text("'pending'"))
    decided_at: Mapped[datetime | None] = mapped_column(default=None)
    note: Mapped[str | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("document_approval_assignees", "decision", ASSIGNEE_DECISIONS),
        UniqueConstraint(
            "tenant_id", "approval_id", "membership_id",
            name="uq_document_approval_assignees__member",
        ),
        tenant_index("document_approval_assignees", "approval_id"),
        tenant_index("document_approval_assignees", "membership_id"),
    )


class DocumentAcknowledgement(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A person acknowledged a document version (attestation campaign)."""

    __tablename__ = "document_acknowledgements"

    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE")
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="CASCADE")
    )
    acknowledged_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "document_id", "membership_id", name="uq_document_acknowledgements"
        ),
        tenant_index("document_acknowledgements", "document_id"),
    )


class DocumentAckCampaign(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A targeted acknowledgement campaign against a document: the owner asks a
    named set of people to read and sign, and tracks who has and who hasn't."""

    __tablename__ = "document_ack_campaigns"

    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    title: Mapped[str]
    message: Mapped[str | None] = mapped_column(default=None)
    created_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )
    status: Mapped[str] = mapped_column(default="active", server_default=text("'active'"))
    due_at: Mapped[datetime | None] = mapped_column(default=None)
    closed_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("document_ack_campaigns", "status", CAMPAIGN_STATUSES),
        tenant_index("document_ack_campaigns", "document_id"),
    )


class DocumentAckCampaignRecipient(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One person asked to acknowledge, their role, and whether they have. Deduped
    per campaign even when added via several sources (a role and a group)."""

    __tablename__ = "document_ack_campaign_recipients"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_ack_campaigns.id", ondelete="CASCADE")
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(default="reviewer", server_default=text("'reviewer'"))
    source: Mapped[str] = mapped_column(default="user", server_default=text("'user'"))
    status: Mapped[str] = mapped_column(default="pending", server_default=text("'pending'"))
    acknowledged_at: Mapped[datetime | None] = mapped_column(default=None)
    ack_comment: Mapped[str | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("document_ack_campaign_recipients", "kind", RECIPIENT_KINDS),
        status_check("document_ack_campaign_recipients", "source", RECIPIENT_SOURCES),
        status_check("document_ack_campaign_recipients", "status", RECIPIENT_STATUSES),
        UniqueConstraint(
            "tenant_id", "campaign_id", "membership_id",
            name="uq_document_ack_campaign_recipients__member",
        ),
        tenant_index("document_ack_campaign_recipients", "membership_id"),
    )


class DocumentAckCampaignComment(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """Discussion on a campaign. Flat, with an optional set of @-mentioned members
    the author tagged (notified separately)."""

    __tablename__ = "document_ack_campaign_comments"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_ack_campaigns.id", ondelete="CASCADE")
    )
    author_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )
    body: Mapped[str]
    mentioned_ids: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )

    __table_args__ = (tenant_index("document_ack_campaign_comments", "campaign_id"),)
