"""``AuditService`` — the only path any module takes to the audit trail.

The session is a parameter rather than an injected dependency, and that is the whole
point: the audit write has to join the caller's transaction. A service that opened a
session of its own would produce exactly the failure this table exists to prevent —
a committed audit row describing a change that rolled back
(openspec/changes/add-audit-trail/design.md).

The one exception is the export (``begin_export``, ``export_batches``). It changes nothing
to join: the only row it writes is its own, and it reads from a response body that is
streamed after the request's session has done its work, so it opens its own.
"""

from __future__ import annotations

import base64
import uuid
from collections.abc import AsyncGenerator, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time
from typing import Any, ClassVar, Final, Literal

import orjson
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from verity.core.db import session_scope
from verity.core.errors import InvalidInput
from verity.core.logging import REDACTED, is_sensitive_key
from verity.modules.audit.models import (
    ACTOR_TYPE_MEMBERSHIP,
    ACTOR_TYPE_PLATFORM_ADMIN,
    ACTOR_TYPE_SYSTEM,
    ACTOR_TYPE_VENDOR_CONTACT,
    AUDIT_ACTIONS,
    AuditAction,
    AuditLog,
)
from verity.modules.audit.repository import AuditLogRepository, ExportWindow
from verity.shared.ids import uuid7


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
class VendorContact:
    """A person at a third party, answering through the vendor portal.

    They hold a token, not a session, and have no ``tenant_memberships`` row —
    inventing one would break rule 3, because a membership means somebody who may
    sign in. The id is the ``vendor_contacts`` row. This is the fourth case of the
    polymorphic pair, and the reason that pair exists: one foreign key cannot point
    at memberships, platform admins, vendor contacts and nothing at once.
    """

    id: uuid.UUID
    actor_type: ClassVar[str] = ACTOR_TYPE_VENDOR_CONTACT

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


Actor = Membership | PlatformAdmin | System | VendorContact

_CURSOR_ERROR: Final = "The pagination cursor is not valid."

# Recorded for forensics and access-review evidence, but not surfaced in the
# default customer-facing view: auth telemetry (every login/logout is a session
# row; every attempt an auth_attempt) and the one-time tenant-provisioning
# plumbing. The trail keeps them; the view answers "who changed something that
# matters", not "what rows did the backend create". `include_system` reveals them.
_SYSTEM_OBJECT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "session",
        "auth_attempt",
        "tenant",
        "tenant_branding",
        "tenant_provisioning",
        "tenant_membership",
    }
)

ExportFormat = Literal["csv", "xlsx"]

EXPORT_OBJECT_TYPE: Final = "audit_export"
"""The ``object_type`` of the row an export writes about itself."""

EXPORT_BATCH_SIZE: Final = 1000
"""Rows read per round trip. An export holds one batch in memory at a time, however
long the trail is."""

EXPORT_XLSX_MAX_ROWS: Final = 50_000
"""An Excel file is built in one piece, so it has a ceiling; CSV streams and has none."""

_EXPORT_RANGE_ERROR: Final = (
    "The From date is after the To date. Choose a From date on or before the To date."
)
_EXPORT_TOO_LARGE_ERROR: Final = (
    "An Excel export holds at most {limit} events and this range has more. "
    "Choose a narrower date range, or export CSV, which has no limit."
)
_UNKNOWN_EXPORTER: Final = "Member"

_MEMBER_NAMES_SQL: Final = (
    "SELECT m.id AS id, u.full_name AS name FROM tenant_memberships m "
    "JOIN users u ON u.id = m.user_id WHERE m.id = ANY(:ids)"
)


@dataclass(frozen=True, slots=True)
class ExportRequest:
    """What the person asked to export. ``date_from`` and ``date_to`` are UTC days and
    both are inclusive."""

    file_format: ExportFormat
    date_from: date | None = None
    date_to: date | None = None
    include_system: bool = False
    object_type: str | None = None


@dataclass(frozen=True, slots=True)
class ExportRun:
    """One export that has started and been recorded, ready to read from."""

    export_id: uuid.UUID
    tenant_id: uuid.UUID
    request: ExportRequest
    cut_off: datetime
    """Rows recorded at or after this instant are not in the export — which is how it
    never contains its own audit row."""
    actor_label: str


def _export_window(tenant_id: uuid.UUID, request: ExportRequest, cut_off: datetime) -> ExportWindow:
    return ExportWindow(
        tenant_id=tenant_id,
        occurred_before=cut_off,
        occurred_from=(
            None
            if request.date_from is None
            else datetime.combine(request.date_from, time.min, tzinfo=UTC)
        ),
        # time.max is the last microsecond of the day, the resolution of occurred_at, so
        # an inclusive bound needs no "start of the next day" that overflows on 9999-12-31.
        occurred_to=(
            None
            if request.date_to is None
            else datetime.combine(request.date_to, time.max, tzinfo=UTC)
        ),
        exclude_object_types=None if request.include_system else _SYSTEM_OBJECT_TYPES,
        object_type=request.object_type,
    )


