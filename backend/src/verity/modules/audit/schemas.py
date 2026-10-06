"""Response models for the audit trail. There is no request body — the trail is
written by services, never by clients, and the routes only read."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, field_serializer, model_validator

from verity.modules.audit.models import ActorType, AuditAction, AuditLog


class ResolvedNames(Protocol):
    """What ``AuditLogEntry.labelled`` asks of ``AuditLabels``. A protocol, so this
    module does not import the service that owns the class: other modules import that
    service, and a path from it to ``audit.models`` through here would break theirs."""

    def actor(self, actor_type: str, actor_id: uuid.UUID | None) -> str | None: ...

    def obj(self, object_type: str, object_id: uuid.UUID) -> str | None: ...


def _humanize(value: str) -> str:
    """``tenant_membership`` -> ``Tenant membership``, ``session`` -> ``Session``."""
    return value.replace("_", " ").capitalize()


def iso_utc_z(value: datetime) -> str:
    """docs/conventions/api.md: ISO 8601 UTC with a Z suffix. Pydantic's default
    renders +00:00, which is valid but not what the contract promises. The export
    writes ``occurred_at`` through the same function, so a file and the API agree."""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


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
        """Fallback labels only — the humanised kind (``System``, ``Membership``,
        ``Tenant membership``), with no id noise. The router overrides these with
        the actor's and object's real names (``resolve_labels``) whenever the
        cross-module lookup resolves one; these stand in when it does not."""
        if not self.actor_label:
            self.actor_label = (
                "System" if self.actor_type == "system" else _humanize(self.actor_type)
            )
        if not self.object_label:
            self.object_label = _humanize(self.object_type)
        return self

    @classmethod
    def labelled(cls, row: AuditLog, names: ResolvedNames) -> AuditLogEntry:
        """``row`` as an event, carrying the real names ``names`` resolved. Where a
        lookup came back empty, the humanised kind the validator filled in stands. The
        list route and the export both read events through this."""
        item = cls.model_validate(row)
        actor = names.actor(row.actor_type, row.actor_id)
        if actor:
            item.actor_label = actor
        obj = names.obj(row.object_type, row.object_id)
        if obj:
            item.object_label = obj
        return item

    @field_serializer("occurred_at")
    def _iso_utc_z(self, value: datetime) -> str:
        return iso_utc_z(value)


class AuditLogPage(BaseModel):
    items: list[AuditLogEntry]
    next_cursor: str | None
    """Opaque. Pass it back as ``?cursor=`` for the next page; ``None`` means the
    listing is exhausted."""
