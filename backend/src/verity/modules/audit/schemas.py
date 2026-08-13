"""Response models for the audit trail. There is no request body — the trail is
written by services, never by clients, and the one route only reads."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, computed_field, field_serializer

from verity.modules.audit.models import ActorType, AuditAction


def _humanize(value: str) -> str:
    """``tenant_membership`` -> ``Tenant membership``, ``session`` -> ``Session``."""
    return value.replace("_", " ").capitalize()


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

    @computed_field
    @property
    def actor_label(self) -> str:
        """A human label for the actor, resolved in-module (no cross-module lookup).

        ``System`` for jobs; otherwise the humanised actor kind plus the id's short
        prefix, e.g. ``Membership · 019ff785``. Resolving the actor's *name* needs the
        iam module and is a deliberate follow-up; the id keeps rows distinguishable now.
        """
        if self.actor_type == "system":
            return "System"
        suffix = f" · {str(self.actor_id)[:8]}" if self.actor_id is not None else ""
        return f"{_humanize(self.actor_type)}{suffix}"

    @computed_field
    @property
    def object_label(self) -> str:
        """The humanised object kind plus the id's short prefix, e.g.
        ``Tenant membership · 019ff7a4``."""
        return f"{_humanize(self.object_type)} · {str(self.object_id)[:8]}"

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
