"""Documents & Policies service — library, versions, workflow, acknowledgements.

DB access lives here (no separate repository, matching the evidence module).
Cross-module reads go through sibling *services* (rule 4): owner/member names
via IAM, control codes via compliance's control service, framework names via
compliance. Files are held in the object store; a document's text is an
append-only ``document_versions`` row.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any, Final

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.core.storage import ObjectStore, get_object_store
from verity.modules.audit.service import Actor, AuditService, audit_service
from verity.modules.documents.models import (
    DOC_TYPES,
    TYPE_PREFIX,
    Document,
    DocumentAckCampaign,
    DocumentAckCampaignComment,
    DocumentAckCampaignRecipient,
    DocumentAcknowledgement,
    DocumentApproval,
    DocumentControl,
    DocumentFramework,
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
class ApprovalView:
    tier: int
    status: str
    approver_name: str | None
    decided_at: datetime | None
    note: str | None


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
            raise NotFound(detail=f"document {document_id}")
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
                    approver_name=(
                        owners.get(a.approver_membership_id) if a.approver_membership_id else None
                    ),
                    decided_at=a.decided_at,
                    note=a.note,
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
            raise InvalidInput(detail=f"unknown document type {doc_type!r}")
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
            raise InvalidInput(detail=f"unknown document type {doc_type!r}")
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
            raise InvalidInput(detail="an archived document cannot be edited; nothing to do")
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
            raise InvalidInput(detail="an archived document cannot be edited")
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
            before={"version": current.version_no if current else None},
            after={"version": version.version_no},
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
            raise InvalidInput(detail="this document has no uploaded file to download")
        data = self._store.open(tenant_id, current.object_key)
        return (
            data,
            current.filename or "document",
            current.content_type or "application/octet-stream",
        )

    # -- workflow ------------------------------------------------------------

    async def submit_for_approval(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        document_id: uuid.UUID,
        approver_ids: Sequence[uuid.UUID] | None = None,
    ) -> DocumentView:
        doc = await self._load(session, tenant_id, document_id)
        if doc.lifecycle not in ("draft", "expired"):
            raise InvalidInput(detail=f"a {doc.lifecycle} document cannot be submitted")
        if doc.owner_membership_id is None:
            raise InvalidInput(detail="assign an owner before sending for review")
        approvers = list(approver_ids or [])
        await session.execute(
            delete(DocumentApproval).where(
                DocumentApproval.tenant_id == tenant_id,
                DocumentApproval.document_id == document_id,
            )
        )
        for tier in range(1, _APPROVAL_TIERS + 1):
            session.add(
                DocumentApproval(
                    id=uuid7(),
                    tenant_id=tenant_id,
                    document_id=doc.id,
                    tier=tier,
                    status="pending" if tier == 1 else "not_started",
                    approver_membership_id=approvers[tier - 1]
                    if tier - 1 < len(approvers)
                    else None,
                )
            )
        before = AuditService.snapshot(doc, fields=_DOC_SNAPSHOT)
        doc.lifecycle = "needs_approval"
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

    async def decide_approval(  # noqa: PLR0913
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
        doc = await self._load(session, tenant_id, document_id)
        if doc.lifecycle != "needs_approval":
            raise InvalidInput(detail="this document is not awaiting approval")
        approval = (
            await session.execute(
                select(DocumentApproval).where(
                    DocumentApproval.tenant_id == tenant_id,
                    DocumentApproval.document_id == document_id,
                    DocumentApproval.tier == tier,
                )
            )
        ).scalar_one_or_none()
        if approval is None:
            raise NotFound(detail=f"approval tier {tier}")
        if approval.status != "pending":
            raise Conflict(detail=f"tier {tier} is not pending")
        approval.status = decision
        approval.approver_membership_id = _membership(actor)
        approval.decided_at = datetime.now(UTC)
        approval.note = note

        before = AuditService.snapshot(doc, fields=_DOC_SNAPSHOT)
        if decision == "rejected":
            doc.lifecycle = "draft"
        else:
            nxt = (
                await session.execute(
                    select(DocumentApproval).where(
                        DocumentApproval.tenant_id == tenant_id,
                        DocumentApproval.document_id == document_id,
                        DocumentApproval.tier == tier + 1,
                    )
                )
            ).scalar_one_or_none()
            if nxt is not None:
                nxt.status = "pending"
            else:
                doc.lifecycle = "approved"
                doc.approved_at = datetime.now(UTC)
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

    async def publish(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor, document_id: uuid.UUID
    ) -> DocumentView:
        doc = await self._load(session, tenant_id, document_id)
        if doc.lifecycle != "approved":
            raise InvalidInput(detail="only an approved document can be published")
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
            raise InvalidInput(detail="only a published document can be acknowledged")
        if doc.current_version_id is None:
            raise InvalidInput(detail="this document has no current version")
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
            raise NotFound(detail=f"campaign {campaign_id}")
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
            raise InvalidInput(detail="select at least one person, role or group to acknowledge")

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
            raise InvalidInput(detail="this campaign is closed")
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
            raise NotFound(detail="you are not a recipient of this campaign")
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