def _export_snapshot(request: ExportRequest, rows: int | None) -> dict[str, object]:
    snapshot: dict[str, object] = {
        "format": request.file_format,
        "from": None if request.date_from is None else request.date_from.isoformat(),
        "to": None if request.date_to is None else request.date_to.isoformat(),
        "include_system": request.include_system,
        "object_type": request.object_type,
    }
    if rows is not None:
        snapshot["rows"] = rows
    return snapshot


@dataclass(frozen=True, slots=True)
class AuditLabels:
    """Resolved human names for a page of events — the person who acted and the
    object acted on, so the trail reads as sentences instead of type + id."""

    members: dict[uuid.UUID, str]  # membership_id -> the user's full name
    users: dict[uuid.UUID, str]
    roles: dict[uuid.UUID, str]
    groups: dict[uuid.UUID, str]
    assets: dict[uuid.UUID, str]
    tasks: dict[uuid.UUID, str]  # task -> its code, e.g. TSK-0014
    findings: dict[uuid.UUID, str]  # vuln_instance -> its CVE, else the title

    def actor(self, actor_type: str, actor_id: uuid.UUID | None) -> str | None:
        if actor_type == ACTOR_TYPE_MEMBERSHIP and actor_id is not None:
            return self.members.get(actor_id)
        return None

    def obj(self, object_type: str, object_id: uuid.UUID) -> str | None:
        by_type: dict[str, dict[uuid.UUID, str]] = {
            "tenant_membership": self.members,
            "membership": self.members,
            "role": self.roles,
            "group": self.groups,
            "user": self.users,
            "asset": self.assets,
            "task": self.tasks,
            "vuln_instance": self.findings,
        }
        return by_type.get(object_type, {}).get(object_id)


