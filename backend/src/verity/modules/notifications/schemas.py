"""Request/response contracts for notifications."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from verity.modules.tenancy.schemas import UtcDateTime


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class NotificationOut(_Response):
    id: uuid.UUID
    kind: str
    title: str
    body: str
    object_type: str | None
    object_id: uuid.UUID | None
    read_at: UtcDateTime | None
    created_at: UtcDateTime


class NotificationInboxOut(_Response):
    """One call gives the bell everything it needs: the recent items and the
    unread badge count (which may exceed ``len(items)`` past the page limit)."""

    items: list[NotificationOut]
    unread_count: int


class MarkedReadOut(_Response):
    marked: int
