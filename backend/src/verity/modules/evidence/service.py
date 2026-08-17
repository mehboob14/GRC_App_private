"""The evidence library: add, map, refresh, retrieve.

Bytes go through ``core.storage``, which computes the sha256, sniffs the MIME
type from content rather than the filename, sanitises the name and enforces the
size cap. This module records the pointer it gets back — it never hashes or
sniffs on its own, so those guarantees hold identically on local disk today and
on S3 later (D12).

Freshness is computed here, never stored (D14): current / aging / stale is read
off ``renewal_date`` against today, so the answer is right the moment it is
asked, without a job having run.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import InvalidInput, NotFound
from verity.core.storage import ObjectStore, get_object_store
from verity.modules.audit.service import Actor, AuditService, audit_service
from verity.modules.evidence.models import (
    DEFAULT_VALIDITY_DAYS,
    Evidence,
    EvidenceControl,
)
from verity.shared.ids import uuid7

AGING_WINDOW_DAYS: Final = 30
"""How long before its renewal date an item starts reading as 'aging'. A cliff
from current straight to stale gives nobody time to act, which is most of the
reason to surface freshness at all."""

_SNAPSHOT: Final = (
    "id",
    "title",
    "evidence_type",
    "kind",
    "source_label",
    "owner_membership_id",
    "collected_at",
    "renewal_date",
    "sha256",
)


def freshness(renewal_date: date | None, *, today: date | None = None) -> str:
    """``current`` | ``aging`` | ``stale`` | ``no_expiry``.

    An item with no renewal date does not expire and is reported as such rather
    than quietly counted as current — "never expires" and "fine for now" are
    different claims to an auditor.
    """
    if renewal_date is None:
        return "no_expiry"
    now = today or datetime.now(UTC).date()
    if renewal_date < now:
        return "stale"
    if (renewal_date - now).days <= AGING_WINDOW_DAYS:
        return "aging"
    return "current"


def default_renewal_date(evidence_type: str, collected_at: date) -> date | None:
    """The renewal date a type suggests. Only ever a pre-fill — the caller may
    override it, and the API lets them (D13)."""
    days = DEFAULT_VALIDITY_DAYS.get(evidence_type)
    return collected_at + timedelta(days=days) if days else None


@dataclass(frozen=True, slots=True)
class EvidenceView:
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
    freshness: str
    filename: str | None
    content_type: str | None
    size_bytes: int | None
    sha256: str | None
    link_url: str | None
    control_ids: list[uuid.UUID] = field(default_factory=list)
    control_codes: list[str] = field(default_factory=list)


class EvidenceService:
    def __init__(self, audit: AuditService | None = None, store: ObjectStore | None = None) -> None:
        self._audit = audit or audit_service
        self._store = store or get_object_store()

    # -- reads ---------------------------------------------------------------

    async def list_evidence(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        evidence_type: str | None = None,
        control_id: uuid.UUID | None = None,
        freshness_filter: str | None = None,
    ) -> list[EvidenceView]:
        statement = select(Evidence).where(Evidence.tenant_id == tenant_id)
        if evidence_type is not None:
            statement = statement.where(Evidence.evidence_type == evidence_type)
        if control_id is not None:
            statement = statement.where(
                Evidence.id.in_(
                    select(EvidenceControl.evidence_id).where(
                        EvidenceControl.tenant_id == tenant_id,
                        EvidenceControl.control_id == control_id,
                    )
                )
            )
        rows = list(
            (await session.execute(statement.order_by(Evidence.collected_at.desc()))).scalars()
        )
        mappings = await self._mappings(session, tenant_id)
        owners = await self._owner_names(session, tenant_id)
        views = [self._view(row, mappings, owners) for row in rows]
        # Filtered after the query because freshness is derived, not a column.
        if freshness_filter:
            views = [view for view in views if view.freshness == freshness_filter]
        return views

    async def get(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, evidence_id: uuid.UUID
    ) -> EvidenceView:
        row = await self._load(session, tenant_id, evidence_id)
        return self._view(
            row,
            await self._mappings(session, tenant_id),
            await self._owner_names(session, tenant_id),
        )

    async def download(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, evidence_id: uuid.UUID
    ) -> tuple[bytes, str, str]:
        """Bytes, filename, content type. The store scopes every read to the
        tenant, so one tenant's key cannot address another's object."""
        row = await self._load(session, tenant_id, evidence_id)
        if row.kind != "file" or row.object_key is None:
            raise InvalidInput(detail="this evidence item is a link, not a stored file")
        data = self._store.open(tenant_id, row.object_key)
        return (
            data,
            row.filename or "evidence",
            row.content_type or "application/octet-stream",
        )

    async def _mappings(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, list[tuple[uuid.UUID, str]]]:
        """Every item's controls in one pass — the library shows them per row,
        and a per-row fetch would be an N+1 across the whole library.

        The join rows come from this module's own table; the human-readable
        control *codes* come from compliance's service, never its models
        (rule 4, enforced by import-linter).
        """
        from verity.modules.compliance.control_service import (  # noqa: PLC0415
            control_service,
        )

        links = await session.execute(
            select(EvidenceControl.evidence_id, EvidenceControl.control_id).where(
                EvidenceControl.tenant_id == tenant_id
            )
        )
        pairs = list(links)
        if not pairs:
            return {}

        controls = await control_service.list_controls(
            session, tenant_id=tenant_id, include_disabled=True
        )
        codes = {control.id: control.code for control in controls}

        out: dict[uuid.UUID, list[tuple[uuid.UUID, str]]] = {}
        for evidence_id, control_id in pairs:
            out.setdefault(evidence_id, []).append((control_id, codes.get(control_id, "?")))
        for mapped in out.values():
            mapped.sort(key=lambda item: item[1])
        return out

    async def _owner_names(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        """Through IAM's service, never its models (rule 4)."""
        from verity.modules.iam.service import iam_service  # noqa: PLC0415

        members = await iam_service.list_members(session, tenant_id=tenant_id)
        return {member.membership_id: member.full_name for member in members}

    @staticmethod
    def _view(
        row: Evidence,
        mappings: dict[uuid.UUID, list[tuple[uuid.UUID, str]]],
        owners: dict[uuid.UUID, str],
    ) -> EvidenceView:
        mapped = mappings.get(row.id, [])
        return EvidenceView(
            id=row.id,
            title=row.title,
            description=row.description,
            evidence_type=row.evidence_type,
            kind=row.kind,
            source_label=row.source_label,
            owner_membership_id=row.owner_membership_id,
            owner_name=(owners.get(row.owner_membership_id) if row.owner_membership_id else None),
            collected_at=row.collected_at,
            renewal_date=row.renewal_date,
            freshness=freshness(row.renewal_date),
            filename=row.filename,
            content_type=row.content_type,
            size_bytes=row.size_bytes,
            sha256=row.sha256,
            link_url=row.link_url,
            control_ids=[item[0] for item in mapped],
            control_codes=[item[1] for item in mapped],
        )

    async def _load(
        self, session: AsyncSession, tenant_id: uuid.UUID, evidence_id: uuid.UUID
    ) -> Evidence:
        row = await session.get(Evidence, evidence_id)
        if row is None or row.tenant_id != tenant_id:
            raise NotFound(detail=f"evidence {evidence_id}")
        return row

    # -- writes ---------------------------------------------------------------

    async def add_file(  # noqa: PLR0913 — the item's own fields, no more
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        title: str,
        filename: str,
        data: bytes,
        evidence_type: str,
        collected_at: date,
        description: str | None = None,
        source_label: str | None = None,
        owner_membership_id: uuid.UUID | None = None,
        renewal_date: date | None = None,
        control_ids: list[uuid.UUID] | None = None,
    ) -> EvidenceView:
        # The store hashes, sniffs and caps. Repeating any of that here would be
        # a second implementation of the same guarantee — one too many.
        stored = self._store.put(tenant_id, filename, data)
        row = Evidence(
            id=uuid7(),
            tenant_id=tenant_id,
            title=title.strip(),
            description=description,
            evidence_type=evidence_type,
            kind="file",
            source_label=source_label,
            owner_membership_id=owner_membership_id,
            collected_at=collected_at,
            renewal_date=(
                renewal_date
                if renewal_date is not None
                else default_renewal_date(evidence_type, collected_at)
            ),
            object_key=stored.key,
            filename=stored.original_filename,
            content_type=stored.content_type,
            size_bytes=stored.size_bytes,
            sha256=stored.sha256,
        )
        return await self._insert(session, row, actor, tenant_id, control_ids or [])

    async def add_link(  # noqa: PLR0913 — the item's own fields, no more
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        title: str,
        link_url: str,
        evidence_type: str,
        collected_at: date,
        description: str | None = None,
        source_label: str | None = None,
        owner_membership_id: uuid.UUID | None = None,
        renewal_date: date | None = None,
        control_ids: list[uuid.UUID] | None = None,
    ) -> EvidenceView:
        url = link_url.strip()
        if not url.lower().startswith(("http://", "https://")):
            raise InvalidInput(detail="a link must be an http or https URL")
        row = Evidence(
            id=uuid7(),
            tenant_id=tenant_id,
            title=title.strip(),
            description=description,
            evidence_type=evidence_type,
            kind="link",
            source_label=source_label,
            owner_membership_id=owner_membership_id,
            collected_at=collected_at,
            renewal_date=(
                renewal_date
                if renewal_date is not None
                else default_renewal_date(evidence_type, collected_at)
            ),
            link_url=url,
        )
        return await self._insert(session, row, actor, tenant_id, control_ids or [])

    async def _insert(
        self,
        session: AsyncSession,
        row: Evidence,
        actor: Actor,
        tenant_id: uuid.UUID,
        control_ids: list[uuid.UUID],
    ) -> EvidenceView:
        session.add(row)
        await session.flush([row])
        await self.map_controls(
            session, tenant_id=tenant_id, evidence_id=row.id, control_ids=control_ids
        )
        await self._audit.record(
            session,
            action="create",
            object_type="evidence",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after=AuditService.snapshot(row, fields=_SNAPSHOT),
        )
        return await self.get(session, tenant_id=tenant_id, evidence_id=row.id)

    async def update(  # noqa: PLR0913 — the editable fields, no more
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        evidence_id: uuid.UUID,
        title: str | None = None,
        description: str | None = None,
        evidence_type: str | None = None,
        source_label: str | None = None,
        owner_membership_id: uuid.UUID | None = None,
        clear_owner: bool = False,
        collected_at: date | None = None,
        renewal_date: date | None = None,
        control_ids: list[uuid.UUID] | None = None,
    ) -> EvidenceView:
        row = await self._load(session, tenant_id, evidence_id)
        before = AuditService.snapshot(row, fields=_SNAPSHOT)
        for attribute, value in (
            ("title", title),
            ("description", description),
            ("evidence_type", evidence_type),
            ("source_label", source_label),
            ("collected_at", collected_at),
            ("renewal_date", renewal_date),
        ):
            if value is not None:
                setattr(row, attribute, value)
        if clear_owner:
            row.owner_membership_id = None
        elif owner_membership_id is not None:
            row.owner_membership_id = owner_membership_id

        if control_ids is not None:
            await self.map_controls(
                session,
                tenant_id=tenant_id,
                evidence_id=evidence_id,
                control_ids=control_ids,
                replace=True,
            )

        await self._audit.record(
            session,
            action="update",
            object_type="evidence",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(row, fields=_SNAPSHOT),
        )
        return await self.get(session, tenant_id=tenant_id, evidence_id=evidence_id)

    async def map_controls(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        evidence_id: uuid.UUID,
        control_ids: list[uuid.UUID],
        replace: bool = False,
    ) -> None:
        """Attach an item to controls. One item satisfying many is the point of
        the join table, not an accident of it."""
        current = await session.execute(
            select(EvidenceControl).where(
                EvidenceControl.tenant_id == tenant_id,
                EvidenceControl.evidence_id == evidence_id,
            )
        )
        rows = {row.control_id: row for row in current.scalars()}
        if replace:
            for control_id, row in rows.items():
                if control_id not in control_ids:
                    await session.delete(row)
        added = [
            EvidenceControl(
                id=uuid7(),
                tenant_id=tenant_id,
                evidence_id=evidence_id,
                control_id=control_id,
            )
            for control_id in control_ids
            if control_id not in rows
        ]
        for row in added:
            session.add(row)
        # Flush before returning: the caller builds its response by re-reading
        # the mappings, and an unflushed row would make the response disagree
        # with what was actually persisted.
        if added or replace:
            await session.flush()


evidence_service = EvidenceService()
