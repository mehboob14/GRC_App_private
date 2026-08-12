"""``AuditService`` — the only path any module takes to the audit trail.

The session is a parameter rather than an injected dependency, and that is the whole
point: the audit write has to join the caller's transaction. A service that opened a
session of its own would produce exactly the failure this table exists to prevent —
a committed audit row describing a change that rolled back
(openspec/changes/add-audit-trail/design.md).
"""

from __future__ import annotations

import base64
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Final

import orjson
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from verity.core.errors import InvalidInput
from verity.core.logging import REDACTED, is_sensitive_key
from verity.modules.audit.models import (
    ACTOR_TYPE_MEMBERSHIP,
    ACTOR_TYPE_PLATFORM_ADMIN,
    ACTOR_TYPE_SYSTEM,
    AUDIT_ACTIONS,
    AuditAction,
    AuditLog,
)
from verity.modules.audit.repository import AuditLogRepository


def _require_uuid(value: object, *, owner: str) -> None:
    if not isinstance(value, uuid.UUID):
        raise TypeError(f"{owner}.id must be a UUID, got {type(value).__name__}")


@dataclass(frozen=True, slots=True)
class Membership:
    """A person acting inside a tenant. The id is the membership, never the user."""

    id: uuid.UUID
    actor_type: ClassVar[str] = ACTOR_TYPE_MEMBERSHIP

    def __post_init__(self) -> None:
        _require_uuid(self.id, owner=type(self).__name__)

    @property
    def actor_id(self) -> uuid.UUID:
        return self.id


@dataclass(frozen=True, slots=True)
class PlatformAdmin:
    """An operator acting on the provider plane."""

    id: uuid.UUID
    actor_type: ClassVar[str] = ACTOR_TYPE_PLATFORM_ADMIN

    def __post_init__(self) -> None:
        _require_uuid(self.id, owner=type(self).__name__)

    @property
    def actor_id(self) -> uuid.UUID:
        return self.id


@dataclass(frozen=True, slots=True)
class System:
    """A scheduled job or internal process. Deliberately has no identifier — a
    ``System`` actor carrying one is refused by construction, mirroring the paired
    CHECK on the table."""

    actor_type: ClassVar[str] = ACTOR_TYPE_SYSTEM

    @property
    def actor_id(self) -> None:
        return None


Actor = Membership | PlatformAdmin | System

_CURSOR_ERROR: Final = "The pagination cursor is not valid."


def encode_cursor(occurred_at: datetime, entry_id: uuid.UUID) -> str:
    """Opaque keyset cursor for ``(occurred_at, id)``, newest-first pagination."""
    payload = orjson.dumps([occurred_at.isoformat(), str(entry_id)])
    return base64.urlsafe_b64encode(payload).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Reverse :func:`encode_cursor`.

    Raises:
        InvalidInput: on any malformed cursor — one code and one message for every
            failure mode, because the cursor is opaque and a client that took it
            apart gets no help putting it back together.
    """
    try:
        decoded = orjson.loads(base64.urlsafe_b64decode(cursor.encode()))
        occurred_at_raw, entry_id_raw = decoded
        occurred_at = datetime.fromisoformat(occurred_at_raw)
        entry_id = uuid.UUID(entry_id_raw)
    except (ValueError, TypeError) as exc:
        raise InvalidInput(_CURSOR_ERROR, detail=f"cursor failed to decode: {exc}") from exc
    if occurred_at.tzinfo is None:
        raise InvalidInput(_CURSOR_ERROR, detail="cursor carried a naive timestamp")
    return occurred_at, entry_id


def _jsonable(snapshot: Mapping[str, object]) -> dict[str, Any]:
    """Coerce a snapshot to JSON-safe primitives (UUIDs and timestamps to strings),
    so the JSONB insert cannot fail on a perfectly ordinary column type."""
    coerced: dict[str, Any] = orjson.loads(orjson.dumps(dict(snapshot), default=str))
    return coerced


class AuditService:
    """Records state changes and reads them back. Every other module reaches the
    trail through this class, never through the repository or the table."""

    def __init__(self, repository: AuditLogRepository | None = None) -> None:
        self._repository = repository or AuditLogRepository()

    # The eight parameters are the audit row's eight facts, fixed by
    # add-audit-trail/design.md; bundling them into a parameter object would just
    # move the same signature one hop away.
    async def record(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        action: AuditAction,
        object_type: str,
        object_id: uuid.UUID,
        actor: Actor,
        tenant_id: uuid.UUID | None,
        before: Mapping[str, object] | None = None,
        after: Mapping[str, object] | None = None,
    ) -> None:
        """Write one audit row on the caller's session, inside the caller's
        transaction. ``tenant_id`` is the stream the event belongs to — a platform
        admin acting on tenant X passes X, so the event lands in X's history.
        """
        if action not in AUDIT_ACTIONS:
            raise ValueError(f"unknown audit action {action!r}; expected one of {AUDIT_ACTIONS}")
        if not isinstance(actor, Membership | PlatformAdmin | System):
            raise TypeError(f"actor must be Membership, PlatformAdmin, or System, got {actor!r}")
        if not object_type:
            raise ValueError("object_type must be a non-empty string")
        entry = AuditLog(
            tenant_id=tenant_id,
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            before=None if before is None else _jsonable(before),
            after=None if after is None else _jsonable(after),
        )
        await self._repository.add(session, entry)

    async def list_page(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID | None,
        limit: int,
        cursor: str | None = None,
    ) -> tuple[list[AuditLog], str | None]:
        """One page, newest first, with the cursor for the next page or ``None``."""
        if limit < 1:
            raise ValueError("limit must be at least 1")
        before = None if cursor is None else decode_cursor(cursor)
        # One row beyond the page answers "is there a next page" without a count,
        # which on this table would only ever grow more expensive.
        entries = await self._repository.list_page(
            session, tenant_id=tenant_id, limit=limit + 1, before=before
        )
        if len(entries) <= limit:
            return entries, None
        page = entries[:limit]
        last = page[-1]
        return page, encode_cursor(last.occurred_at, last.id)

    @staticmethod
    def snapshot(
        instance: DeclarativeBase, *, fields: Sequence[str] | None = None
    ) -> dict[str, Any]:
        """The before/after payload for ``record``, with secrets removed.

        Reads mapped columns only — relationships and Python-side attributes never
        enter the trail. Any column whose name matches the secret deny-list — the
        same one ``core.logging`` uses, imported so a new secret column is covered
        in logs and snapshots at once — is replaced with the redaction marker, so
        the change is still visible as having happened.
        """
        mapped = [attr.key for attr in sa_inspect(type(instance)).mapper.column_attrs]
        if fields is not None:
            unknown = sorted(set(fields) - set(mapped))
            if unknown:
                raise ValueError(f"fields not mapped on {type(instance).__name__}: {unknown}")
            mapped = [name for name in mapped if name in set(fields)]
        return _jsonable(
            {
                name: REDACTED if is_sensitive_key(name) else getattr(instance, name)
                for name in mapped
            }
        )


audit_service: Final = AuditService()
"""The shared instance other modules call. The class stays importable for tests
that fake the repository."""
