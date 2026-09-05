"""Documents & Policies service — library, versions, workflow, acknowledgements.

DB access lives here (no separate repository, matching the evidence module).
Cross-module reads go through sibling *services* (rule 4): owner/member names
via IAM, control codes via compliance's control service, framework names via
compliance. Files are held in the object store; a document's text is an
append-only ``document_versions`` row.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any, Final

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import Conflict, InvalidInput, NotFound, PermissionDenied
from verity.core.storage import ObjectStore, get_object_store
from verity.modules.audit.service import Actor, AuditService, audit_service
from verity.modules.documents import placeholders as placeholder_lib
from verity.modules.documents.diffing import (
    DiffBlock,
    DiffSummary,
    diff_html,
    summarise,
)
from verity.modules.documents.models import (
    DOC_TYPES,
    TYPE_PREFIX,
    Document,
    DocumentAckCampaign,
    DocumentAckCampaignComment,
    DocumentAckCampaignRecipient,
    DocumentAcknowledgement,
    DocumentApproval,
    DocumentApprovalAssignee,
    DocumentApprovalTarget,
    DocumentControl,
    DocumentFramework,
    DocumentTemplate,
    DocumentVersion,
)
from verity.shared.ids import uuid7

if TYPE_CHECKING:
    from verity.modules.notifications.service import NotificationService

_DOC_SNAPSHOT: Final = (
    "id",
    "code",
    "title",
    "description",
    "doc_type",
    "classification",
    "lifecycle",
    "content_format",
    "owner_membership_id",
    "assigned_to",
    "renewal_date",
    "archived_at",
    "archived_reason",
)

# ponytail: fixed two-tier sign-off; make configurable if a client needs it.
_APPROVAL_TIERS: Final = 2

_CAMPAIGN_SNAPSHOT: Final = ("id", "document_id", "title", "status", "due_at", "closed_at")
_RECIPIENT_SNAPSHOT: Final = (
    "id",
    "campaign_id",
    "membership_id",
    "kind",
    "source",
    "status",
    "acknowledged_at",
)


@dataclass(frozen=True, slots=True)
class PlaceholderView:
    """A field the reader still has to decide, and how much text it affects."""

    key: str
    label: str
    count: int


@dataclass(frozen=True, slots=True)
class TemplateView:
    """A shipped policy someone can start from."""

    id: uuid.UUID
    key: str
    title: str
    doc_type: str
    classification: str
    summary: str | None
    tags: list[str]
    #: {"SOC 2": ["CC6.1", ...]} — the criteria this policy speaks to.
    satisfies: dict[str, list[str]]
    placeholders: list[PlaceholderView]
    word_count: int
    optional_markers: int
    #: Whether this tenant already has a document started from this template.
    #: Not a bar to starting another, just worth saying before they do.
    already_used: bool
    source: str | None
    source_url: str | None
    license: str | None


@dataclass(frozen=True, slots=True)
class VersionDiffView:
    """One version, and what it changed relative to the version before it.

    ``blocks`` is tagged text, never markup — the diff path deliberately gives
    the client nothing to inject.
    """

    version_id: uuid.UUID
    version_no: str
    compared_with: str | None
    created_at: datetime
    created_by_name: str | None
    summary: str | None
    blocks: list[DiffBlock]
    stats: DiffSummary
    comparable: bool
    reason: str | None


@dataclass(frozen=True)
class VersionView:
    id: uuid.UUID
    version_no: str
    change_type: str
    content_format: str
    filename: str | None
    size_bytes: int | None
    summary: str | None
    created_at: datetime
    created_by_name: str | None
    is_current: bool


@dataclass(frozen=True)
class ApprovalTargetView:
    target_type: str
    target_id: uuid.UUID
    target_name: str


@dataclass(frozen=True)
class ApprovalAssigneeView:
    membership_id: uuid.UUID
    name: str
    decision: str
    decided_at: datetime | None
    note: str | None


@dataclass(frozen=True)
class ApprovalView:
    tier: int
    status: str
    decided_at: datetime | None
    note: str | None
    targets: list[ApprovalTargetView] = field(default_factory=list)
    assignees: list[ApprovalAssigneeView] = field(default_factory=list)
    # This viewer's own decision on this tier, or None if they are not on it.
    my_decision: str | None = None


@dataclass(frozen=True)
class DocumentView:
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
    created_at: datetime
    approved_at: datetime | None
    published_at: datetime | None
    archived_at: datetime | None
    updated_at: datetime
    frameworks: list[str] = field(default_factory=list)
    controls: list[str] = field(default_factory=list)
    attestation_pct: float | None = None


@dataclass(frozen=True)
class DocumentDetailView(DocumentView):
    content_html: str | None = None
    versions: list[VersionView] = field(default_factory=list)
    approvals: list[ApprovalView] = field(default_factory=list)
    acknowledged: int = 0
    assigned_count: int = 0
    acknowledged_by_me: bool = False
    #: Fields still carrying a {{placeholder}} in the current content. A
    #: template that has not been filled in is not yet a policy.
    placeholders: list[PlaceholderView] = field(default_factory=list)


# -- acknowledgement-campaign views -----------------------------------------


@dataclass(frozen=True)
class RecipientSelection:
    """Who a campaign targets, by any mix of individuals, roles and groups.
    Resolved to a deduped set of memberships when the campaign is created."""

    user_ids: Sequence[uuid.UUID] = ()
    role_ids: Sequence[uuid.UUID] = ()
    group_ids: Sequence[uuid.UUID] = ()


@dataclass(frozen=True)
class CampaignRecipientView:
    membership_id: uuid.UUID
    name: str
    email: str
    kind: str
    source: str
    status: str
    acknowledged_at: datetime | None
    ack_comment: str | None


@dataclass(frozen=True)
class CampaignCommentView:
    id: uuid.UUID
    author_membership_id: uuid.UUID | None
    author_name: str
    body: str
    mentioned_ids: list[str]
    mentioned_names: list[str]
    created_at: datetime


@dataclass(frozen=True)
class CampaignView:
    id: uuid.UUID
    document_id: uuid.UUID
    document_code: str
    document_title: str
    title: str
    message: str | None
    status: str
    created_by_membership_id: uuid.UUID | None
    created_by_name: str
    due_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    total: int
    acknowledged: int
    pending: int
    recipients: list[CampaignRecipientView] = field(default_factory=list)
    comments: list[CampaignCommentView] = field(default_factory=list)


@dataclass(frozen=True)
class CampaignSummaryView:
    id: uuid.UUID
    document_id: uuid.UUID
    title: str
    status: str
    due_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    total: int
    acknowledged: int
    pending: int


@dataclass(frozen=True)
class PendingCampaignView:
    id: uuid.UUID
    document_id: uuid.UUID
    document_code: str
    document_title: str
    title: str
    message: str | None
    kind: str
    due_at: datetime | None
    created_at: datetime
    created_by_name: str


@dataclass(frozen=True)
class PendingApprovalView:
    document_id: uuid.UUID
    document_code: str
    document_title: str
    tier: int


def _next_version(current: str | None, change_type: str) -> str:
    """Bump a MAJOR.MINOR version. `major` → next major .0, else next minor."""
    if current is None:
        return "0.1"
    try:
        major_s, _, minor_s = current.partition(".")
        major, minor = int(major_s), int(minor_s or 0)
    except ValueError:
        return "0.1"
    if change_type == "major":
        return f"{major + 1}.0"
    return f"{major}.{minor + 1}"


class DocumentService:
    def __init__(self, audit: AuditService | None = None, store: ObjectStore | None = None) -> None:
        self._audit = audit or audit_service
        self._store = store or get_object_store()

    # -- cross-module name/code resolution (rule 4) --------------------------

    async def _owner_names(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        from verity.modules.iam.service import iam_service  # noqa: PLC0415

        members = await iam_service.list_members(session, tenant_id=tenant_id)
        return {m.membership_id: m.full_name for m in members}

    async def _control_codes(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        from verity.modules.compliance.control_service import control_service  # noqa: PLC0415

        controls = await control_service.list_controls(
            session, tenant_id=tenant_id, include_disabled=True
        )
        return {c.id: c.code for c in controls}

    async def _framework_names(self, session: AsyncSession) -> dict[uuid.UUID, str]:
        from verity.modules.compliance.service import compliance_service  # noqa: PLC0415

        return {f.id: f.name for f in await compliance_service.list_frameworks(session)}

    # -- reads ---------------------------------------------------------------

    async def _load(
        self, session: AsyncSession, tenant_id: uuid.UUID, document_id: uuid.UUID
    ) -> Document:
        doc = await session.get(Document, document_id)
        if doc is None or doc.tenant_id != tenant_id:
            raise NotFound(
                "This document no longer exists. It may have been deleted.",
                detail=f"document {document_id}",
            )
        return doc

    async def _links(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> tuple[dict[uuid.UUID, list[uuid.UUID]], dict[uuid.UUID, list[uuid.UUID]]]:
        """Per-document framework ids and control ids, each in one query."""
        fw_rows = await session.execute(
            select(DocumentFramework.document_id, DocumentFramework.framework_id).where(
                DocumentFramework.tenant_id == tenant_id
            )
        )
        ct_rows = await session.execute(
            select(DocumentControl.document_id, DocumentControl.control_id).where(
                DocumentControl.tenant_id == tenant_id
            )
        )
        frameworks: dict[uuid.UUID, list[uuid.UUID]] = {}
        controls: dict[uuid.UUID, list[uuid.UUID]] = {}
        for doc_id, fw_id in fw_rows:
            frameworks.setdefault(doc_id, []).append(fw_id)
        for doc_id, ct_id in ct_rows:
            controls.setdefault(doc_id, []).append(ct_id)
        return frameworks, controls

    async def _ack_counts(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, int]:
        rows = await session.execute(
            select(DocumentAcknowledgement.document_id).where(
                DocumentAcknowledgement.tenant_id == tenant_id
            )
        )
        out: dict[uuid.UUID, int] = {}
        for (doc_id,) in rows:
            out[doc_id] = out.get(doc_id, 0) + 1
        return out

    @staticmethod
    def _assigned_count(doc: Document) -> int:
        # A real campaign resolves the assignment to a headcount; until the
        # people-directory join lands, "All personnel" stands in at a fixed size.
        return 50 if doc.assigned_to else 0

    def _attestation(self, doc: Document, acked: int) -> float | None:
        assigned = self._assigned_count(doc)
        if assigned == 0:
            return None
        return round(acked / assigned * 100, 1)

    def _view(  # noqa: PLR0913
        self,
        doc: Document,
        *,
        owners: dict[uuid.UUID, str],
        fw_names: dict[uuid.UUID, str],
        ct_codes: dict[uuid.UUID, str],
        fw_ids: list[uuid.UUID],
        ct_ids: list[uuid.UUID],
        acked: int,
    ) -> DocumentView:
        return DocumentView(
            id=doc.id,
            code=doc.code,
            title=doc.title,
            description=doc.description,
            doc_type=doc.doc_type,
            classification=doc.classification,
            lifecycle=doc.lifecycle,
            content_format=doc.content_format,
            filename=doc.filename,
            version=None,  # filled by callers that load the current version
            owner_membership_id=doc.owner_membership_id,
            owner_name=(owners.get(doc.owner_membership_id) if doc.owner_membership_id else None),
            assigned_to=doc.assigned_to,
            renewal_date=doc.renewal_date,
            created_at=doc.created_at,
            approved_at=doc.approved_at,
            published_at=doc.published_at,
            archived_at=doc.archived_at,
            updated_at=doc.updated_at,
            frameworks=sorted(fw_names[i] for i in fw_ids if i in fw_names),
            controls=sorted(ct_codes[i] for i in ct_ids if i in ct_codes),
            attestation_pct=self._attestation(doc, acked),
        )

    async def list_documents(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[DocumentView]:
        rows = (
            (await session.execute(select(Document).where(Document.tenant_id == tenant_id)))
            .scalars()
            .all()
        )
        owners = await self._owner_names(session, tenant_id)
        fw_names = await self._framework_names(session)
        ct_codes = await self._control_codes(session, tenant_id)
        fw_ids, ct_ids = await self._links(session, tenant_id)
        acks = await self._ack_counts(session, tenant_id)
        current = await self._current_versions(session, tenant_id, [r.id for r in rows])
        views = []
        for doc in rows:
            base = self._view(
                doc,
                owners=owners,
                fw_names=fw_names,
                ct_codes=ct_codes,
                fw_ids=fw_ids.get(doc.id, []),
                ct_ids=ct_ids.get(doc.id, []),
                acked=acks.get(doc.id, 0),
            )
            views.append(_with_version(base, current.get(doc.id)))
        views.sort(key=lambda v: v.code)
        return views

    async def _current_versions(
        self, session: AsyncSession, tenant_id: uuid.UUID, doc_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, str]:
        if not doc_ids:
            return {}
        rows = await session.execute(
            select(Document.id, DocumentVersion.version_no)
            .join(DocumentVersion, DocumentVersion.id == Document.current_version_id)
            .where(Document.tenant_id == tenant_id, Document.id.in_(doc_ids))
        )
        return {doc_id: version_no for doc_id, version_no in rows}  # noqa: C416

    async def kpis(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> dict[str, int]:
        rows = (
            (
                await session.execute(
                    select(Document).where(
                        Document.tenant_id == tenant_id, Document.lifecycle != "archived"
                    )
                )
            )
            .scalars()
            .all()
        )
        now = datetime.now(UTC).date()
        soon = date.fromordinal(now.toordinal() + 30)
        past_due = sum(1 for d in rows if d.renewal_date and d.renewal_date <= now)
        return {
            "renewal_past_due": past_due,
            "renewal_soon": sum(1 for d in rows if d.renewal_date and now < d.renewal_date <= soon),
            "needs_approval": sum(1 for d in rows if d.lifecycle == "needs_approval"),
            "ready_to_publish": sum(1 for d in rows if d.lifecycle == "approved"),
        }

    async def get_document(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        me: uuid.UUID | None = None,
    ) -> DocumentDetailView:
        doc = await self._load(session, tenant_id, document_id)
        # Flush pending writes, then load server-computed columns
        # (created_at/updated_at) so the sync view builder never triggers a lazy
        # refresh outside the async context.
        await session.flush()
        await session.refresh(doc)
        owners = await self._owner_names(session, tenant_id)
        fw_names = await self._framework_names(session)
        ct_codes = await self._control_codes(session, tenant_id)
        fw_ids, ct_ids = await self._links(session, tenant_id)
        acks = await self._ack_counts(session, tenant_id)

        versions = (
            (
                await session.execute(
                    select(DocumentVersion)
                    .where(
                        DocumentVersion.tenant_id == tenant_id,
                        DocumentVersion.document_id == document_id,
                    )
                    .order_by(DocumentVersion.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        approvals = (
            (
                await session.execute(
                    select(DocumentApproval)
                    .where(
                        DocumentApproval.tenant_id == tenant_id,
                        DocumentApproval.document_id == document_id,
                    )
                    .order_by(DocumentApproval.tier)
                )
            )
            .scalars()
            .all()
        )
        approval_targets, approval_assignees = await self._approval_children(
            session, tenant_id, [a.id for a in approvals], owners
        )

        current = next((v for v in versions if v.id == doc.current_version_id), None)
        base = self._view(
            doc,
            owners=owners,
            fw_names=fw_names,
            ct_codes=ct_codes,
            fw_ids=fw_ids.get(doc.id, []),
            ct_ids=ct_ids.get(doc.id, []),
            acked=acks.get(doc.id, 0),
        )
        acked = acks.get(doc.id, 0)
        me_acked = False
        if me is not None:
            me_acked = (
                await session.execute(
                    select(DocumentAcknowledgement.id).where(
                        DocumentAcknowledgement.tenant_id == tenant_id,
                        DocumentAcknowledgement.document_id == document_id,
                        DocumentAcknowledgement.membership_id == me,
                    )
                )
            ).first() is not None

        return DocumentDetailView(
            **{**base.__dict__, "version": current.version_no if current else None},
            content_html=current.content_html if current else None,
            placeholders=[
                PlaceholderView(key=ph.key, label=ph.label, count=ph.count)
                for ph in placeholder_lib.find(current.content_html if current else None)
            ],
            versions=[
                VersionView(
                    id=v.id,
                    version_no=v.version_no,
                    change_type=v.change_type,
                    content_format=v.content_format,
                    filename=v.filename,
                    size_bytes=v.size_bytes,
                    summary=v.summary,
                    created_at=v.created_at,
                    created_by_name=(
                        owners.get(v.created_by_membership_id)
                        if v.created_by_membership_id
                        else None
                    ),
                    is_current=v.id == doc.current_version_id,
                )
                for v in versions
            ],
            approvals=[
                ApprovalView(
                    tier=a.tier,
                    status=a.status,
                    decided_at=a.decided_at,
                    note=a.note,
                    targets=approval_targets.get(a.id, []),
                    assignees=approval_assignees.get(a.id, []),
                    my_decision=next(
                        (
                            asn.decision
                            for asn in approval_assignees.get(a.id, [])
                            if me is not None and asn.membership_id == me
                        ),
                        None,
                    ),
                )
                for a in approvals
            ],
            acknowledged=acked,
            assigned_count=self._assigned_count(doc),
            acknowledged_by_me=me_acked,
        )

    # -- writes --------------------------------------------------------------

    async def _next_code(self, session: AsyncSession, tenant_id: uuid.UUID, doc_type: str) -> str:
        prefix = TYPE_PREFIX[doc_type]
        rows = await session.execute(
            select(Document.code).where(
                Document.tenant_id == tenant_id, Document.code.like(f"{prefix}-%")
            )
        )
        highest = 0
        for (code,) in rows:
            suffix = code.removeprefix(f"{prefix}-")
            if suffix.isdigit():
                highest = max(highest, int(suffix))
        return f"{prefix}-{highest + 1:02d}"

    async def _set_links(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        *,
        framework_ids: Sequence[uuid.UUID] | None,
        control_ids: Sequence[uuid.UUID] | None,
    ) -> None:
        if framework_ids is not None:
            await session.execute(
                delete(DocumentFramework).where(
                    DocumentFramework.tenant_id == tenant_id,
                    DocumentFramework.document_id == document_id,
                )
            )
            for fw in set(framework_ids):
                session.add(
                    DocumentFramework(
                        id=uuid7(), tenant_id=tenant_id, document_id=document_id, framework_id=fw
                    )
                )
        if control_ids is not None:
            await session.execute(
                delete(DocumentControl).where(
                    DocumentControl.tenant_id == tenant_id,
                    DocumentControl.document_id == document_id,
                )
            )
            for ct in set(control_ids):
                session.add(
                    DocumentControl(
                        id=uuid7(), tenant_id=tenant_id, document_id=document_id, control_id=ct
                    )
                )
        await session.flush()

    async def create_document(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        title: str,
        doc_type: str,
        classification: str = "internal",
        description: str | None = None,
        content_html: str | None = None,
        assigned_to: str | None = None,
        owner_membership_id: uuid.UUID | None = None,
        framework_ids: Sequence[uuid.UUID] | None = None,
        control_ids: Sequence[uuid.UUID] | None = None,
    ) -> DocumentView:
        if doc_type not in DOC_TYPES:
            raise InvalidInput(
                "Pick a document type from the list before saving.",
                detail=f"unknown document type {doc_type!r}",
            )
        code = await self._next_code(session, tenant_id, doc_type)
        doc = Document(
            id=uuid7(),
            tenant_id=tenant_id,
            code=code,
            title=title.strip(),
            description=(description or None),
            doc_type=doc_type,
            classification=classification,
            lifecycle="draft",
            content_format="html",
            assigned_to=assigned_to,
            owner_membership_id=owner_membership_id,
        )
        session.add(doc)
        await session.flush([doc])

        version = DocumentVersion(
            id=uuid7(),
            tenant_id=tenant_id,
            document_id=doc.id,
            version_no="0.1",
            change_type="minor",
            content_format="html",
            content_html=content_html or "",
            summary="Initial draft.",
            created_by_membership_id=_membership(actor),
        )
        session.add(version)
        await session.flush([version])
        doc.current_version_id = version.id

        await self._set_links(
            session, tenant_id, doc.id, framework_ids=framework_ids, control_ids=control_ids
        )
        await self._audit.record(
            session,
            action="create",
            object_type="document",
            object_id=doc.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after=AuditService.snapshot(doc, fields=_DOC_SNAPSHOT),
        )
        return await self._one(session, tenant_id, doc.id)

    async def create_uploaded(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        title: str,
        doc_type: str,
        filename: str,
        data: bytes,
        classification: str = "internal",
        description: str | None = None,
        assigned_to: str | None = None,
        framework_ids: Sequence[uuid.UUID] | None = None,
        control_ids: Sequence[uuid.UUID] | None = None,
    ) -> DocumentView:
        if doc_type not in DOC_TYPES:
            raise InvalidInput(
                "Pick a document type from the list before uploading.",
                detail=f"unknown document type {doc_type!r}",
            )
        fmt = "pdf" if filename.lower().endswith(".pdf") else "docx"
        stored = self._store.put(tenant_id, filename, data)
        code = await self._next_code(session, tenant_id, doc_type)
        doc = Document(
            id=uuid7(),
            tenant_id=tenant_id,
            code=code,
            title=title.strip(),
            description=(description or None),
            doc_type=doc_type,
            classification=classification,
            lifecycle="draft",
            content_format=fmt,
            filename=stored.original_filename,
            assigned_to=assigned_to,
        )
        session.add(doc)
        await session.flush([doc])

        version = DocumentVersion(
            id=uuid7(),
            tenant_id=tenant_id,
            document_id=doc.id,
            version_no="1.0",
            change_type="major",
            content_format=fmt,
            object_key=stored.key,
            filename=stored.original_filename,
            content_type=stored.content_type,
            size_bytes=stored.size_bytes,
            sha256=stored.sha256,
            summary="Uploaded file.",
            created_by_membership_id=_membership(actor),
        )
        session.add(version)
        await session.flush([version])
        doc.current_version_id = version.id

        await self._set_links(
            session, tenant_id, doc.id, framework_ids=framework_ids, control_ids=control_ids
        )
        await self._audit.record(
            session,
            action="create",
            object_type="document",
            object_id=doc.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after=AuditService.snapshot(doc, fields=_DOC_SNAPSHOT),
        )
        return await self._one(session, tenant_id, doc.id)

    async def update_document(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        document_id: uuid.UUID,
        title: str | None = None,
        description: str | None = None,
        doc_type: str | None = None,
        classification: str | None = None,
        assigned_to: str | None = None,
        renewal_date: date | None = None,
        owner_membership_id: uuid.UUID | None = None,
        clear_owner: bool = False,
        framework_ids: Sequence[uuid.UUID] | None = None,
        control_ids: Sequence[uuid.UUID] | None = None,
    ) -> DocumentView:
        doc = await self._load(session, tenant_id, document_id)
        if doc.archived_at is not None:
            raise InvalidInput(
                "This document is archived, so its details can no longer be changed. "
                "Create a new document if you need an up to date version.",
                detail="an archived document cannot be edited; nothing to do",
            )
        before = AuditService.snapshot(doc, fields=_DOC_SNAPSHOT)
        for attr, value in (
            ("title", title.strip() if title else None),
            ("description", description),
            ("doc_type", doc_type),
            ("classification", classification),
            ("assigned_to", assigned_to),
            ("renewal_date", renewal_date),
        ):
            if value is not None:
                setattr(doc, attr, value)
        if clear_owner:
            doc.owner_membership_id = None
        elif owner_membership_id is not None:
            doc.owner_membership_id = owner_membership_id
        await self._set_links(
            session, tenant_id, doc.id, framework_ids=framework_ids, control_ids=control_ids
        )
        after = AuditService.snapshot(doc, fields=_DOC_SNAPSHOT)
        if before != after or framework_ids is not None or control_ids is not None:
            await self._audit.record(
                session,
                action="update",
                object_type="document",
                object_id=doc.id,
                actor=actor,
                tenant_id=tenant_id,
                before=before,
                after=after,
            )
        return await self._one(session, tenant_id, doc.id)

    async def archive_document(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        document_id: uuid.UUID,
        reason: str,
    ) -> DocumentView:
        doc = await self._load(session, tenant_id, document_id)
        if doc.archived_at is not None:
            return await self._one(session, tenant_id, doc.id)
        before = AuditService.snapshot(doc, fields=_DOC_SNAPSHOT)
        doc.archived_at = datetime.now(UTC)
        doc.archived_reason = reason.strip()
        doc.lifecycle = "archived"
        await self._audit.record(
            session,
            action="update",
            object_type="document",
            object_id=doc.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(doc, fields=_DOC_SNAPSHOT),
        )
        return await self._one(session, tenant_id, doc.id)

    async def save_content(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        document_id: uuid.UUID,
        content_html: str,
        change_type: str = "minor",
        summary: str | None = None,
    ) -> DocumentDetailView:
        doc = await self._load(session, tenant_id, document_id)
        if doc.archived_at is not None:
            raise InvalidInput(
                "This document is archived, so its content can no longer be edited. "
                "Create a new document if you need an up to date version.",
                detail="an archived document cannot be edited",
            )
        # Changing the text of an approved or published policy invalidates the
        # sign-off on it: the tiers were approved against words that no longer
        # exist, and every acknowledgement was given against them too. So the
        # document goes back to draft and its tiers reset, the same way a
        # rejection already sends it back (see decide_approval_tier). Without
        # this, a published policy could be rewritten while still reporting
        # itself approved, signed on the old dates, and fully acknowledged.
        demoted_from = None
        if doc.lifecycle in ("approved", "published"):
            demoted_from = doc.lifecycle
            doc_before = AuditService.snapshot(doc, fields=_DOC_SNAPSHOT)
            doc.lifecycle = "draft"
            doc.approved_at = None
            doc.published_at = None
            approvals = (
                await session.execute(
                    select(DocumentApproval).where(
                        DocumentApproval.tenant_id == tenant_id,
                        DocumentApproval.document_id == doc.id,
                    )
                )
            ).scalars()
            for approval in approvals:
                approval.status = "not_started"
                approval.decided_at = None
                approval.note = None
            await self._audit.record(
                session,
                action="transition",
                object_type="document",
                object_id=doc.id,
                actor=actor,
                tenant_id=tenant_id,
                before=doc_before,
                after=AuditService.snapshot(doc, fields=_DOC_SNAPSHOT),
            )
        # Editing an uploaded (PDF/Word) document converts it to an authored
        # HTML document from this version on (the file was parsed in the editor).
        doc.content_format = "html"
        current = (
            await session.get(DocumentVersion, doc.current_version_id)
            if doc.current_version_id
            else None
        )
        version = DocumentVersion(
            id=uuid7(),
            tenant_id=tenant_id,
            document_id=doc.id,
            version_no=_next_version(current.version_no if current else None, change_type),
            change_type=change_type,
            content_format="html",
            content_html=content_html,
            summary=summary or "Content edited.",
            created_by_membership_id=_membership(actor),
        )
        session.add(version)
        await session.flush([version])
        doc.current_version_id = version.id
        await self._audit.record(
            session,
            action="update",
            object_type="document",
            object_id=doc.id,
            actor=actor,
            tenant_id=tenant_id,
            before={
                "version": current.version_no if current else None,
                **({"lifecycle": demoted_from} if demoted_from else {}),
            },
            after={
                "version": version.version_no,
                **({"lifecycle": "draft"} if demoted_from else {}),
            },
        )
        return await self.get_document(
            session, tenant_id=tenant_id, document_id=doc.id, me=_membership(actor)
        )

    async def download(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, document_id: uuid.UUID
    ) -> tuple[bytes, str, str]:
        doc = await self._load(session, tenant_id, document_id)
        current = (
            await session.get(DocumentVersion, doc.current_version_id)
            if doc.current_version_id
            else None
        )
        if current is None or current.object_key is None:
            raise InvalidInput(
                "There is no file to download for this document. "
                "It was written in the editor, so open it to read the current version.",
                detail="this document has no uploaded file to download",
            )
        data = self._store.open(tenant_id, current.object_key)
        return (
            data,
            current.filename or "document",
            current.content_type or "application/octet-stream",
        )

    # -- workflow ------------------------------------------------------------

    async def _approval_children(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        approval_ids: Sequence[uuid.UUID],
        names: dict[uuid.UUID, str],
    ) -> tuple[
        dict[uuid.UUID, list[ApprovalTargetView]], dict[uuid.UUID, list[ApprovalAssigneeView]]
    ]:
        """Targets and assignees for a batch of tiers, one query each."""
        if not approval_ids:
            return {}, {}
        target_rows = (
            (
                await session.execute(
                    select(DocumentApprovalTarget)
                    .where(
                        DocumentApprovalTarget.tenant_id == tenant_id,
                        DocumentApprovalTarget.approval_id.in_(approval_ids),
                    )
                    .order_by(
                        DocumentApprovalTarget.target_type, DocumentApprovalTarget.target_name
                    )
                )
            )
            .scalars()
            .all()
        )
        assignee_rows = (
            (
                await session.execute(
                    select(DocumentApprovalAssignee).where(
                        DocumentApprovalAssignee.tenant_id == tenant_id,
                        DocumentApprovalAssignee.approval_id.in_(approval_ids),
                    )
                )
            )
            .scalars()
            .all()
        )
        targets: dict[uuid.UUID, list[ApprovalTargetView]] = defaultdict(list)
        for t in target_rows:
            targets[t.approval_id].append(
                ApprovalTargetView(
                    target_type=t.target_type, target_id=t.target_id, target_name=t.target_name
                )
            )
        assignees: dict[uuid.UUID, list[ApprovalAssigneeView]] = defaultdict(list)
        for a in assignee_rows:
            assignees[a.approval_id].append(
                ApprovalAssigneeView(
                    membership_id=a.membership_id,
                    name=names.get(a.membership_id, "Unknown"),
                    decision=a.decision,
                    decided_at=a.decided_at,
                    note=a.note,
                )
            )
        return dict(targets), dict(assignees)

    async def _resolve_tier_targets(
        self, session: AsyncSession, tenant_id: uuid.UUID, targets: RecipientSelection
    ) -> tuple[list[tuple[str, uuid.UUID, str]], dict[uuid.UUID, list[uuid.UUID]]]:
        """Turn a (users, roles, groups) selection into rows to store, plus the
        membership -> [target_id] map to create assignees from. The SELECTION is
        kept (not just the resolved people), because a tier's completion rule
        needs it: every named person, and at least one from each role/group
        (mirrors campaigns' ``_resolve_recipients``, but for that reason cannot
        reuse it as-is)."""
        from verity.modules.iam.service import iam_service  # noqa: PLC0415

        members = await iam_service.list_members(session, tenant_id=tenant_id)
        roles = await iam_service.list_roles(session, tenant_id=tenant_id)
        groups = await iam_service.list_groups(session, tenant_id=tenant_id)
        valid = {m.membership_id for m in members}
        name_by_member = {m.membership_id: m.full_name for m in members}
        role_by_id = {r.id: r for r in roles}
        group_by_id = {g.id: g for g in groups}
        members_by_role: dict[str, list[uuid.UUID]] = defaultdict(list)
        for m in members:
            for rn in m.role_names:
                members_by_role[rn].append(m.membership_id)

        rows: list[tuple[str, uuid.UUID, str]] = []
        member_targets: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)

        for uid in targets.user_ids:
            if uid not in valid:
                continue
            rows.append(("user", uid, name_by_member[uid]))
            member_targets[uid].append(uid)
        for rid in targets.role_ids:
            role = role_by_id.get(rid)
            if role is None:
                continue
            rows.append(("role", rid, role.name))
            for mid in members_by_role.get(role.name, []):
                member_targets[mid].append(rid)
        for gid in targets.group_ids:
            group = group_by_id.get(gid)
            if group is None:
                continue
            rows.append(("group", gid, group.name))
            for mid in group.member_ids:
                if mid in valid:
                    member_targets[mid].append(gid)
        return rows, dict(member_targets)

    async def _tier_row(
        self, session: AsyncSession, tenant_id: uuid.UUID, document_id: uuid.UUID, tier: int
    ) -> DocumentApproval | None:
        return (
            await session.execute(
                select(DocumentApproval).where(
                    DocumentApproval.tenant_id == tenant_id,
                    DocumentApproval.document_id == document_id,
                    DocumentApproval.tier == tier,
                )
            )
        ).scalar_one_or_none()

    async def _tier_has_targets(
        self, session: AsyncSession, tenant_id: uuid.UUID, approval_id: uuid.UUID
    ) -> bool:
        return (
            await session.execute(
                select(DocumentApprovalTarget.id)
                .where(
                    DocumentApprovalTarget.tenant_id == tenant_id,
                    DocumentApprovalTarget.approval_id == approval_id,
                )
                .limit(1)
            )
        ).first() is not None

    async def _tier_satisfied(
        self, session: AsyncSession, tenant_id: uuid.UUID, approval_id: uuid.UUID
    ) -> bool:
        """Every named person on the tier approved, and at least one resolved
        member of each role/group did. Stored, not re-resolved: a role/group
        membership change after assignment does not retroactively unlock or
        lock a tier."""
        target_ids = (
            (
                await session.execute(
                    select(DocumentApprovalTarget.target_id).where(
                        DocumentApprovalTarget.tenant_id == tenant_id,
                        DocumentApprovalTarget.approval_id == approval_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        assignees = (
            (
                await session.execute(
                    select(DocumentApprovalAssignee).where(
                        DocumentApprovalAssignee.tenant_id == tenant_id,
                        DocumentApprovalAssignee.approval_id == approval_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        satisfied: set[uuid.UUID] = set()
        for a in assignees:
            if a.decision == "approved":
                satisfied.update(uuid.UUID(x) for x in a.source_target_ids)
        return all(tid in satisfied for tid in target_ids)

    async def assign_approval_tier(  # noqa: PLR0912, PLR0913, PLR0915
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        document_id: uuid.UUID,
        tier: int,
        targets: RecipientSelection,
    ) -> DocumentView:
        """Set who reviews/approves a tier. Assigning tier 1 on a draft (or
        expired) document IS what starts the review: it moves the document to
        ``needs_approval`` and notifies every assignee immediately, there is no
        separate "send for review" step. Assigning tier 2 while tier 1 is still
        open just stages it - its assignees are notified once tier 1 clears."""
        if tier not in range(1, _APPROVAL_TIERS + 1):
            raise InvalidInput("There is no such review step.", detail=f"tier {tier} out of range")
        doc = await self._load(session, tenant_id, document_id)
        if doc.owner_membership_id is None:
            raise InvalidInput(
                "Give this document an owner before assigning reviewers or approvers.",
                detail="assign an owner before assigning a tier",
            )
        if doc.lifecycle not in ("draft", "expired", "needs_approval"):
            raise InvalidInput(
                "This document is not open for review right now. Refresh the page to see "
                "where it stands.",
                detail=f"cannot assign a tier on a {doc.lifecycle} document",
            )
        if tier > 1:
            first = await self._tier_row(session, tenant_id, doc.id, 1)
            if first is None or not await self._tier_has_targets(session, tenant_id, first.id):
                raise InvalidInput(
                    "Assign tier 1 first. Tiers sign off in order.",
                    detail="tier 1 has no targets yet",
                )

        # First assignment on a draft/expired document starts a fresh review -
        # clear anything left from an earlier, rejected pass (rows cascade to
        # their targets and assignees) and recreate every tier row.
        if tier == 1 and doc.lifecycle in ("draft", "expired"):
            await session.execute(
                delete(DocumentApproval).where(
                    DocumentApproval.tenant_id == tenant_id,
                    DocumentApproval.document_id == document_id,
                )
            )
            await session.flush()
            for t in range(1, _APPROVAL_TIERS + 1):
                session.add(
                    DocumentApproval(
                        id=uuid7(), tenant_id=tenant_id, document_id=doc.id, tier=t,
                        status="not_started",
                    )
                )
            await session.flush()

        approval = await self._tier_row(session, tenant_id, doc.id, tier)
        if approval is None:
            # Tier 2 assigned before tier 1 has ever run in this pass: make sure
            # every row up to this tier exists so it has somewhere to stage.
            for t in range(1, tier + 1):
                if await self._tier_row(session, tenant_id, doc.id, t) is None:
                    session.add(
                        DocumentApproval(
                            id=uuid7(), tenant_id=tenant_id, document_id=doc.id, tier=t,
                            status="not_started",
                        )
                    )
            await session.flush()
            approval = await self._tier_row(session, tenant_id, doc.id, tier)
        assert approval is not None  # noqa: S101 - the row was just ensured above

        if approval.status in ("approved", "rejected"):
            raise Conflict(
                "This step has already been decided, so it can no longer be reassigned. "
                "Resubmit the document to start a new review.",
                detail=f"tier {tier} is already {approval.status}",
            )

        target_rows, member_targets = await self._resolve_tier_targets(session, tenant_id, targets)
        if not target_rows:
            raise InvalidInput(
                "Choose at least one person, role or group for this step.",
                detail="no targets resolved",
            )

        existing = {
            a.membership_id: a
            for a in (
                await session.execute(
                    select(DocumentApprovalAssignee).where(
                        DocumentApprovalAssignee.tenant_id == tenant_id,
                        DocumentApprovalAssignee.approval_id == approval.id,
                    )
                )
            ).scalars()
        }
        await session.execute(
            delete(DocumentApprovalTarget).where(
                DocumentApprovalTarget.tenant_id == tenant_id,
                DocumentApprovalTarget.approval_id == approval.id,
            )
        )
        for t_type, t_id, t_name in target_rows:
            session.add(
                DocumentApprovalTarget(
                    id=uuid7(), tenant_id=tenant_id, approval_id=approval.id,
                    target_type=t_type, target_id=t_id, target_name=t_name,
                )
            )

        newly_added: list[uuid.UUID] = []
        for mid, tids in member_targets.items():
            row = existing.pop(mid, None)
            if row is None:
                row = DocumentApprovalAssignee(
                    id=uuid7(), tenant_id=tenant_id, approval_id=approval.id, membership_id=mid,
                )
                session.add(row)
                newly_added.append(mid)
            row.source_target_ids = [str(x) for x in tids]
        # Anyone no longer covered by any target on this tier: their old
        # decision no longer means anything against the new picks.
        for row in existing.values():
            await session.delete(row)
        await session.flush()

        before = AuditService.snapshot(doc, fields=_DOC_SNAPSHOT)
        starting_review = doc.lifecycle in ("draft", "expired")
        prior = await self._tier_row(session, tenant_id, doc.id, tier - 1) if tier > 1 else None
        gate_open = tier == 1 or (prior is not None and prior.status == "approved")
        if starting_review:
            doc.lifecycle = "needs_approval"
        if gate_open:
            approval.status = "pending"
        await self._audit.record(
            session, action="update", object_type="document_approval", object_id=approval.id,
            actor=actor, tenant_id=tenant_id,
            after={"tier": tier, "targets": [name for _t, _i, name in target_rows]},
        )
        if starting_review:
            await self._audit.record(
                session, action="transition", object_type="document", object_id=doc.id,
                actor=actor, tenant_id=tenant_id, before=before,
                after=AuditService.snapshot(doc, fields=_DOC_SNAPSHOT),
            )

        if gate_open and newly_added:
            await self._notify().notify_many(
                session, tenant_id=tenant_id, recipients=newly_added, kind="assigned",
                title=f"Please review: {doc.title}",
                body=(
                    f"You've been asked to review {doc.code} (tier {tier}). Open it to read, "
                    "comment and confirm."
                ),
                object_type="document_approval", object_id=approval.id,
            )
        return await self._one(session, tenant_id, doc.id)

    async def decide_approval_tier(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        document_id: uuid.UUID,
        tier: int,
        decision: str,
        note: str | None = None,
    ) -> DocumentView:
        """A single assignee's own decision on a tier they were asked to sign
        off - never a blanket "approve tier N" by anyone with the permission.
        Approving may cascade: it can satisfy the tier, which activates and
        notifies the next tier's assignees, or, on the last tier, both approves
        AND publishes the document in one motion (no separate publish click)."""
        doc = await self._load(session, tenant_id, document_id)
        approval = await self._tier_row(session, tenant_id, doc.id, tier)
        if approval is None or approval.status != "pending":
            raise Conflict(
                "This step is not open for a decision right now. Refresh the page to see "
                "where it stands.",
                detail=f"tier {tier} is not pending",
            )
        my_id = _membership(actor)
        assignee = (
            await session.execute(
                select(DocumentApprovalAssignee).where(
                    DocumentApprovalAssignee.tenant_id == tenant_id,
                    DocumentApprovalAssignee.approval_id == approval.id,
                    DocumentApprovalAssignee.membership_id == my_id,
                )
            )
        ).scalar_one_or_none()
        if assignee is None:
            raise PermissionDenied(
                "You were not asked to review this step, so you cannot decide it.",
                detail=f"{my_id} is not an assignee of tier {tier}",
            )
        if assignee.decision != "pending":
            raise Conflict(
                "You already made a decision on this step.",
                detail=f"assignee {assignee.id} already decided {assignee.decision}",
            )

        now = datetime.now(UTC)
        assignee.decision = decision
        assignee.decided_at = now
        assignee.note = note
        await session.flush()
        await self._audit.record(
            session, action="approve", object_type="document_approval_assignee",
            object_id=assignee.id, actor=actor, tenant_id=tenant_id,
            after={"tier": tier, "decision": decision},
        )

        if decision == "rejected":
            before = AuditService.snapshot(doc, fields=_DOC_SNAPSHOT)
            approval.status = "rejected"
            approval.decided_at = now
            approval.note = note
            doc.lifecycle = "draft"
            await self._audit.record(
                session, action="transition", object_type="document", object_id=doc.id,
                actor=actor, tenant_id=tenant_id, before=before,
                after=AuditService.snapshot(doc, fields=_DOC_SNAPSHOT),
            )
            return await self._one(session, tenant_id, doc.id)

        if not await self._tier_satisfied(session, tenant_id, approval.id):
            # Other assignees on this tier still have to weigh in.
            return await self._one(session, tenant_id, doc.id)

        approval.status = "approved"
        approval.decided_at = now
        await self._audit.record(
            session, action="transition", object_type="document_approval", object_id=approval.id,
            actor=actor, tenant_id=tenant_id, after={"status": "approved"},
        )

        nxt = await self._tier_row(session, tenant_id, doc.id, tier + 1)
        if nxt is not None and await self._tier_has_targets(session, tenant_id, nxt.id):
            nxt.status = "pending"
            await self._audit.record(
                session, action="transition", object_type="document_approval", object_id=nxt.id,
                actor=actor, tenant_id=tenant_id, after={"status": "pending"},
            )
            pending_next = (
                (
                    await session.execute(
                        select(DocumentApprovalAssignee.membership_id).where(
                            DocumentApprovalAssignee.tenant_id == tenant_id,
                            DocumentApprovalAssignee.approval_id == nxt.id,
                            DocumentApprovalAssignee.decision == "pending",
                        )
                    )
                )
                .scalars()
                .all()
            )
            if pending_next:
                await self._notify().notify_many(
                    session, tenant_id=tenant_id, recipients=pending_next, kind="assigned",
                    title=f"Please review: {doc.title}",
                    body=(
                        f"You've been asked to review {doc.code} (tier {nxt.tier}). Open it "
                        "to read, comment and confirm."
                    ),
                    object_type="document_approval", object_id=nxt.id,
                )
            return await self._one(session, tenant_id, doc.id)

        if nxt is None:
            # No further tier at all: fully approved, publish in the same motion.
            before = AuditService.snapshot(doc, fields=_DOC_SNAPSHOT)
            doc.approved_at = now
            doc.lifecycle = "approved"
            await self._audit.record(
                session, action="transition", object_type="document", object_id=doc.id,
                actor=actor, tenant_id=tenant_id, before=before,
                after=AuditService.snapshot(doc, fields=_DOC_SNAPSHOT),
            )
            before = AuditService.snapshot(doc, fields=_DOC_SNAPSHOT)
            doc.published_at = now
            doc.lifecycle = "published"
            await self._audit.record(
                session, action="transition", object_type="document", object_id=doc.id,
                actor=actor, tenant_id=tenant_id, before=before,
                after=AuditService.snapshot(doc, fields=_DOC_SNAPSHOT),
            )
        # else: tier N+1 exists but the owner has not assigned it yet - the
        # document stays needs_approval until they do.
        return await self._one(session, tenant_id, doc.id)

    async def my_pending_approvals(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, membership_id: uuid.UUID
    ) -> list[PendingApprovalView]:
        rows = (
            await session.execute(
                select(DocumentApprovalAssignee, DocumentApproval, Document)
                .join(DocumentApproval, DocumentApprovalAssignee.approval_id == DocumentApproval.id)
                .join(Document, DocumentApproval.document_id == Document.id)
                .where(
                    DocumentApprovalAssignee.tenant_id == tenant_id,
                    DocumentApprovalAssignee.membership_id == membership_id,
                    DocumentApprovalAssignee.decision == "pending",
                    DocumentApproval.status == "pending",
                )
                .order_by(DocumentApprovalAssignee.created_at)
            )
        ).all()
        return [
            PendingApprovalView(
                document_id=doc.id,
                document_code=doc.code,
                document_title=doc.title,
                tier=appr.tier,
            )
            for _assignee, appr, doc in rows
        ]

    async def my_pending_approval_count(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, membership_id: uuid.UUID
    ) -> int:
        return (
            await session.execute(
                select(func.count())
                .select_from(DocumentApprovalAssignee)
                .join(
                    DocumentApproval, DocumentApproval.id == DocumentApprovalAssignee.approval_id
                )
                .where(
                    DocumentApprovalAssignee.tenant_id == tenant_id,
                    DocumentApprovalAssignee.membership_id == membership_id,
                    DocumentApprovalAssignee.decision == "pending",
                    DocumentApproval.status == "pending",
                )
            )
        ).scalar_one()

    async def publish(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor, document_id: uuid.UUID
    ) -> DocumentView:
        doc = await self._load(session, tenant_id, document_id)
        if doc.lifecycle != "approved":
            raise InvalidInput(
                "This document has to be fully approved before it can be published. "
                "Send it for review first.",
                detail="only an approved document can be published",
            )
        before = AuditService.snapshot(doc, fields=_DOC_SNAPSHOT)
        doc.lifecycle = "published"
        doc.published_at = datetime.now(UTC)
        await self._audit.record(
            session,
            action="transition",
            object_type="document",
            object_id=doc.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(doc, fields=_DOC_SNAPSHOT),
        )
        return await self._one(session, tenant_id, doc.id)

    async def acknowledge(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        membership_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> None:
        doc = await self._load(session, tenant_id, document_id)
        if doc.lifecycle != "published":
            raise InvalidInput(
                "This document can only be acknowledged once it has been published. "
                "Check back when the owner publishes it.",
                detail="only a published document can be acknowledged",
            )
        if doc.current_version_id is None:
            raise InvalidInput(
                "This document has no content yet, so there is nothing to acknowledge. "
                "Ask the owner to add content and publish it.",
                detail="this document has no current version",
            )
        existing = (
            await session.execute(
                select(DocumentAcknowledgement.id).where(
                    DocumentAcknowledgement.tenant_id == tenant_id,
                    DocumentAcknowledgement.document_id == document_id,
                    DocumentAcknowledgement.membership_id == membership_id,
                )
            )
        ).first()
        if existing is not None:
            return
        session.add(
            DocumentAcknowledgement(
                id=uuid7(),
                tenant_id=tenant_id,
                document_id=doc.id,
                version_id=doc.current_version_id,
                membership_id=membership_id,
            )
        )
        await session.flush()

    # -- acknowledgement campaigns -------------------------------------------

    async def _load_campaign(
        self, session: AsyncSession, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> DocumentAckCampaign:
        camp = await session.get(DocumentAckCampaign, campaign_id)
        if camp is None or camp.tenant_id != tenant_id:
            raise NotFound(
                "This acknowledgement request no longer exists. It may have been deleted.",
                detail=f"campaign {campaign_id}",
            )
        return camp

    async def _resolve_recipients(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        reviewers: RecipientSelection,
        approvers: RecipientSelection,
    ) -> tuple[dict[uuid.UUID, tuple[str, str]], list[Any]]:
        """Turn the (users, roles, groups) selections for each kind into one
        (kind, source) per membership. Approver beats reviewer; a directly named
        user beats a role or group they also fall under. Returns the resolved
        map plus the member list (reused for name lookups)."""
        from verity.modules.iam.service import iam_service  # noqa: PLC0415

        members = await iam_service.list_members(session, tenant_id=tenant_id)
        roles = await iam_service.list_roles(session, tenant_id=tenant_id)
        groups = await iam_service.list_groups(session, tenant_id=tenant_id)
        valid = {m.membership_id for m in members}
        role_name = {r.id: r.name for r in roles}
        group_members = {g.id: list(g.member_ids) for g in groups}
        members_by_role: dict[str, list[uuid.UUID]] = {}
        for m in members:
            for rn in m.role_names:
                members_by_role.setdefault(rn, []).append(m.membership_id)

        resolved: dict[uuid.UUID, tuple[str, str]] = {}

        def add(mid: uuid.UUID, kind: str, source: str) -> None:
            if mid not in valid:
                return
            current = resolved.get(mid)
            # Approver always wins; within a kind, keep the first (most specific).
            if current is not None and not (kind == "approver" and current[0] == "reviewer"):
                return
            resolved[mid] = (kind, source)

        # Reviewers first, approvers second so approver overrides on overlap.
        for kind, sel in (("reviewer", reviewers), ("approver", approvers)):
            for uid in sel.user_ids:
                add(uid, kind, "user")
            for rid in sel.role_ids:
                for mid in members_by_role.get(role_name.get(rid, ""), []):
                    add(mid, kind, "role")
            for gid in sel.group_ids:
                for mid in group_members.get(gid, []):
                    add(mid, kind, "group")

        return resolved, list(members)

    async def create_campaign(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        document_id: uuid.UUID,
        title: str,
        message: str | None,
        reviewers: RecipientSelection,
        approvers: RecipientSelection,
        due_at: datetime | None = None,
    ) -> CampaignView:
        doc = await self._load(session, tenant_id, document_id)
        resolved, members = await self._resolve_recipients(
            session, tenant_id, reviewers, approvers
        )
        if not resolved:
            raise InvalidInput(
                "Choose at least one person, role or group to acknowledge this document. "
                "If you already picked someone, they may no longer be a member here.",
                detail="select at least one person, role or group to acknowledge",
            )

        camp = DocumentAckCampaign(
            id=uuid7(),
            tenant_id=tenant_id,
            document_id=doc.id,
            title=title,
            message=message,
            created_by_membership_id=_membership(actor),
            status="active",
            due_at=due_at,
        )
        session.add(camp)
        await session.flush()
        for mid, (kind, source) in resolved.items():
            session.add(
                DocumentAckCampaignRecipient(
                    id=uuid7(),
                    tenant_id=tenant_id,
                    campaign_id=camp.id,
                    membership_id=mid,
                    kind=kind,
                    source=source,
                    status="pending",
                )
            )
        await session.flush()

        await self._audit.record(
            session,
            action="create",
            object_type="document_ack_campaign",
            object_id=camp.id,
            actor=actor,
            tenant_id=tenant_id,
            after=AuditService.snapshot(camp, fields=_CAMPAIGN_SNAPSHOT),
        )
        await self._notify().notify_many(
            session,
            tenant_id=tenant_id,
            recipients=list(resolved),
            kind="assigned",
            title=f"Please acknowledge: {doc.title}",
            body=message or f"You've been asked to read and acknowledge {doc.code}.",
            object_type="document_ack_campaign",
            object_id=camp.id,
        )
        return await self._campaign_view(session, tenant_id, camp, members=members)

    async def list_document_campaigns(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, document_id: uuid.UUID
    ) -> list[CampaignSummaryView]:
        camps = list(
            (
                await session.execute(
                    select(DocumentAckCampaign)
                    .where(
                        DocumentAckCampaign.tenant_id == tenant_id,
                        DocumentAckCampaign.document_id == document_id,
                    )
                    .order_by(DocumentAckCampaign.created_at.desc())
                )
            ).scalars()
        )
        counts = await self._recipient_counts(session, tenant_id, [c.id for c in camps])
        out: list[CampaignSummaryView] = []
        for c in camps:
            total, ack = counts.get(c.id, (0, 0))
            out.append(
                CampaignSummaryView(
                    id=c.id,
                    document_id=c.document_id,
                    title=c.title,
                    status=c.status,
                    due_at=c.due_at,
                    closed_at=c.closed_at,
                    created_at=c.created_at,
                    total=total,
                    acknowledged=ack,
                    pending=total - ack,
                )
            )
        return out

    async def get_campaign(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> CampaignView:
        camp = await self._load_campaign(session, tenant_id, campaign_id)
        return await self._campaign_view(session, tenant_id, camp)

    async def my_pending_campaigns(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, membership_id: uuid.UUID
    ) -> list[PendingCampaignView]:
        rows = list(
            (
                await session.execute(
                    select(DocumentAckCampaignRecipient, DocumentAckCampaign, Document)
                    .join(
                        DocumentAckCampaign,
                        DocumentAckCampaign.id == DocumentAckCampaignRecipient.campaign_id,
                    )
                    .join(Document, Document.id == DocumentAckCampaign.document_id)
                    .where(
                        DocumentAckCampaignRecipient.tenant_id == tenant_id,
                        DocumentAckCampaignRecipient.membership_id == membership_id,
                        DocumentAckCampaignRecipient.status == "pending",
                        DocumentAckCampaign.status == "active",
                    )
                    .order_by(DocumentAckCampaign.created_at.desc())
                )
            ).all()
        )
        names = await self._member_names(session, tenant_id)
        return [
            PendingCampaignView(
                id=camp.id,
                document_id=doc.id,
                document_code=doc.code,
                document_title=doc.title,
                title=camp.title,
                message=camp.message,
                kind=rec.kind,
                due_at=camp.due_at,
                created_at=camp.created_at,
                created_by_name=_name_of(names, camp.created_by_membership_id),
            )
            for rec, camp, doc in rows
        ]

    async def my_pending_count(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, membership_id: uuid.UUID
    ) -> int:
        return (
            await session.execute(
                select(func.count())
                .select_from(DocumentAckCampaignRecipient)
                .join(
                    DocumentAckCampaign,
                    DocumentAckCampaign.id == DocumentAckCampaignRecipient.campaign_id,
                )
                .where(
                    DocumentAckCampaignRecipient.tenant_id == tenant_id,
                    DocumentAckCampaignRecipient.membership_id == membership_id,
                    DocumentAckCampaignRecipient.status == "pending",
                    DocumentAckCampaign.status == "active",
                )
            )
        ).scalar_one()

    async def acknowledge_campaign(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        membership_id: uuid.UUID,
        campaign_id: uuid.UUID,
        comment: str | None = None,
    ) -> CampaignView:
        camp = await self._load_campaign(session, tenant_id, campaign_id)
        if camp.status != "active":
            raise InvalidInput(
                "This acknowledgement request has been closed, so it can no longer be signed. "
                "Contact the person who sent it if you still need to respond.",
                detail="this campaign is closed",
            )
        rec = (
            await session.execute(
                select(DocumentAckCampaignRecipient).where(
                    DocumentAckCampaignRecipient.tenant_id == tenant_id,
                    DocumentAckCampaignRecipient.campaign_id == campaign_id,
                    DocumentAckCampaignRecipient.membership_id == membership_id,
                )
            )
        ).scalar_one_or_none()
        if rec is None:
            raise NotFound(
                "You have not been asked to acknowledge this document, so there is nothing "
                "to sign. Contact the person who sent the request if you think that is wrong.",
                detail="you are not a recipient of this campaign",
            )
        if rec.status != "acknowledged":
            before = AuditService.snapshot(rec, fields=_RECIPIENT_SNAPSHOT)
            rec.status = "acknowledged"
            rec.acknowledged_at = datetime.now(UTC)
            rec.ack_comment = comment
            await session.flush()
            await self._audit.record(
                session,
                action="approve",
                object_type="document_ack_campaign",
                object_id=camp.id,
                actor=actor,
                tenant_id=tenant_id,
                before=before,
                after=AuditService.snapshot(rec, fields=_RECIPIENT_SNAPSHOT),
            )
            names = await self._member_names(session, tenant_id)
            who = names.get(membership_id, "Someone")
            await self._notify().notify_many(
                session,
                tenant_id=tenant_id,
                recipients=[camp.created_by_membership_id],
                kind="approval",
                title=f"{who} acknowledged {camp.title}",
                body=comment or "",
                object_type="document_ack_campaign",
                object_id=camp.id,
            )
        return await self._campaign_view(session, tenant_id, camp)

    async def add_campaign_comment(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        campaign_id: uuid.UUID,
        body: str,
        mentioned_ids: Sequence[uuid.UUID] = (),
    ) -> CampaignView:
        camp = await self._load_campaign(session, tenant_id, campaign_id)
        comment = DocumentAckCampaignComment(
            id=uuid7(),
            tenant_id=tenant_id,
            campaign_id=camp.id,
            author_membership_id=_membership(actor),
            body=body,
            mentioned_ids=[str(m) for m in mentioned_ids],
        )
        session.add(comment)
        await session.flush()
        await self._audit.record(
            session,
            action="create",
            object_type="document_ack_campaign_comment",
            object_id=comment.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"campaign_id": str(camp.id), "body": body},
        )
        # Owner and anyone tagged hear about it (the author is dropped by notify_many).
        recipients: list[uuid.UUID | None] = [camp.created_by_membership_id, *mentioned_ids]
        await self._notify().notify_many(
            session,
            tenant_id=tenant_id,
            recipients=[r for r in recipients if r != _membership(actor)],
            kind="comment",
            title=f"New comment on {camp.title}",
            body=body,
            object_type="document_ack_campaign",
            object_id=camp.id,
        )
        return await self._campaign_view(session, tenant_id, camp)

    async def close_campaign(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor, campaign_id: uuid.UUID
    ) -> CampaignView:
        camp = await self._load_campaign(session, tenant_id, campaign_id)
        if camp.status != "closed":
            before = AuditService.snapshot(camp, fields=_CAMPAIGN_SNAPSHOT)
            camp.status = "closed"
            camp.closed_at = datetime.now(UTC)
            await session.flush()
            await self._audit.record(
                session,
                action="transition",
                object_type="document_ack_campaign",
                object_id=camp.id,
                actor=actor,
                tenant_id=tenant_id,
                before=before,
                after=AuditService.snapshot(camp, fields=_CAMPAIGN_SNAPSHOT),
            )
        return await self._campaign_view(session, tenant_id, camp)

    # -- campaign helpers ----------------------------------------------------

    def _notify(self) -> NotificationService:
        from verity.modules.notifications.service import notification_service  # noqa: PLC0415

        return notification_service

    async def _member_names(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        return await self._owner_names(session, tenant_id)

    async def _recipient_counts(
        self, session: AsyncSession, tenant_id: uuid.UUID, campaign_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[int, int]]:
        """Per campaign, (total, acknowledged) in one grouped query."""
        if not campaign_ids:
            return {}
        rows = (
            await session.execute(
                select(
                    DocumentAckCampaignRecipient.campaign_id,
                    func.count().label("total"),
                    func.count()
                    .filter(DocumentAckCampaignRecipient.status == "acknowledged")
                    .label("ack"),
                )
                .where(
                    DocumentAckCampaignRecipient.tenant_id == tenant_id,
                    DocumentAckCampaignRecipient.campaign_id.in_(campaign_ids),
                )
                .group_by(DocumentAckCampaignRecipient.campaign_id)
            )
        ).all()
        return {cid: (total, ack) for cid, total, ack in rows}

    async def _campaign_view(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        camp: DocumentAckCampaign,
        *,
        members: Sequence[Any] | None = None,
    ) -> CampaignView:
        doc = await session.get(Document, camp.document_id)
        names = await self._member_names(session, tenant_id)
        emails: dict[uuid.UUID, str] = {}
        if members is None:
            from verity.modules.iam.service import iam_service  # noqa: PLC0415

            members = await iam_service.list_members(session, tenant_id=tenant_id)
        for m in members:
            emails[m.membership_id] = m.email

        rec_rows = list(
            (
                await session.execute(
                    select(DocumentAckCampaignRecipient)
                    .where(
                        DocumentAckCampaignRecipient.tenant_id == tenant_id,
                        DocumentAckCampaignRecipient.campaign_id == camp.id,
                    )
                    .order_by(DocumentAckCampaignRecipient.created_at)
                )
            ).scalars()
        )
        recipients = [
            CampaignRecipientView(
                membership_id=r.membership_id,
                name=names.get(r.membership_id, "Unknown"),
                email=emails.get(r.membership_id, ""),
                kind=r.kind,
                source=r.source,
                status=r.status,
                acknowledged_at=r.acknowledged_at,
                ack_comment=r.ack_comment,
            )
            for r in rec_rows
        ]

        com_rows = list(
            (
                await session.execute(
                    select(DocumentAckCampaignComment)
                    .where(
                        DocumentAckCampaignComment.tenant_id == tenant_id,
                        DocumentAckCampaignComment.campaign_id == camp.id,
                    )
                    .order_by(DocumentAckCampaignComment.created_at)
                )
            ).scalars()
        )
        comments = [
            CampaignCommentView(
                id=c.id,
                author_membership_id=c.author_membership_id,
                author_name=_name_of(names, c.author_membership_id),
                body=c.body,
                mentioned_ids=list(c.mentioned_ids),
                mentioned_names=[
                    names.get(uuid.UUID(mid), "Unknown")
                    for mid in c.mentioned_ids
                    if _is_uuid(mid)
                ],
                created_at=c.created_at,
            )
            for c in com_rows
        ]

        ack = sum(1 for r in rec_rows if r.status == "acknowledged")
        total = len(rec_rows)
        return CampaignView(
            id=camp.id,
            document_id=camp.document_id,
            document_code=doc.code if doc else "",
            document_title=doc.title if doc else "",
            title=camp.title,
            message=camp.message,
            status=camp.status,
            created_by_membership_id=camp.created_by_membership_id,
            created_by_name=_name_of(names, camp.created_by_membership_id),
            due_at=camp.due_at,
            closed_at=camp.closed_at,
            created_at=camp.created_at,
            total=total,
            acknowledged=ack,
            pending=total - ack,
            recipients=recipients,
            comments=comments,
        )

    # -- helper: one document's view (with current version_no) ---------------

    async def _one(
        self, session: AsyncSession, tenant_id: uuid.UUID, document_id: uuid.UUID
    ) -> DocumentView:
        # DocumentDetailView is a DocumentView; the detail load also fills the
        # current version_no, which the base view needs.
        return await self.get_document(session, tenant_id=tenant_id, document_id=document_id)


    # -- version history: what changed, and putting it back -------------------

    async def _version(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> DocumentVersion:
        row = await session.get(DocumentVersion, version_id)
        if row is None or row.tenant_id != tenant_id or row.document_id != document_id:
            raise NotFound(
                "That version of this document no longer exists.",
                detail=f"version {version_id} not on document {document_id}",
            )
        return row

    async def version_diff(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> VersionDiffView:
        """What this version changed, against the version immediately before it."""
        target = await self._version(session, tenant_id, document_id, version_id)
        previous = (
            await session.execute(
                select(DocumentVersion)
                .where(
                    DocumentVersion.tenant_id == tenant_id,
                    DocumentVersion.document_id == document_id,
                    DocumentVersion.created_at < target.created_at,
                )
                .order_by(DocumentVersion.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        names = await self._member_names(session, tenant_id)
        author = (
            names.get(target.created_by_membership_id)
            if target.created_by_membership_id
            else None
        )
        # An uploaded PDF or Word version has no text to compare. Say so rather
        # than rendering it as an empty document, which reads like a deletion.
        uploaded = target.content_html is None or (
            previous is not None and previous.content_html is None
        )
        if uploaded:
            return VersionDiffView(
                version_id=target.id,
                version_no=target.version_no,
                compared_with=previous.version_no if previous else None,
                created_at=target.created_at,
                created_by_name=author,
                summary=target.summary,
                blocks=[],
                stats=summarise([]),
                comparable=False,
                reason="This version is an uploaded file, so there is no text to compare.",
            )

        blocks = diff_html(previous.content_html if previous else None, target.content_html)
        return VersionDiffView(
            version_id=target.id,
            version_no=target.version_no,
            compared_with=previous.version_no if previous else None,
            created_at=target.created_at,
            created_by_name=author,
            summary=target.summary,
            blocks=blocks,
            stats=summarise(blocks),
            comparable=True,
            reason=None,
        )

    async def restore_version(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        document_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> DocumentDetailView:
        """Put an earlier version's text back, as a NEW version.

        ``document_versions`` is append-only behind a database trigger, so a
        restore can only ever move forward. That is the useful property: nothing
        is overwritten, the version you left is still in the list, and restoring
        it again is the redo. The version list is the undo stack, and it lives in
        Postgres, so it survives a reload and a different person.
        """
        target = await self._version(session, tenant_id, document_id, version_id)
        if target.content_html is None:
            raise InvalidInput(
                "That version is an uploaded file rather than authored text, so it "
                "cannot be restored into the editor. Download it instead.",
                detail="only an html version can be restored",
            )
        if target.id == (await self._load(session, tenant_id, document_id)).current_version_id:
            raise Conflict(
                "That version is already the current one.",
                detail="cannot restore the current version",
            )
        return await self.save_content(
            session,
            tenant_id=tenant_id,
            actor=actor,
            document_id=document_id,
            content_html=target.content_html,
            change_type="minor",
            summary=f"Restored from v{target.version_no}",
        )


    # -- shipped policy templates ---------------------------------------------

    async def list_templates(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[TemplateView]:
        """Every shipped policy, with whether this tenant has used it already."""
        rows = (
            await session.execute(select(DocumentTemplate).order_by(DocumentTemplate.title))
        ).scalars()
        used = set(
            (
                await session.execute(
                    select(Document.template_key).where(
                        Document.tenant_id == tenant_id,
                        Document.template_key.is_not(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        return [
            TemplateView(
                id=row.id,
                key=row.key,
                title=row.title,
                doc_type=row.doc_type,
                classification=row.classification,
                summary=row.summary,
                tags=list(row.tags or []),
                satisfies={k: list(v) for k, v in (row.satisfies or {}).items()},
                placeholders=[
                    PlaceholderView(
                        key=str(p.get("key")),
                        label=placeholder_lib.LABELS.get(
                            str(p.get("key")), str(p.get("key", "")).replace("_", " ").capitalize()
                        ),
                        count=int(str(p.get("count", 0) or 0)),
                    )
                    for p in (row.placeholders or [])
                ],
                word_count=row.word_count,
                optional_markers=row.optional_markers,
                already_used=row.key in used,
                source=row.source,
                source_url=row.source_url,
                license=row.license,
            )
            for row in rows
        ]

    async def create_from_template(  # noqa: PLR0913 — the instantiation contract
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        template_key: str,
        title: str | None = None,
        owner_membership_id: uuid.UUID | None = None,
    ) -> DocumentView:
        """Start a tenant draft from a shipped policy.

        The tenant gets a copy, not a reference: from here the text is theirs and
        nothing upstream can change it. ``{{company_name}}`` is filled in from
        the workspace name, because that is the one field the platform knows the
        answer to; everything else is left in place for someone to decide, and
        counted so the editor can say what is outstanding.
        """
        template = (
            await session.execute(
                select(DocumentTemplate).where(DocumentTemplate.key == template_key)
            )
        ).scalar_one_or_none()
        if template is None:
            raise NotFound(
                "That policy template is no longer available.",
                detail=f"template {template_key!r}",
            )

        tenant_name = await self._tenant_name(session, tenant_id)
        content = placeholder_lib.fill(
            template.content_html, {"company_name": tenant_name} if tenant_name else {}
        )
        view = await self.create_document(
            session,
            tenant_id=tenant_id,
            actor=actor,
            title=(title or template.title).strip(),
            doc_type=template.doc_type,
            classification=template.classification,
            description=template.summary,
            content_html=content,
            owner_membership_id=owner_membership_id,
        )
        # Record where it came from, for the attribution the licence requires
        # and so the picker can say a template has been used already.
        doc = await self._load(session, tenant_id, view.id)
        doc.template_key = template.key
        await session.flush()
        return view

    async def _tenant_name(self, session: AsyncSession, tenant_id: uuid.UUID) -> str | None:
        from verity.modules.tenancy.service import tenancy_service  # noqa: PLC0415

        try:
            tenant = await tenancy_service.get_tenant(session, tenant_id=tenant_id)
        except Exception:
            return None
        return getattr(tenant, "legal_name", None) or getattr(tenant, "name", None)


def _with_version(view: DocumentView, version_no: str | None) -> DocumentView:
    if version_no is None:
        return view
    return DocumentView(**{**view.__dict__, "version": version_no})


def _membership(actor: Actor) -> uuid.UUID | None:
    return getattr(actor, "id", None)


def _name_of(names: dict[uuid.UUID, str], mid: uuid.UUID | None) -> str:
    if mid is None:
        return "Unknown"
    return names.get(mid, "Unknown")


def _is_uuid(value: object) -> bool:
    try:
        uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return False
    return True


document_service = DocumentService()
