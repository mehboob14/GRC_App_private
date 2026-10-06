"""The walk behind the trace view: breadth first from one record over every edge.

Pure, so its rules are tested without a database. It takes two async callables, one
that lists the edges of a record and one that labels a record; the service wires them
to the links table and to the modules that own the pairs with a table of their own.

* Breadth first, so a record that can be reached two ways appears once, under its
  shortest path.
* At most ``NEIGHBOURS_PER_TYPE`` records of one type under one record and ``MAX_NODES``
  in all. ``truncated`` says a cap left something out, so a short tree is never a
  silent one.
* A type the caller may not read is never opened, so nothing behind it is reached
  either. It is named in ``hidden_types`` instead.

The caps are read as module globals at call time, which is what lets a test lower them.
"""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Awaitable, Callable, Container, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Final

MAX_DEPTH: Final = 4
"""How many hops the walk goes. The signed exit criterion is four: vulnerability, asset,
risk, control, policy."""

NEIGHBOURS_PER_TYPE: Final = 25
"""Records of one type listed under one record. More than this is a list, not a trace."""

MAX_NODES: Final = 150
"""Records in a whole trace, however many hops."""

TYPE_ORDER: Final[tuple[str, ...]] = (
    "control",
    "risk",
    "document",
    "evidence",
    "asset",
    "vulnerability",
    "vendor",
    "task",
)
"""The order the children of one record read in: what governs it first (controls, risks,
policies, evidence), then what it covers (assets, findings), then the rest."""

# What a generic link's relation reads as from its other end. A link is stored once, as
# "from relation to"; the record it is read from decides which way the words face.
_REVERSE_RELATION: Final[dict[str, str]] = {
    "relates_to": "relates_to",
    "remediates": "remediated_by",
    "caused_by": "cause_of",
    "depends_on": "depended_on_by",
    "duplicates": "duplicated_by",
}
_PHRASES: Final[dict[str, str]] = {"relates_to": "Related to"}


def relation_key(stored: str, direction: str) -> str:
    """A link's relation as the record it is read from would say it: a remediation read
    from the remediated record is ``remediated_by``."""
    return stored if direction == "outgoing" else _REVERSE_RELATION.get(stored, stored)


def phrase(key: str) -> str:
    """A relation key as the words a person reads: ``mitigated_by`` is "Mitigated by"."""
    return _PHRASES.get(key) or key.replace("_", " ").capitalize()


@dataclass(frozen=True, slots=True)
class Ref:
    """Which record: a type and an id, the pair every link stores."""

    type: str
    id: uuid.UUID

    @property
    def key(self) -> str:
        return f"{self.type}:{self.id}"


@dataclass(frozen=True, slots=True)
class Candidate:
    """One edge, seen from the record being opened. ``relation`` is a key, and
    ``direction`` says whether the edge was drawn from that record or towards it."""

    ref: Ref
    relation: str
    direction: str
    linked_at: datetime | None = None
    linked_by_id: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class Label:
    """What a person reads about a record, as its own module words it."""

    code: str
    title: str
    status: str
    detail: str | None


@dataclass(frozen=True, slots=True)
class TraceNode:
    type: str
    id: uuid.UUID
    code: str
    title: str
    status: str
    detail: str | None
    depth: int
    parent_key: str | None = None
    relation: str | None = None
    direction: str | None = None
    linked_at: datetime | None = None
    linked_by_id: uuid.UUID | None = None
    linked_by: str | None = None
    """The person's name; the service fills it in from ``linked_by_id``."""

    @property
    def ref(self) -> Ref:
        return Ref(self.type, self.id)

    @property
    def key(self) -> str:
        return f"{self.type}:{self.id}"


@dataclass(frozen=True, slots=True)
class Trace:
    start: TraceNode
    nodes: list[TraceNode]
    """Every record reached, nearest first, each once, under its shortest path."""

    depth: int
    truncated: bool
    hidden_types: list[str]
    neighbour_limit: int
    node_limit: int


EdgesOf = Callable[[Ref], Awaitable[Sequence[Candidate]]]
LabelOf = Callable[[Ref], Awaitable[Label | None]]


def _rank(node_type: str) -> int:
    return TYPE_ORDER.index(node_type) if node_type in TYPE_ORDER else len(TYPE_ORDER)


async def walk(  # noqa: PLR0913 — the start, its two readers, the caller's reach and the depth
    start: Ref,
    start_label: Label,
    *,
    edges: EdgesOf,
    label: LabelOf,
    readable: Container[str],
    depth: int,
) -> Trace:
    """Walk ``depth`` hops out from ``start``.

    ``edges`` lists the candidates of a record in the order they should be kept when a
    cap bites; ``label`` returns None for a record that is gone, which drops the edge.
    Children of one record are grouped by type and keep that order within a type.
    """
    root = TraceNode(
        type=start.type,
        id=start.id,
        code=start_label.code,
        title=start_label.title,
        status=start_label.status,
        detail=start_label.detail,
        depth=0,
    )
    seen = {start}
    nodes: list[TraceNode] = []
    hidden: set[str] = set()
    truncated = False
    frontier = [root]
    for level in range(1, depth + 1):
        opened: list[TraceNode] = []
        for parent in frontier:
            children: list[TraceNode] = []
            taken: Counter[str] = Counter()
            for edge in await edges(parent.ref):
                ref = edge.ref
                if ref in seen:
                    continue
                if ref.type not in readable:
                    hidden.add(ref.type)
                    continue
                if (
                    taken[ref.type] >= NEIGHBOURS_PER_TYPE
                    or len(nodes) + len(children) >= MAX_NODES
                ):
                    truncated = True
                    continue
                described = await label(ref)
                if described is None:
                    continue
                seen.add(ref)
                taken[ref.type] += 1
                children.append(
                    TraceNode(
                        type=ref.type,
                        id=ref.id,
                        code=described.code,
                        title=described.title,
                        status=described.status,
                        detail=described.detail,
                        depth=level,
                        parent_key=parent.key,
                        relation=edge.relation,
                        direction=edge.direction,
                        linked_at=edge.linked_at,
                        linked_by_id=edge.linked_by_id,
                    )
                )
            children.sort(key=lambda node: _rank(node.type))
            nodes.extend(children)
            opened.extend(children)
        frontier = opened
    return Trace(
        start=root,
        nodes=nodes,
        depth=depth,
        truncated=truncated,
        hidden_types=sorted(hidden, key=lambda t: (_rank(t), t)),
        neighbour_limit=NEIGHBOURS_PER_TYPE,
        node_limit=MAX_NODES,
    )