ExportBatch = tuple[list[AuditLog], AuditLabels]
"""One read of an export: the rows, and the names behind them."""


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
        if not isinstance(actor, Membership | PlatformAdmin | System | VendorContact):
            raise TypeError(
                f"actor must be Membership, PlatformAdmin, System or VendorContact, got {actor!r}"
            )
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

    async def list_page(  # noqa: PLR0913 — one keyword per documented filter
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID | None,
        limit: int,
        cursor: str | None = None,
        include_system: bool = False,
        object_type: str | None = None,
        object_id: uuid.UUID | None = None,
    ) -> tuple[list[AuditLog], str | None]:
        """One page, newest first, with the cursor for the next page or ``None``.

        By default the auth/provisioning telemetry in ``_SYSTEM_OBJECT_TYPES`` is
        hidden — the view is business changes, not backend row churn.
        ``include_system=True`` returns everything for a security/forensics read."""
        if limit < 1:
            raise ValueError("limit must be at least 1")
        before = None if cursor is None else decode_cursor(cursor)
        # One row beyond the page answers "is there a next page" without a count,
        # which on this table would only ever grow more expensive.
        entries = await self._repository.list_page(
            session,
            tenant_id=tenant_id,
            limit=limit + 1,
            object_type=object_type,
            object_id=object_id,
            before=before,
            exclude_object_types=None if include_system else _SYSTEM_OBJECT_TYPES,
        )
        if len(entries) <= limit:
            return entries, None
        page = entries[:limit]
        last = page[-1]
        return page, encode_cursor(last.occurred_at, last.id)

    async def resolve_labels(
        self, session: AsyncSession, entries: Sequence[AuditLog]
    ) -> AuditLabels:
        """Batch-resolve the real names behind a page of events. Reads the handful
        of columns it needs by name — no cross-module model import — the same
        identity-resolution pattern ``core.deps`` uses. Runs under the caller's
        tenant session, so RLS keeps every lookup inside the tenant."""
        member_ids: set[uuid.UUID] = set()
        user_ids: set[uuid.UUID] = set()
        role_ids: set[uuid.UUID] = set()
        group_ids: set[uuid.UUID] = set()
        asset_ids: set[uuid.UUID] = set()
        task_ids: set[uuid.UUID] = set()
        finding_ids: set[uuid.UUID] = set()
        for e in entries:
            if e.actor_type == ACTOR_TYPE_MEMBERSHIP and e.actor_id is not None:
                member_ids.add(e.actor_id)
            if e.object_type in ("tenant_membership", "membership"):
                member_ids.add(e.object_id)
            elif e.object_type == "role":
                role_ids.add(e.object_id)
            elif e.object_type == "group":
                group_ids.add(e.object_id)
            elif e.object_type == "user":
                user_ids.add(e.object_id)
            elif e.object_type == "asset":
                asset_ids.add(e.object_id)
            elif e.object_type == "task":
                task_ids.add(e.object_id)
            elif e.object_type == "vuln_instance":
                finding_ids.add(e.object_id)
        return AuditLabels(
            members=await self._names(session, _MEMBER_NAMES_SQL, member_ids),
            users=await self._names(
                session, "SELECT id, full_name AS name FROM users WHERE id = ANY(:ids)", user_ids
            ),
            roles=await self._names(
                session, "SELECT id, name FROM roles WHERE id = ANY(:ids)", role_ids
            ),
            groups=await self._names(
                session, "SELECT id, name FROM groups WHERE id = ANY(:ids)", group_ids
            ),
            assets=await self._names(
                session, "SELECT id, name FROM assets WHERE id = ANY(:ids)", asset_ids
            ),
            tasks=await self._names(
                session, "SELECT id, code AS name FROM tasks WHERE id = ANY(:ids)", task_ids
            ),
            # A finding has no name of its own — it is identified by the CVE on
            # its definition, falling back to that definition's title.
            findings=await self._names(
                session,
                "SELECT i.id AS id, COALESCE(d.cve_id, d.title) AS name "
                "FROM vuln_instances i JOIN vuln_definitions d ON d.id = i.definition_id "
                "WHERE i.id = ANY(:ids)",
                finding_ids,
            ),
        )

    @staticmethod
    async def _names(session: AsyncSession, sql: str, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not ids:
            return {}
        rows = (await session.execute(text(sql), {"ids": list(ids)})).all()
        return {row.id: row.name for row in rows if row.name}

    async def begin_export(
        self, *, tenant_id: uuid.UUID, actor: Membership, request: ExportRequest
    ) -> ExportRun:
        """Start one export: fix its cut-off, and write its audit row before any data
        leaves.

        Runs in a unit of work of its own rather than the caller's. A streamed response
        outlives the request's session, and the row has to be committed by the time the
        first byte is sent: an export that fails half way is still an export that
        happened. The cut-off is the database's ``now()`` in the same transaction as the
        audit row, so the two are the same instant and the row sits exactly on the
        boundary the export excludes.

        An Excel export is counted first. The count is bounded, so a long trail costs no
        more than the ceiling, and it is what lets the row carry ``rows``; a streamed CSV
        has no count to give, so its row has none.

        Raises:
            InvalidInput: the range runs backwards, or an Excel export is over its ceiling.
        """
        if request.date_from and request.date_to and request.date_from > request.date_to:
            raise InvalidInput(
                _EXPORT_RANGE_ERROR,
                detail=f"export range {request.date_from} to {request.date_to} runs backwards",
            )
        request = replace(request, object_type=(request.object_type or "").strip() or None)
        async with session_scope(tenant_id) as session:
            cut_off = await self._repository.database_time(session)
            rows: int | None = None
            if request.file_format == "xlsx":
                rows = await self._repository.export_count(
                    session,
                    _export_window(tenant_id, request, cut_off),
                    limit=EXPORT_XLSX_MAX_ROWS,
                )
                if rows > EXPORT_XLSX_MAX_ROWS:
                    raise InvalidInput(
                        _EXPORT_TOO_LARGE_ERROR.format(limit=f"{EXPORT_XLSX_MAX_ROWS:,}"),
                        detail="xlsx export is over the row ceiling",
                    )
            run = ExportRun(
                export_id=uuid7(),
                tenant_id=tenant_id,
                request=request,
                cut_off=cut_off,
                actor_label=(await self._names(session, _MEMBER_NAMES_SQL, {actor.id})).get(
                    actor.id, _UNKNOWN_EXPORTER
                ),
            )
            await self.record(
                session,
                action="create",
                object_type=EXPORT_OBJECT_TYPE,
                object_id=run.export_id,
                actor=actor,
                tenant_id=tenant_id,
                after=_export_snapshot(request, rows),
            )
        return run

    async def export_batches(self, run: ExportRun) -> AsyncGenerator[ExportBatch, None]:
        """The export's events, oldest first, one batch at a time, with the names the
        list shows.

        Each batch is read in a unit of work of its own and nothing is held between
        them: a long export never pins a connection or a transaction, and never holds
        more than one batch, however long the trail is."""
        window = _export_window(run.tenant_id, run.request, run.cut_off)
        after: tuple[datetime, uuid.UUID] | None = None
        while True:
            async with session_scope(run.tenant_id) as session:
                rows = await self._repository.export_batch(
                    session, window, after=after, limit=EXPORT_BATCH_SIZE
                )
                labels = await self.resolve_labels(session, rows)
            if not rows:
                return
            yield rows, labels
            if len(rows) < EXPORT_BATCH_SIZE:
                return
            after = (rows[-1].occurred_at, rows[-1].id)

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
