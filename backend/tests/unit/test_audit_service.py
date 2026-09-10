"""``AuditService`` with the repository faked — actor kinds, snapshots, cursors."""

from __future__ import annotations

import base64
import uuid
from collections.abc import Collection
from datetime import UTC, datetime
from typing import cast

import orjson
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from verity.core.errors import InvalidInput
from verity.core.logging import REDACTED
from verity.modules.audit.models import AuditAction, AuditLog
from verity.modules.audit.repository import AuditLogRepository
from verity.modules.audit.service import (
    AuditService,
    Membership,
    PlatformAdmin,
    System,
    decode_cursor,
    encode_cursor,
)
from verity.shared.ids import uuid7

SESSION = cast("AsyncSession", object())


class FakeAuditLogRepository(AuditLogRepository):
    def __init__(self) -> None:
        self.added: list[AuditLog] = []
        self.page: list[AuditLog] = []
        self.requested: tuple[uuid.UUID | None, int, tuple[datetime, uuid.UUID] | None] | None = (
            None
        )

    async def add(self, session: AsyncSession, entry: AuditLog) -> None:
        self.added.append(entry)

    async def list_page(  # noqa: PLR0913 — mirrors the real repository exactly
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID | None,
        limit: int,
        before: tuple[datetime, uuid.UUID] | None = None,
        exclude_object_types: Collection[str] | None = None,
        object_type: str | None = None,
        object_id: uuid.UUID | None = None,
    ) -> list[AuditLog]:
        # The filters this fake ignores are exercised against the real
        # repository in the integration suite; the signature still has to match,
        # or the fake silently stops standing in for what it replaces.
        self.requested = (tenant_id, limit, before)
        return self.page[:limit]


@pytest.fixture
def repository() -> FakeAuditLogRepository:
    return FakeAuditLogRepository()


@pytest.fixture
def service(repository: FakeAuditLogRepository) -> AuditService:
    return AuditService(repository)


# ---------------------------------------------------------------------------
# The three actor kinds
# ---------------------------------------------------------------------------


async def test_a_membership_actor_is_recorded_as_one(
    service: AuditService, repository: FakeAuditLogRepository
) -> None:
    membership_id, object_id, tenant_id = uuid7(), uuid7(), uuid7()
    await service.record(
        SESSION,
        action="update",
        object_type="control",
        object_id=object_id,
        actor=Membership(membership_id),
        tenant_id=tenant_id,
        before={"status": "draft"},
        after={"status": "active"},
    )
    (entry,) = repository.added
    assert entry.actor_type == "membership"
    assert entry.actor_id == membership_id
    assert entry.tenant_id == tenant_id
    assert entry.action == "update"
    assert entry.object_type == "control"
    assert entry.object_id == object_id
    assert entry.before == {"status": "draft"}
    assert entry.after == {"status": "active"}


async def test_a_platform_admin_actor_is_recorded_as_one(
    service: AuditService, repository: FakeAuditLogRepository
) -> None:
    admin_id = uuid7()
    await service.record(
        SESSION,
        action="create",
        object_type="tenant",
        object_id=uuid7(),
        actor=PlatformAdmin(admin_id),
        tenant_id=None,
    )
    (entry,) = repository.added
    assert entry.actor_type == "platform_admin"
    assert entry.actor_id == admin_id
    assert entry.tenant_id is None


async def test_a_system_actor_carries_no_actor_id(
    service: AuditService, repository: FakeAuditLogRepository
) -> None:
    await service.record(
        SESSION,
        action="transition",
        object_type="evidence",
        object_id=uuid7(),
        actor=System(),
        tenant_id=uuid7(),
    )
    (entry,) = repository.added
    assert entry.actor_type == "system"
    assert entry.actor_id is None


def test_a_system_actor_cannot_be_given_an_id() -> None:
    """Mirrors the paired CHECK on the table, refused before any database."""
    with pytest.raises(TypeError):
        System(uuid7())  # type: ignore[call-arg]


def test_a_membership_actor_cannot_omit_its_id() -> None:
    with pytest.raises(TypeError):
        Membership()  # type: ignore[call-arg]
    with pytest.raises(TypeError, match="must be a UUID"):
        Membership(cast("uuid.UUID", None))


