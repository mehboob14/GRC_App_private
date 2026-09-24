"""Wire shapes for linked records."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LinkedRecordOut(_Response):
    link_id: uuid.UUID
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
