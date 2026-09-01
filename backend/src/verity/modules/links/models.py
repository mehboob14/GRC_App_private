"""The ``links`` table (ADR-0003).

A link stores only the *identity* of each end — a type and an id. The label a
person reads ("CC6.1 · Logical access controls") is resolved at read time by the
module that owns the object, never stored here, so renaming that object cannot
leave a stale label behind.

Indexed in both directions: a lookup from either end is a single tenant-scoped
index scan. The ``(tenant_id, from, to, relation)`` uniqueness makes linking
idempotent — the same edge added twice is one row.
"""

from __future__ import annotations

import uuid
from typing import Final

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from verity.db.base import (
    Base,
    TenantScoped,
    Timestamped,
    UUIDPrimaryKey,
    status_check,
    tenant_index,
)

# The object types a link may point at. A new module adds itself here (and to the
# check constraint, in a migration); a typo is then a constraint violation rather
# than a link nothing can reach.
LINK_TYPES: Final[tuple[str, ...]] = (
    "task",
    "control",
    "evidence",
    "risk",
    "document",
    "vendor",
    "asset",
    "vulnerability",
    "incident",
)

# The relationship an edge expresses. Deliberately small and generic: a hot,
# meaningful pair earns its own explicit join table (ADR-0003), so this stays a
# loose association vocabulary rather than growing into one.
LINK_RELATIONS: Final[tuple[str, ...]] = (
    "relates_to",
    "remediates",
    "caused_by",
    "depends_on",
    "duplicates",
)


class Link(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A directed association between two tenant-owned objects."""

    __tablename__ = "links"

    from_type: Mapped[str]
    from_id: Mapped[uuid.UUID]
    to_type: Mapped[str]
    to_id: Mapped[uuid.UUID]
    relation: Mapped[str] = mapped_column(default="relates_to")
    note: Mapped[str | None] = mapped_column(default=None)

    # Who drew the link — a membership, never a global user (rule 3).
    created_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )

    __table_args__ = (
        status_check("links", "from_type", LINK_TYPES),
        status_check("links", "to_type", LINK_TYPES),
        status_check("links", "relation", LINK_RELATIONS),
        UniqueConstraint(
            "tenant_id",
            "from_type",
            "from_id",
            "to_type",
            "to_id",
            "relation",
            name="uq_links__pair",
        ),
        tenant_index("links", "from_type", "from_id"),
        tenant_index("links", "to_type", "to_id"),
    )

    def __repr__(self) -> str:
        return (
            f"Link(id={self.id!r}, {self.from_type}:{self.from_id} "
            f"-{self.relation}-> {self.to_type}:{self.to_id})"
        )
