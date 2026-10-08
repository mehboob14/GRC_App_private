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
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from typing import Any, Final

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import InvalidInput, NotFound
from verity.core.storage import ObjectStore, get_object_store
from verity.modules.audit.service import Actor, AuditService, Membership, audit_service
from verity.modules.evidence.models import (
    DEFAULT_VALIDITY_DAYS,
    Evidence,
    EvidenceControl,
)
from verity.modules.evidence.text import extract_text
from verity.shared.ids import uuid7

#: Types evidence may be linked to. A subset of the links table's own
#: constraint - those whose module ships a detail view the resolver can read.
LINKABLE_TYPES: Final[frozenset[str]] = frozenset({"task", "document", "asset", "vulnerability"})

#: Stand-in until the resolver's result is paired with the edge it came from.
_UNSET_LINK_ID: Final = uuid.UUID(int=0)

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
    "review_status",
    "reviewed_by_membership_id",
    "review_note",
)


def freshness(
    renewal_date: date | None, *, collected_at: date | None = None, today: date | None = None
) -> str:
    """``current`` | ``aging`` | ``stale`` | ``no_expiry``.

    An item with no renewal date does not expire and is reported as such rather
    than quietly counted as current — "never expires" and "fine for now" are
    different claims to an auditor.

    Given when the item was collected, the aging warning is the last third of its
    life at most: a connector's result is valid for a week and replaced by the next
    run, so it must not read as aging the moment it is filed.
    """
    if renewal_date is None:
        return "no_expiry"
    now = today or datetime.now(UTC).date()
    if renewal_date < now:
        return "stale"
    window = AGING_WINDOW_DAYS
    if collected_at is not None:
        window = min(window, max((renewal_date - collected_at).days // 3, 0))
    if (renewal_date - now).days <= window:
        return "aging"
    return "current"


def default_renewal_date(evidence_type: str, collected_at: date) -> date | None:
    """The renewal date a type suggests. Only ever a pre-fill — the caller may
    override it, and the API lets them (D13)."""
    days = DEFAULT_VALIDITY_DAYS.get(evidence_type)
    return collected_at + timedelta(days=days) if days else None


@dataclass(frozen=True, slots=True)
class ControlLink:
    """A linked control as the evidence library shows it: the platform control
    code plus the criteria that control satisfies (framework prefix stripped)."""

    id: uuid.UUID
    code: str
    criteria: list[str] = field(default_factory=list)


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
    source: str | None
    link_url: str | None
    review_status: str
    #: Whether a reviewer's verdict is called for at all. Evidence proves a
    #: control; until one is linked there is nothing to review it against, so a
    #: bare upload is not "pending" anybody. Derived from the mappings, never
    #: stored - linking a control makes review due, unlinking the last one
    #: makes it moot, and neither should need a write.
    review_required: bool
    reviewed_by_membership_id: uuid.UUID | None
    reviewed_by_name: str | None
    reviewed_at: datetime | None
    review_note: str | None
    control_ids: list[uuid.UUID] = field(default_factory=list)
    control_codes: list[str] = field(default_factory=list)
    control_links: list[ControlLink] = field(default_factory=list)
    #: A connector files its result again on each run, so an item is history once a
    #: later one of the same series exists. History lapses on schedule and nobody
    #: renews it; it is not counted as stale or aging work. Only set by ``list_evidence``,
    #: which sees the whole series.
    superseded: bool = False


def series_of(source: str | None, external_id: str | None) -> str | None:
    """The series a connector's item belongs to, or None for any other item.

    A connector files under ``<series>:<digest>:<run>``: every item of one series is a
    revision of the same thing (one check on one connection), and the newest replaces
    the rest.
    """
    if source is None or external_id is None:
        return None
    parts = external_id.rsplit(":", 2)
    return parts[0] if len(parts) == 3 else None  # noqa: PLR2004 - series, digest, run


@dataclass(frozen=True, slots=True)
class SuggestionView:
    """One AI/heuristic-suggested control mapping — a draft a person approves."""

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
    #: "CC6.1: Logical access security" for each criterion the control answers.
    requirements: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class MaturityView:
    """A draft judgement of how well one item proves one control (rule 11)."""

    control_id: uuid.UUID
    code: str
    name: str
    maturity: int
    verdict: str
    summary: str
    strengths: list[str]
    gaps: list[str]
    requirements: list[dict[str, str]]


@dataclass(frozen=True, slots=True)
class LinkTarget:
    """What a link points at. One value rather than two loose arguments, so the
    pair cannot be passed in the wrong order."""

    type: str
    id: uuid.UUID


@dataclass(frozen=True, slots=True)
class LinkedRecordView:
    """A record this evidence is linked to, in one shape regardless of module.

    ``code`` is the human handle its own module uses (a task code, a document
    code, a CVE, an asset hostname) and is empty when that module has none;
    ``detail`` is the module's second fact - a task kind, a doc type, a severity.
    """

    link_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    code: str
    title: str
    status: str
    detail: str | None


@dataclass(frozen=True, slots=True)
class EvidenceBrief:
    """An evidence item as a record that carries it shows it: what it is and how fresh,
    without the control mappings, which cost a pass over the whole library to build."""

    id: uuid.UUID
    title: str
    evidence_type: str
    kind: str
    filename: str | None
    content_type: str | None
    size_bytes: int | None
    sha256: str | None
    link_url: str | None
    renewal_date: date | None
    freshness: str
    review_status: str


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
        # created_at breaks the tie: collected_at is a day, and several results from one
        # connection can land in it, so "newest first" needs a second key to be true.
        rows = list(
            (
                await session.execute(
                    statement.order_by(Evidence.collected_at.desc(), Evidence.created_at.desc())
                )
            ).scalars()
        )
        mappings = await self._mappings(session, tenant_id)
        owners = await self._owner_names(session, tenant_id)
        # The rows come newest first, so the first of a series is the one that stands.
        newest: dict[str, uuid.UUID] = {}
        for row in rows:
            series = series_of(row.source, row.external_id)
            if series is not None:
                newest.setdefault(series, row.id)
        views = [
            replace(
                self._view(row, mappings, owners),
                superseded=(
                    (series := series_of(row.source, row.external_id)) is not None
                    and newest[series] != row.id
                ),
            )
            for row in rows
        ]
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
            raise InvalidInput(
                "This evidence item is a link, so there is no file to download. "
                "Open the link instead.",
                detail="this evidence item is a link, not a stored file",
            )
        data = self._store.open(tenant_id, row.object_key)
        return (
            data,
            row.filename or "evidence",
            row.content_type or "application/octet-stream",
        )

    async def collected_dates(self, session: AsyncSession, tenant_id: uuid.UUID) -> list[date]:
        """Every evidence item's collection date, oldest first.

        Exists so the compliance dashboard can draw "evidence collected over
        time" without reading this module's tables. Dates only — the caller
        buckets them into a cumulative line and needs nothing else.
        """
        rows = await session.execute(
            select(Evidence.collected_at)
            .where(Evidence.tenant_id == tenant_id)
            .order_by(Evidence.collected_at.asc())
        )
        return list(rows.scalars())

    async def evidence_ids_for_control(
        self, session: AsyncSession, tenant_id: uuid.UUID, control_id: uuid.UUID
    ) -> list[uuid.UUID]:
        """The evidence linked to one control. For the control editor's prefill
        and its before/after audit snapshot; compliance asks through here, never
        the table (rule 4)."""
        rows = await session.execute(
            select(EvidenceControl.evidence_id).where(
                EvidenceControl.tenant_id == tenant_id,
                EvidenceControl.control_id == control_id,
            )
        )
        return list(rows.scalars())

    async def control_ids_for_evidence(
        self, session: AsyncSession, tenant_id: uuid.UUID, evidence_id: uuid.UUID
    ) -> list[uuid.UUID]:
        """The controls one evidence item supports, for the 360 trace. The other end
        of ``evidence_ids_for_control``."""
        rows = await session.execute(
            select(EvidenceControl.control_id)
            .where(
                EvidenceControl.tenant_id == tenant_id,
                EvidenceControl.evidence_id == evidence_id,
            )
            .order_by(EvidenceControl.created_at, EvidenceControl.id)
        )
        return list(rows.scalars())

    async def label(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, evidence_id: uuid.UUID
    ) -> tuple[str, str, str] | None:
        """``(title, freshness, evidence_type)`` of one item, or None when it is gone.
        One row, for a page that names many items and needs nothing else: ``get`` also
        reads every mapping in the library and every member's name."""
        row = (
            await session.execute(
                select(
                    Evidence.title,
                    Evidence.renewal_date,
                    Evidence.collected_at,
                    Evidence.evidence_type,
                ).where(Evidence.tenant_id == tenant_id, Evidence.id == evidence_id)
            )
        ).first()
        if row is None:
            return None
        state = freshness(row.renewal_date, collected_at=row.collected_at)
        return (row.title, state, row.evidence_type)

    async def set_control_evidence(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        control_id: uuid.UUID,
        evidence_ids: Sequence[uuid.UUID],
    ) -> None:
        """Replace the evidence links for one control with ``evidence_ids``.

        The reverse of attaching controls to an evidence item — used by the
        control editor. Rows this module owns; compliance drives it through this
        service (rule 4). The parent control's audit records the before/after
        id sets, so this method does not write its own trail.
        """
        target = set(evidence_ids)
        existing = set(await self.evidence_ids_for_control(session, tenant_id, control_id))
        for evidence_id in existing - target:
            await session.execute(
                delete(EvidenceControl).where(
                    EvidenceControl.tenant_id == tenant_id,
                    EvidenceControl.control_id == control_id,
                    EvidenceControl.evidence_id == evidence_id,
                )
            )
        for evidence_id in target - existing:
            session.add(
                EvidenceControl(
                    id=uuid7(),
                    tenant_id=tenant_id,
                    evidence_id=evidence_id,
                    control_id=control_id,
                )
            )
        await session.flush()

    async def evidence_counts_by_control(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, int]:
        """How many evidence items each control carries, in one query.

        For the gap-assessment report, which shows a count per control. Reads
        this module's own join table; the compliance report asks through the
        service, never the table (rule 4).
        """
        rows = await session.execute(
            select(EvidenceControl.control_id).where(EvidenceControl.tenant_id == tenant_id)
        )
        counts: dict[uuid.UUID, int] = {}
        for (control_id,) in rows:
            counts[control_id] = counts.get(control_id, 0) + 1
        return counts

    async def control_ids_with_evidence(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> set[uuid.UUID]:
        """Which controls have at least one evidence item linked to them.

        Exists so compliance's coverage report can answer "controls with no
        evidence" without reading this module's tables, which rule 4 forbids.
        Ids only: the caller already holds the controls and needs nothing else
        from evidence, so this stays a set membership test rather than a join
        that would drag evidence rows across the module boundary.
        """
        rows = await session.execute(
            select(EvidenceControl.control_id)
            .where(EvidenceControl.tenant_id == tenant_id)
            .distinct()
        )
        return set(rows.scalars())

    async def control_ids_with_current_evidence(
        self, session: AsyncSession, tenant_id: uuid.UUID, *, today: date | None = None
    ) -> set[uuid.UUID]:
        """Which controls have evidence that still counts as evidence.

        ``control_ids_with_evidence`` answers "is anything attached", which is the
        right question for the gap list. Readiness asks a harder one: a rejected
        item was reviewed and found wanting, and one past its renewal date proves
        the control worked once, not that it works now. Neither makes a control
        ready, so neither is counted here.
        """
        now = today or datetime.now(UTC).date()
        rows = await session.execute(
            select(EvidenceControl.control_id)
            .join(Evidence, Evidence.id == EvidenceControl.evidence_id)
            .where(
                EvidenceControl.tenant_id == tenant_id,
                Evidence.review_status != "rejected",
                or_(Evidence.renewal_date.is_(None), Evidence.renewal_date >= now),
            )
            .distinct()
        )
        return set(rows.scalars())

    async def _mappings(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, list[ControlLink]]:
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
        link_by_id = {
            control.id: ControlLink(
                id=control.id,
                code=control.code,
                criteria=sorted({key.split(":", 1)[-1] for key in control.requirement_keys}),
            )
            for control in controls
        }
        out: dict[uuid.UUID, list[ControlLink]] = {}
        for evidence_id, control_id in pairs:
            link = link_by_id.get(control_id) or ControlLink(id=control_id, code="?")
            out.setdefault(evidence_id, []).append(link)
        for mapped in out.values():
            mapped.sort(key=lambda link: link.code)
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
        mappings: dict[uuid.UUID, list[ControlLink]],
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
            freshness=freshness(row.renewal_date, collected_at=row.collected_at),
            filename=row.filename,
            content_type=row.content_type,
            size_bytes=row.size_bytes,
            sha256=row.sha256,
            link_url=row.link_url,
            source=row.source,
            review_status=row.review_status,
            review_required=bool(mapped),
            reviewed_by_membership_id=row.reviewed_by_membership_id,
            reviewed_by_name=(
                owners.get(row.reviewed_by_membership_id) if row.reviewed_by_membership_id else None
            ),
            reviewed_at=row.reviewed_at,
            review_note=row.review_note,
            control_ids=[link.id for link in mapped],
            control_codes=[link.code for link in mapped],
            control_links=list(mapped),
        )

    async def _has_control_links(
        self, session: AsyncSession, tenant_id: uuid.UUID, evidence_id: uuid.UUID
    ) -> bool:
        """Whether this evidence is mapped to any control."""
        found = await session.scalar(
            select(EvidenceControl.control_id)
            .where(
                EvidenceControl.tenant_id == tenant_id,
                EvidenceControl.evidence_id == evidence_id,
            )
            .limit(1)
        )
        return found is not None

    async def _load(
        self, session: AsyncSession, tenant_id: uuid.UUID, evidence_id: uuid.UUID
    ) -> Evidence:
        row = await session.get(Evidence, evidence_id)
        if row is None or row.tenant_id != tenant_id:
            raise NotFound(
                "This evidence item no longer exists. It may have been deleted.",
                detail=f"evidence {evidence_id}",
            )
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
        source: str | None = None,
        external_id: str | None = None,
        synced_at: datetime | None = None,
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
            # Rule 9: what a connector filed says which one, and under what id.
            source=source,
            external_id=external_id,
            synced_at=synced_at,
        )
        return await self._insert(session, row, actor, tenant_id, control_ids or [])

    async def latest_synced(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        source: str,
        external_id_prefix: str,
    ) -> tuple[str, datetime] | None:
        """The newest item a connector filed under an id prefix: its id and when.

        A connector asks this to decide whether what it just read is worth a new file,
        so it never reads the evidence table itself.
        """
        row = (
            await session.execute(
                select(Evidence.external_id, Evidence.synced_at)
                .where(
                    Evidence.tenant_id == tenant_id,
                    Evidence.source == source,
                    Evidence.external_id.startswith(external_id_prefix, autoescape=True),
                    Evidence.synced_at.is_not(None),
                )
                .order_by(Evidence.synced_at.desc())
                .limit(1)
            )
        ).first()
        if row is None or row.external_id is None or row.synced_at is None:
            return None
        return row.external_id, row.synced_at

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
            raise InvalidInput(
                "Enter a web address that starts with http:// or https://.",
                detail="a link must be an http or https URL",
            )
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
            session,
            tenant_id=tenant_id,
            evidence_id=row.id,
            control_ids=control_ids,
            actor=actor,
            title=row.title,
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
                actor=actor,
                title=row.title,
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

    async def review(  # noqa: PLR0913 — reviewer + decision + note + audit actor
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        evidence_id: uuid.UUID,
        reviewer_membership_id: uuid.UUID,
        decision: str,
        note: str | None = None,
    ) -> EvidenceView:
        """Record a reviewer's verdict on one item.

        ``decision`` is ``approved`` or ``rejected`` — ``pending`` is a starting
        state, not something a person chooses. A rejection must say why, so the
        owner knows what to fix; the note is optional on an approval. The verdict
        is audited with before/after, so who signed off (or refused) and when is
        part of the tenant's record.
        """
        if decision not in ("approved", "rejected"):
            raise InvalidInput(
                "Choose either approve or reject to record your review.",
                detail="a review decision is 'approved' or 'rejected'",
            )
        cleaned = (note or "").strip()
        if decision == "rejected" and not cleaned:
            raise InvalidInput(
                "Add a reason when you reject evidence, so the owner knows what to fix.",
                detail="a rejection must include a reason",
            )

        row = await self._load(session, tenant_id, evidence_id)
        # Reviewing evidence that supports no control approves it against
        # nothing. The reviewer signs off that it proves a control, so a control
        # has to be linked first.
        if not await self._has_control_links(session, tenant_id, evidence_id):
            raise InvalidInput(
                "Link this evidence to a control before reviewing it.",
                detail="review requires at least one control mapping",
            )
        before = AuditService.snapshot(row, fields=_SNAPSHOT)
        row.review_status = decision
        row.reviewed_by_membership_id = reviewer_membership_id
        row.reviewed_at = datetime.now(UTC)
        row.review_note = cleaned or None

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

    async def map_controls(  # noqa: PLR0913 — actor is required to audit the link
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        evidence_id: uuid.UUID,
        control_ids: list[uuid.UUID],
        replace: bool = False,
        actor: Actor | None = None,
        title: str | None = None,
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
        detached: list[uuid.UUID] = []
        if replace:
            for control_id, row in rows.items():
                if control_id not in control_ids:
                    await session.delete(row)
                    detached.append(control_id)
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

        # One audit row per control touched, written against the CONTROL so it
        # surfaces in that control's history. The evidence item has its own row
        # already; this is the other side of the same fact.
        if actor is not None:
            for row in added:
                await self._audit.record(
                    session,
                    action="update",
                    object_type="control",
                    object_id=row.control_id,
                    actor=actor,
                    tenant_id=tenant_id,
                    before=None,
                    after={"evidence_linked": title or str(evidence_id)},
                )
            for control_id in detached:
                await self._audit.record(
                    session,
                    action="update",
                    object_type="control",
                    object_id=control_id,
                    actor=actor,
                    tenant_id=tenant_id,
                    before={"evidence_linked": title or str(evidence_id)},
                    after=None,
                )

    async def suggest_mappings(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, evidence_id: uuid.UUID
    ) -> tuple[str, list[SuggestionView]]:
        """Rank the controls this evidence likely supports (draft, rule 11). Excludes
        controls already linked. Returns ``(source, suggestions)`` where source is
        ``"ai"`` or ``"heuristic"``."""
        from verity.modules.ai.mapping import (  # noqa: PLC0415 — keeps the LLM path optional
            ControlCandidate,
            EvidenceContext,
            suggest_mappings,
        )
        from verity.modules.compliance.control_service import control_service  # noqa: PLC0415

        row = await self._load(session, tenant_id, evidence_id)
        linked = set(
            (
                await session.execute(
                    select(EvidenceControl.control_id).where(
                        EvidenceControl.tenant_id == tenant_id,
                        EvidenceControl.evidence_id == evidence_id,
                    )
                )
            ).scalars()
        )
        controls = await control_service.list_controls(session, tenant_id=tenant_id)
        by_id = {str(c.id): c for c in controls}
        texts = await control_service.requirement_texts(
            session, keys=sorted({k for c in controls for k in c.requirement_keys})
        )

        def cited(c: Any) -> list[str]:  # noqa: ANN401 — a control view
            return [
                f"{k.split(':', 1)[-1]}: {texts[k][0]}" for k in c.requirement_keys if k in texts
            ]

        candidates = [
            ControlCandidate(
                control_id=str(c.id),
                code=c.code,
                name=c.name,
                description=c.description or "",
                criteria=[k.split(":", 1)[-1] for k in c.requirement_keys],
                requirements=cited(c),
            )
            for c in controls
            if c.id not in linked
        ]
        suggestions, source = await suggest_mappings(
            EvidenceContext(
                title=row.title,
                description=row.description or "",
                evidence_type=row.evidence_type,
                text=await self._text_of(tenant_id, row),
            ),
            candidates,
        )
        views = [
            SuggestionView(
                control_id=uuid.UUID(s.control_id),
                code=by_id[s.control_id].code,
                name=by_id[s.control_id].name,
                criteria=[k.split(":", 1)[-1] for k in by_id[s.control_id].requirement_keys],
                coverage=s.coverage,
                confidence=s.confidence,
                rationale=s.rationale,
                maturity=s.maturity,
                verdict=s.verdict,
                gaps=s.gaps,
                requirements=cited(by_id[s.control_id]),
            )
            for s in suggestions
            if s.control_id in by_id
        ]
        return source, views

    async def _text_of(self, tenant_id: uuid.UUID, row: Evidence) -> str:
        if row.kind != "file" or row.object_key is None:
            return ""
        try:
            data = self._store.open(tenant_id, row.object_key)
        except Exception:
            return ""
        return extract_text(data, row.content_type or "", row.filename or "")

    async def assess_maturity(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        evidence_id: uuid.UUID,
        control_id: uuid.UUID,
    ) -> MaturityView | None:
        """Judge this item against one control and the requirements it answers: a draft
        for a person (rule 11). None when no model is configured or it could not decide."""
        from verity.modules.ai.mapping import (  # noqa: PLC0415 — keeps the LLM path optional
            ControlCandidate,
            EvidenceContext,
            assess_maturity,
        )
        from verity.modules.compliance.control_service import control_service  # noqa: PLC0415

        row = await self._load(session, tenant_id, evidence_id)
        controls = await control_service.list_controls(session, tenant_id=tenant_id)
        control = next((c for c in controls if c.id == control_id), None)
        if control is None:
            raise NotFound("That control does not exist.", detail=str(control_id))
        texts = await control_service.requirement_texts(session, keys=control.requirement_keys)
        result = await assess_maturity(
            EvidenceContext(
                title=row.title,
                description=row.description or "",
                evidence_type=row.evidence_type,
                text=await self._text_of(tenant_id, row),
            ),
            ControlCandidate(
                control_id=str(control.id),
                code=control.code,
                name=control.name,
                description=control.description or "",
                criteria=[k.split(":", 1)[-1] for k in control.requirement_keys],
                requirements=[
                    f"{k.split(':', 1)[-1]}: {texts[k][0]}. {texts[k][1][:300]}"
                    for k in control.requirement_keys
                    if k in texts
                ],
            ),
        )
        if result is None:
            return None
        return MaturityView(
            control_id=control.id,
            code=control.code,
            name=control.name,
            maturity=result.maturity,
            verdict=result.verdict,
            summary=result.summary,
            strengths=result.strengths,
            gaps=result.gaps,
            requirements=result.requirements,
        )

    async def approve_mapping(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        evidence_id: uuid.UUID,
        control_id: uuid.UUID,
    ) -> EvidenceView:
        """Link one suggested control (a person's decision, rule 11). Merges rather
        than replaces, so approving several suggestions never drops the others, and
        the link is audited on the control's history like any manual mapping."""
        row = await self._load(session, tenant_id, evidence_id)
        await self.map_controls(
            session,
            tenant_id=tenant_id,
            evidence_id=evidence_id,
            control_ids=[control_id],
            replace=False,
            actor=actor,
            title=row.title,
        )
        return await self.get(session, tenant_id=tenant_id, evidence_id=evidence_id)

    # -- cross-module links ---------------------------------------------------
    #
    # One trio serves every linkable module. Each target type contributes a
    # resolver that turns its own detail view into the common shape, so titles
    # and status stay their module's business (rule 4: service -> service, never
    # into another module's repository).

    async def _resolve_link_target(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        target_type: str,
        target_id: uuid.UUID,
    ) -> LinkedRecordView | None:
        """The linked record as a common view, or None if it is gone or out of
        scope - a dangling edge is skipped, never raised."""
        from verity.modules.assets.service import asset_service  # noqa: PLC0415
        from verity.modules.documents.service import document_service  # noqa: PLC0415
        from verity.modules.tasks.service import task_service  # noqa: PLC0415
        from verity.modules.vulnerabilities.service import (  # noqa: PLC0415
            vulnerability_service,
        )

        try:
            if target_type == "task":
                task = await task_service.get_task(session, tenant_id=tenant_id, task_id=target_id)
                return LinkedRecordView(
                    link_id=_UNSET_LINK_ID,
                    target_type="task",
                    target_id=task.id,
                    code=task.code,
                    title=task.title,
                    status=task.status,
                    detail=task.task_kind,
                )
            if target_type == "document":
                doc = await document_service.get_document(
                    session, tenant_id=tenant_id, document_id=target_id
                )
                return LinkedRecordView(
                    link_id=_UNSET_LINK_ID,
                    target_type="document",
                    target_id=doc.id,
                    code=doc.code,
                    title=doc.title,
                    status=doc.lifecycle,
                    detail=doc.doc_type,
                )
            if target_type == "asset":
                asset = await asset_service.get_asset(
                    session, tenant_id=tenant_id, asset_id=target_id
                )
                return LinkedRecordView(
                    link_id=_UNSET_LINK_ID,
                    target_type="asset",
                    target_id=asset.id,
                    code=asset.hostname or "",
                    title=asset.name,
                    status=asset.status,
                    detail=asset.asset_type,
                )
            if target_type == "vulnerability":
                vuln = await vulnerability_service.get_instance(
                    session, tenant_id=tenant_id, instance_id=target_id
                )
                return LinkedRecordView(
                    link_id=_UNSET_LINK_ID,
                    target_type="vulnerability",
                    target_id=vuln.id,
                    code=vuln.cve_id or "",
                    title=vuln.title,
                    status=vuln.state,
                    detail=vuln.severity,
                )
        except NotFound:
            return None
        return None

    async def linked_records(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        evidence_id: uuid.UUID,
        target_type: str | None = None,
    ) -> list[LinkedRecordView]:
        """Every record this evidence is linked to, optionally of one type."""
        from verity.modules.links.service import link_service  # noqa: PLC0415

        edges = await link_service.for_object(
            session, tenant_id=tenant_id, obj_type="evidence", obj_id=evidence_id
        )
        out: list[LinkedRecordView] = []
        for edge in edges:
            if target_type is not None and edge.other_type != target_type:
                continue
            view = await self._resolve_link_target(
                session, tenant_id, edge.other_type, edge.other_id
            )
            if view is None:
                continue  # target removed or out of scope; skip the dangling edge
            out.append(replace(view, link_id=edge.link_id))
        out.sort(key=lambda r: (r.target_type, r.code, r.title))
        return out

    async def link_record(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        evidence_id: uuid.UUID,
        target: LinkTarget,
    ) -> list[LinkedRecordView]:
        """Link this evidence to another record (idempotent). Audited on the
        evidence, in the same transaction as the link (rule 5)."""
        from verity.modules.links.service import link_service  # noqa: PLC0415

        target_type, target_id = target.type, target.id
        if target_type not in LINKABLE_TYPES:
            raise InvalidInput(
                "evidence.link_type_unsupported",
                detail=f"{target_type!r} is not a type evidence can be linked to",
            )
        await self._load(session, tenant_id, evidence_id)  # 404 if the evidence is gone
        # Resolve before writing: a link to a record that does not exist is a
        # dangling edge nothing will ever render, and the caller deserves a 404
        # rather than a silent success.
        if await self._resolve_link_target(session, tenant_id, target_type, target_id) is None:
            raise NotFound("evidence.link_target_missing", detail=f"{target_type} {target_id}")
        member = actor.id if isinstance(actor, Membership) else None
        await link_service.create(
            session,
            tenant_id=tenant_id,
            from_type="evidence",
            from_id=evidence_id,
            to_type=target_type,
            to_id=target_id,
            created_by_membership_id=member,
        )
        await self._audit.record(
            session,
            action="update",
            object_type="evidence",
            object_id=evidence_id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after={"linked": f"{target_type}:{target_id}"},
        )
        return await self.linked_records(session, tenant_id=tenant_id, evidence_id=evidence_id)

    async def unlink_record(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        evidence_id: uuid.UUID,
        link_id: uuid.UUID,
    ) -> list[LinkedRecordView]:
        from verity.modules.links.service import link_service  # noqa: PLC0415

        await self._load(session, tenant_id, evidence_id)
        await link_service.delete(session, tenant_id=tenant_id, link_id=link_id)
        await self._audit.record(
            session,
            action="update",
            object_type="evidence",
            object_id=evidence_id,
            actor=actor,
            tenant_id=tenant_id,
            before={"unlinked_link_id": str(link_id)},
            after=None,
        )
        return await self.linked_records(session, tenant_id=tenant_id, evidence_id=evidence_id)

    # -- tasks that carry evidence ---------------------------------------------
    #
    # A task attaches evidence through the same edge ``link_record`` draws from the
    # evidence page (evidence to task), so an item attached from either end reads from
    # both. These two are the task side's reads and writes of that pair: they skip what
    # ``link_record`` does for a page of links (resolving every record the evidence
    # touches), which a task attaching several items in one call cannot afford.

    async def briefs_for_task(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, task_id: uuid.UUID
    ) -> list[EvidenceBrief]:
        """The evidence linked to one task, most recently collected first."""
        from verity.modules.links.service import link_service  # noqa: PLC0415

        edges = await link_service.for_object(
            session, tenant_id=tenant_id, obj_type="task", obj_id=task_id
        )
        ids = list(dict.fromkeys(e.other_id for e in edges if e.other_type == "evidence"))
        if not ids:
            return []
        rows = (
            await session.execute(
                select(Evidence)
                .where(Evidence.tenant_id == tenant_id, Evidence.id.in_(ids))
                .order_by(Evidence.collected_at.desc(), Evidence.created_at.desc())
            )
        ).scalars()
        return [
            EvidenceBrief(
                id=row.id,
                title=row.title,
                evidence_type=row.evidence_type,
                kind=row.kind,
                filename=row.filename,
                content_type=row.content_type,
                size_bytes=row.size_bytes,
                sha256=row.sha256,
                link_url=row.link_url,
                renewal_date=row.renewal_date,
                freshness=freshness(row.renewal_date, collected_at=row.collected_at),
                review_status=row.review_status,
            )
            for row in rows
        ]

    async def link_to_task(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        evidence_id: uuid.UUID,
        task_id: uuid.UUID,
    ) -> None:
        """Link an evidence item to a task the caller has already resolved. Idempotent;
        audited on the evidence in the caller's transaction, like ``link_record`` (rule 5)."""
        from verity.modules.links.service import link_service  # noqa: PLC0415

        await self._load(session, tenant_id, evidence_id)  # 404 if the evidence is gone
        await link_service.create(
            session,
            tenant_id=tenant_id,
            from_type="evidence",
            from_id=evidence_id,
            to_type="task",
            to_id=task_id,
            created_by_membership_id=actor.id if isinstance(actor, Membership) else None,
        )
        await self._audit.record(
            session,
            action="update",
            object_type="evidence",
            object_id=evidence_id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after={"linked": f"task:{task_id}"},
        )


evidence_service = EvidenceService()
