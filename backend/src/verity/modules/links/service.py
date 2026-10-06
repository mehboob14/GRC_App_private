"""Generic linkage service (ADR-0003).

Storage only. Creating a link is not, by itself, an audited domain event — the
module that draws the link records that in its own history (a task's transition
log, say), so this service stays decoupled from ``audit`` and from every domain.

It returns domain dataclasses, never ORM rows, so a caller imports
``links.service`` and never ``links.models`` — which is what keeps the module
boundary (and the import-linter) satisfied.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import InvalidInput, NotFound
from verity.modules.links.models import LINK_RELATIONS, LINK_TYPES, Link
from verity.shared.ids import uuid7


@dataclass(frozen=True, slots=True)
class LinkedObject:
    """One end of a link, seen from a given object. ``direction`` says which side
    the queried object sat on, so the caller can render "remediates X" vs
    "remediated by Y" correctly."""

    link_id: uuid.UUID
    other_type: str
    other_id: uuid.UUID
    relation: str
    note: str | None
    direction: str  # "outgoing" (queried object is the `from`) | "incoming"
    # When the edge was drawn and by whom, for the trace view. Defaulted so a
    # caller that builds one by hand does not have to know them.
    created_at: datetime | None = None
    created_by_membership_id: uuid.UUID | None = None


_UNKNOWN_TYPE_MESSAGE = (
    "That is not something you can link here. Choose one of the item types offered."
)


def _validate(from_type: str, to_type: str, relation: str) -> None:
    if from_type not in LINK_TYPES:
        raise InvalidInput(_UNKNOWN_TYPE_MESSAGE, detail=f"unknown link type {from_type!r}")
    if to_type not in LINK_TYPES:
        raise InvalidInput(_UNKNOWN_TYPE_MESSAGE, detail=f"unknown link type {to_type!r}")
    if relation not in LINK_RELATIONS:
        raise InvalidInput(
            "That is not a relationship you can use for a link. Choose one from the list.",
            detail=f"unknown relation {relation!r}",
        )


class LinkService:
    async def create(  # noqa: PLR0913 — a link genuinely has this many parts
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        from_type: str,
        from_id: uuid.UUID,
        to_type: str,
        to_id: uuid.UUID,
        relation: str = "relates_to",
        note: str | None = None,
        created_by_membership_id: uuid.UUID | None = None,
    ) -> uuid.UUID:
        """Create the edge, or return the existing one — linking is idempotent."""
        _validate(from_type, to_type, relation)
        if from_type == to_type and from_id == to_id:
            raise InvalidInput(
                "You cannot link an item to itself. Choose a different item.",
                detail="an object cannot be linked to itself",
            )

        existing = (
            await session.execute(
                select(Link.id).where(
                    Link.tenant_id == tenant_id,
                    Link.from_type == from_type,
                    Link.from_id == from_id,
                    Link.to_type == to_type,
                    Link.to_id == to_id,
                    Link.relation == relation,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

        link = Link(
            id=uuid7(),
            tenant_id=tenant_id,
            from_type=from_type,
            from_id=from_id,
            to_type=to_type,
            to_id=to_id,
            relation=relation,
            note=note,
            created_by_membership_id=created_by_membership_id,
        )
        session.add(link)
        await session.flush([link])
        return link.id

    async def delete(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, link_id: uuid.UUID
    ) -> None:
        # RETURNING tells us whether a row actually matched, without a second query
        # and without reaching for CursorResult.rowcount (untyped under RLS).
        deleted = (
            await session.execute(
                delete(Link)
                .where(Link.tenant_id == tenant_id, Link.id == link_id)
                .returning(Link.id)
            )
        ).scalar_one_or_none()
        if deleted is None:
            raise NotFound(
                "This link no longer exists. It may have been removed already.",
                detail=f"link {link_id}",
            )

    async def for_object(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        obj_type: str,
        obj_id: uuid.UUID,
    ) -> list[LinkedObject]:
        """Every link touching this object, from either end, normalised so the
        caller sees the *other* end and which direction it points."""
        rows = (
            await session.execute(
                select(Link).where(
                    Link.tenant_id == tenant_id,
                    or_(
                        (Link.from_type == obj_type) & (Link.from_id == obj_id),
                        (Link.to_type == obj_type) & (Link.to_id == obj_id),
                    ),
                )
            )
        ).scalars()
        out: list[LinkedObject] = []
        for link in rows:
            outgoing = link.from_type == obj_type and link.from_id == obj_id
            out.append(
                LinkedObject(
                    link_id=link.id,
                    other_type=link.to_type if outgoing else link.from_type,
                    other_id=link.to_id if outgoing else link.from_id,
                    relation=link.relation,
                    note=link.note,
                    direction="outgoing" if outgoing else "incoming",
                    created_at=link.created_at,
                    created_by_membership_id=link.created_by_membership_id,
                )
            )
        return out

    async def ids_of_type_linked_from(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        from_type: str,
        from_ids: Sequence[uuid.UUID],
        to_type: str,
    ) -> dict[uuid.UUID, list[uuid.UUID]]:
        """Bulk helper: for many source objects at once, the ids of a given target
        type each links to. Used to badge a list without an N+1."""
        if not from_ids:
            return {}
        rows = await session.execute(
            select(Link.from_id, Link.to_id).where(
                Link.tenant_id == tenant_id,
                Link.from_type == from_type,
                Link.from_id.in_(list(from_ids)),
                Link.to_type == to_type,
            )
        )
        out: dict[uuid.UUID, list[uuid.UUID]] = {}
        for from_id, to_id in rows:
            out.setdefault(from_id, []).append(to_id)
        return out

    async def counts_into(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        to_type: str,
        to_ids: Sequence[uuid.UUID],
        from_type: str,
    ) -> dict[uuid.UUID, int]:
        """The other direction of ``ids_of_type_linked_from``: for many target objects at
        once, how many edges of ``from_type`` point at each. Badges a list in one query."""
        if not to_ids:
            return {}
        rows = await session.execute(
            select(Link.to_id, func.count())
            .where(
                Link.tenant_id == tenant_id,
                Link.to_type == to_type,
                Link.to_id.in_(list(to_ids)),
                Link.from_type == from_type,
            )
            .group_by(Link.to_id)
        )
        return {to_id: n for to_id, n in rows}  # noqa: C416 — dict(rows) is rejected by mypy


link_service = LinkService()
"""Module-level singleton, imported by other modules' services."""
