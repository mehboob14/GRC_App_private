"""Wire shapes for linked records."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from verity.modules.tenancy.schemas import UtcDateTime


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LinkedRecordOut(_Response):
    # Null for a pair the other record's page manages: there is no link to remove.
    link_id: uuid.UUID | None
    target_type: str
    target_id: uuid.UUID
    relation: str
    direction: str
    code: str
    title: str
    status: str
    detail: str | None
    can_unlink: bool


class LinkedRecordsOut(_Response):
    records: list[LinkedRecordOut]
    offered: list[str]
    can_link: list[str]
    # The read only groups among `offered`, each with where its pair is changed.
    managed_elsewhere: dict[str, str]


class LinkWrite(_Request):
    target_type: str = Field(min_length=1, max_length=40)
    target_id: uuid.UUID


class RaiseRiskWrite(_Request):
    title: str | None = Field(default=None, max_length=300)
    register_id: uuid.UUID | None = None


class RaisedRiskOut(_Response):
    id: uuid.UUID
    code: str
    title: str


class TraceNodeOut(_Response):
    """One record in a trace. ``relation`` and ``direction`` describe the edge to its
    parent, read from the parent: "Mitigated by" under a risk is a control."""

    key: str
    type: str
    id: uuid.UUID
    code: str
    title: str
    status: str
    detail: str | None
    depth: int
    parent_key: str | None
    relation: str | None
    direction: str | None
    # Only a link drawn on the links table carries these; a pair with its own table does not.
    linked_at: UtcDateTime | None
    linked_by: str | None


class TraceOut(_Response):
    start: TraceNodeOut
    nodes: list[TraceNodeOut]
    depth: int
    # A cap left records out: too many of one type under a record, or too many in all.
    truncated: bool
    # Types linked to something in this trace that the caller may not read.
    hidden_types: list[str]
    neighbour_limit: int
    node_limit: int
