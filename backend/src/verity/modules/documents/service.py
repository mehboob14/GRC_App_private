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
from typing import Final

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.core.storage import ObjectStore, get_object_store
from verity.modules.audit.service import Actor, AuditService, audit_service
from verity.modules.documents.models import (
    DOC_TYPES,
    TYPE_PREFIX,
    Document,
    DocumentAcknowledgement,
    DocumentApproval,
    DocumentControl,
    DocumentFramework,
    DocumentVersion,
)
from verity.shared.ids import uuid7

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


document_service = DocumentService()
