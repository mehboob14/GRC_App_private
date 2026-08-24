"""Evidence: the artefacts that prove a control operates.

One item can satisfy many controls — that is the whole economics of evidence
collection, and why ``evidence_controls`` is a join table rather than a column
on ``evidence``. Collect an access-review export once, attach it to every
criterion it speaks to.

Freshness is **derived**, never stored (D14). ``renewal_date`` is a real column
the user sets; whether an item is current, aging or stale is computed from it at
read time. A stored ``is_stale`` boolean is wrong within a day of being written.

A file's bytes live behind ``core.storage``; this table records the pointer plus
the sha256 the store computed on write (D12). The hash is what makes an item's
integrity checkable years later, so it is not nullable for stored files.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Final

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint, text
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

EVIDENCE_KINDS: Final[tuple[str, ...]] = ("file", "link")
"""A file is bytes we hold and can hash; a link points at a system we do not
control. The distinction matters to an auditor, so it is a column, not a guess
made from whether ``link_url`` happens to be null."""

# D13: shipped types with default validity periods. The default only pre-fills
# the renewal date — the user picks the type AND may override the date at upload
# and at edit. A compliance product must not silently decide when evidence dies.
EVIDENCE_TYPES: Final[tuple[str, ...]] = (
    "screenshot",
    "configuration_export",
    "log_export",
    "policy_document",
    "training_record",
    "vendor_report",
    "ticket_record",
    "meeting_minutes",
    "other",
)

REVIEW_STATUSES: Final[tuple[str, ...]] = ("pending", "approved", "rejected")
"""A reviewer's verdict on an item. New evidence starts ``pending``; a reviewer
with ``evidence:review`` approves it or rejects it with a reason. Kept distinct
from freshness (which is about age) — an item can be current but unreviewed, or
approved but going stale."""

DEFAULT_VALIDITY_DAYS: Final[dict[str, int]] = {
    "screenshot": 90,
    "configuration_export": 90,
    "log_export": 30,
    "policy_document": 365,
    "training_record": 365,
    "vendor_report": 365,
    "ticket_record": 90,
    "meeting_minutes": 365,
    "other": 90,
}


class Evidence(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One piece of evidence: an uploaded artefact or a link to one."""

    __tablename__ = "evidence"

    title: Mapped[str]
    description: Mapped[str | None] = mapped_column(default=None)
    evidence_type: Mapped[str]
    kind: Mapped[str]

    # Where it came from, in the auditor's sense: "Okta admin console",
    # "AWS Config". Free text because the honest answer is often a sentence.
    source_label: Mapped[str | None] = mapped_column(default=None)

    # Rule 3: an in-tenant person is a membership, never a global user id.
    owner_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )

    collected_at: Mapped[date]
    renewal_date: Mapped[date | None] = mapped_column(default=None)

    # -- file payload (kind='file') -----------------------------------------
    object_key: Mapped[str | None] = mapped_column(default=None)
    filename: Mapped[str | None] = mapped_column(default=None)
    content_type: Mapped[str | None] = mapped_column(default=None)
    size_bytes: Mapped[int | None] = mapped_column(default=None)
    sha256: Mapped[str | None] = mapped_column(default=None)

    # -- link payload (kind='link') -----------------------------------------
    link_url: Mapped[str | None] = mapped_column(default=None)

    # -- review / approval --------------------------------------------------
    # A four-eyes step: evidence is a claim until a reviewer signs off on it.
    # ``reviewed_by`` is a membership (rule 3), SET NULL so a departed reviewer
    # does not erase the fact that a review happened.
    review_status: Mapped[str] = mapped_column(server_default=text("'pending'"), default="pending")
    reviewed_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(default=None)
    review_note: Mapped[str | None] = mapped_column(default=None)

    # Rule 9: anything that could arrive from a connector carries these from
    # the first migration, so a future sync is a sync and not a migration.
    source: Mapped[str | None] = mapped_column(default=None)
    external_id: Mapped[str | None] = mapped_column(default=None)
    synced_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("evidence", "kind", EVIDENCE_KINDS),
        status_check("evidence", "evidence_type", EVIDENCE_TYPES),
        status_check("evidence", "review_status", REVIEW_STATUSES),
        # A file must have its bytes and their hash; a link must have its URL.
        # Without this an item could claim to be a file and hold nothing.
        CheckConstraint(
            "(kind = 'file') = (object_key IS NOT NULL AND sha256 IS NOT NULL)",
            name=conv("ck_evidence__file_has_object_and_hash"),
        ),
        CheckConstraint(
            "(kind = 'link') = (link_url IS NOT NULL)",
            name=conv("ck_evidence__link_has_url"),
        ),
        CheckConstraint(
            "renewal_date IS NULL OR renewal_date >= collected_at",
            name=conv("ck_evidence__renewal_after_collection"),
        ),
        tenant_index("evidence", "renewal_date"),
        tenant_index("evidence", "evidence_type"),
        Index(
            "uq_evidence__tenant_source_external",
            "tenant_id",
            "source",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
    )

    def __repr__(self) -> str:
        return f"Evidence(id={self.id!r}, tenant_id={self.tenant_id!r}, kind={self.kind!r})"


class EvidenceControl(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """Which control a piece of evidence supports. Many-to-many on purpose."""

    __tablename__ = "evidence_controls"

    evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"))
    control_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("controls.id", ondelete="CASCADE"))

    __table_args__ = (
        UniqueConstraint("tenant_id", "evidence_id", "control_id", name="uq_evidence_controls"),
        tenant_index("evidence_controls", "control_id"),
        tenant_index("evidence_controls", "evidence_id"),
    )

    def __repr__(self) -> str:
        return f"EvidenceControl(evidence_id={self.evidence_id!r}, control_id={self.control_id!r})"
