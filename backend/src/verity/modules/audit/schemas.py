"""Response models for the audit trail. There is no request body — the trail is
written by services, never by clients, and the one route only reads."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer, model_validator

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
    # The UI renders these; they are derived (below) from the fields above, in-module —
    # resolving the actor's real name needs the iam module and is a deliberate follow-up.
    # The default lets from_attributes build the model from an ORM row that has neither.
    actor_label: str = ""
    object_label: str = ""

    @model_validator(mode="after")
    def _derive_labels(self) -> AuditLogEntry:
        """A human label for the actor (``System`` for jobs; else the humanised kind plus
        the id's short prefix, e.g. ``Membership · 019ff785``) and for the object
        (``Tenant membership · 019ff7a4``). Distinguishes rows without a cross-module lookup."""
        if self.actor_type == "system":
            self.actor_label = "System"
        else:
            suffix = f" · {str(self.actor_id)[:8]}" if self.actor_id is not None else ""
            self.actor_label = f"{_humanize(self.actor_type)}{suffix}"
        self.object_label = f"{_humanize(self.object_type)} · {str(self.object_id)[:8]}"
        return self

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