def test_a_platform_admin_actor_rejects_a_non_uuid_id() -> None:
    with pytest.raises(TypeError, match="must be a UUID"):
        PlatformAdmin(cast("uuid.UUID", "not-a-uuid"))


async def test_an_unknown_actor_object_is_rejected(
    service: AuditService, repository: FakeAuditLogRepository
) -> None:
    with pytest.raises(TypeError, match="actor must be"):
        await service.record(
            SESSION,
            action="create",
            object_type="control",
            object_id=uuid7(),
            actor=cast("System", "system"),
            tenant_id=uuid7(),
        )
    assert repository.added == []


async def test_an_unknown_action_is_rejected_before_the_database(
    service: AuditService, repository: FakeAuditLogRepository
) -> None:
    with pytest.raises(ValueError, match="unknown audit action"):
        await service.record(
            SESSION,
            action=cast("AuditAction", "login"),
            object_type="session",
            object_id=uuid7(),
            actor=System(),
            tenant_id=None,
        )
    assert repository.added == []


async def test_an_empty_object_type_is_rejected(
    service: AuditService, repository: FakeAuditLogRepository
) -> None:
    with pytest.raises(ValueError, match="object_type"):
        await service.record(
            SESSION,
            action="create",
            object_type="",
            object_id=uuid7(),
            actor=System(),
            tenant_id=None,
        )
    assert repository.added == []


async def test_snapshot_payloads_are_coerced_to_json_safe_values(
    service: AuditService, repository: FakeAuditLogRepository
) -> None:
    """UUIDs and timestamps become strings, so the JSONB insert cannot fail on a
    perfectly ordinary column type."""
    owner = uuid7()
    at = datetime(2026, 1, 1, tzinfo=UTC)
    await service.record(
        SESSION,
        action="create",
        object_type="control",
        object_id=uuid7(),
        actor=System(),
        tenant_id=uuid7(),
        after={"owner_id": owner, "captured_at": at},
    )
    (entry,) = repository.added
    assert entry.after == {"owner_id": str(owner), "captured_at": at.isoformat()}


# ---------------------------------------------------------------------------
# Snapshots — the secret deny-list, imported from core.logging
# ---------------------------------------------------------------------------


class _SnapshotBase(DeclarativeBase):
    """A base of its own, so the probe never registers on the real metadata."""


class _CredentialRow(_SnapshotBase):
    __tablename__ = "snapshot_probe_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str]
    password_hash: Mapped[str]
    mfa_secret_encrypted: Mapped[str]
    recovery_codes_encrypted: Mapped[str]


@pytest.fixture
def credential_row() -> _CredentialRow:
    return _CredentialRow(
        id=1,
        email="person@example.com",
        password_hash="$argon2id$v=19$...",  # noqa: S106
        mfa_secret_encrypted="ciphertext-a",  # noqa: S106
        recovery_codes_encrypted="ciphertext-b",
    )


def test_snapshot_redacts_secret_columns_but_keeps_the_change_visible(
    credential_row: _CredentialRow,
) -> None:
    snapshot = AuditService.snapshot(credential_row)
    assert snapshot["password_hash"] == REDACTED
    assert snapshot["mfa_secret_encrypted"] == REDACTED
    assert snapshot["recovery_codes_encrypted"] == REDACTED
    # The fields are present — the event is not silent — but no ciphertext survives.
    assert "argon2id" not in str(snapshot)
    assert "ciphertext" not in str(snapshot)
    assert snapshot["email"] == "person@example.com"
    assert snapshot["id"] == 1


def test_snapshot_restricts_to_the_named_fields(credential_row: _CredentialRow) -> None:
    assert AuditService.snapshot(credential_row, fields=["email"]) == {
        "email": "person@example.com"
    }


def test_snapshot_redacts_even_when_a_secret_field_is_named_explicitly(
    credential_row: _CredentialRow,
) -> None:
    assert AuditService.snapshot(credential_row, fields=["password_hash"]) == {
        "password_hash": REDACTED
    }


