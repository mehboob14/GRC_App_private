"""Response models for the audit trail. There is no request body — the trail is
written by services, never by clients, and the one route only reads."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer

from verity.modules.audit.models import ActorType, AuditAction


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    actor_type: ActorType
    actor_id: uuid.UUID | None
    action: AuditAction
    object_type: str
    object_id: uuid.UUID
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    occurred_at: datetime

    @field_serializer("occurred_at")
    def _iso_utc_z(self, value: datetime) -> str:
        # docs/conventions/api.md: ISO 8601 UTC with a Z suffix. Pydantic's default
        # renders +00:00, which is valid but not what the contract promises.
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class AuditLogPage(BaseModel):
    items: list[AuditLogEntry]
    next_cursor: str | None
    """Opaque. Pass it back as ``?cursor=`` for the next page; ``None`` means the
    listing is exhausted."""