def test_snapshot_refuses_a_field_that_is_not_a_mapped_column(
    credential_row: _CredentialRow,
) -> None:
    with pytest.raises(ValueError, match="not mapped"):
        AuditService.snapshot(credential_row, fields=["email", "no_such_column"])


# ---------------------------------------------------------------------------
# Cursor encoding
# ---------------------------------------------------------------------------


def test_the_cursor_round_trips() -> None:
    occurred_at = datetime(2026, 8, 12, 9, 30, 15, 123456, tzinfo=UTC)
    entry_id = uuid7()
    assert decode_cursor(encode_cursor(occurred_at, entry_id)) == (occurred_at, entry_id)


@pytest.mark.parametrize(
    "cursor",
    [
        "",
        "not-base64!!!",
        "AAAA",  # valid base64, not JSON
        encode_cursor(datetime(2026, 1, 1, tzinfo=UTC), uuid7())[:-8],  # truncated
    ],
)
def test_a_malformed_cursor_is_a_typed_domain_error(cursor: str) -> None:
    with pytest.raises(InvalidInput):
        decode_cursor(cursor)


def test_a_cursor_with_the_wrong_shape_is_refused() -> None:
    wrong_arity = base64.urlsafe_b64encode(orjson.dumps(["2026-01-01T00:00:00+00:00"])).decode()
    with pytest.raises(InvalidInput):
        decode_cursor(wrong_arity)
    not_a_uuid = base64.urlsafe_b64encode(
        orjson.dumps(["2026-01-01T00:00:00+00:00", "not-a-uuid"])
    ).decode()
    with pytest.raises(InvalidInput):
        decode_cursor(not_a_uuid)


def test_a_cursor_with_a_naive_timestamp_is_refused() -> None:
    naive = base64.urlsafe_b64encode(orjson.dumps(["2026-01-01T00:00:00", str(uuid7())])).decode()
    with pytest.raises(InvalidInput):
        decode_cursor(naive)


# ---------------------------------------------------------------------------
# Page assembly
# ---------------------------------------------------------------------------


def _entry(occurred_at: datetime) -> AuditLog:
    return AuditLog(
        id=uuid7(),
        tenant_id=uuid7(),
        actor_type="system",
        actor_id=None,
        action="create",
        object_type="control",
        object_id=uuid7(),
        occurred_at=occurred_at,
    )


async def test_a_full_page_carries_the_cursor_of_its_last_entry(
    service: AuditService, repository: FakeAuditLogRepository
) -> None:
    base = datetime(2026, 8, 12, 12, 0, 0, tzinfo=UTC)
    newest, middle, oldest = (_entry(base.replace(minute=m)) for m in (30, 20, 10))
    repository.page = [newest, middle, oldest]

    entries, next_cursor = await service.list_page(SESSION, tenant_id=uuid7(), limit=2)

    assert entries == [newest, middle]
    assert next_cursor == encode_cursor(middle.occurred_at, middle.id)
    assert repository.requested is not None
    # One row beyond the page answers "is there a next page" without a count.
    assert repository.requested[1] == 3


async def test_the_last_page_carries_no_cursor(
    service: AuditService, repository: FakeAuditLogRepository
) -> None:
    repository.page = [_entry(datetime(2026, 8, 12, 12, 0, 0, tzinfo=UTC))]
    entries, next_cursor = await service.list_page(SESSION, tenant_id=uuid7(), limit=2)
    assert len(entries) == 1
    assert next_cursor is None


async def test_the_cursor_is_passed_through_to_the_repository(
    service: AuditService, repository: FakeAuditLogRepository
) -> None:
    occurred_at = datetime(2026, 8, 12, 12, 0, 0, tzinfo=UTC)
    entry_id = uuid7()
    await service.list_page(
        SESSION, tenant_id=None, limit=5, cursor=encode_cursor(occurred_at, entry_id)
    )
    assert repository.requested == (None, 6, (occurred_at, entry_id))


async def test_a_non_positive_limit_is_a_programmer_error(service: AuditService) -> None:
    with pytest.raises(ValueError, match="limit"):
        await service.list_page(SESSION, tenant_id=None, limit=0)
