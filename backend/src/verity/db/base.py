"""The declarative base, the mixins every table uses, and the helpers that keep
docs/conventions/database.md from being optional.

A module that hand-rolls its primary key, its timestamps, its ``tenant_id``, or its
integration columns will eventually get one of them subtly different — a naive
datetime, a UUIDv4, a composite index with ``tenant_id`` second. So they are mixins,
and the index helper refuses to build an index that does not lead with ``tenant_id``.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any, ClassVar, Final

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    MetaData,
    Text,
    UniqueConstraint,
    column,
    func,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

from verity.shared.ids import uuid7

TENANT_TABLE: Final = "tenants"
TENANT_ID_COLUMN: Final = "tenant_id"

# docs/conventions/database.md: ix_<table>__<cols>, uq_<table>__<cols>,
# ck_<table>__<rule>. Naming the objects in the metadata rather than in each migration
# means Alembic autogenerate produces the convention instead of `ix_1234abcd`.
NAMING_CONVENTION: Final[dict[str, str]] = {
    "ix": "ix_%(table_name)s__%(column_0_N_name)s",
    "uq": "uq_%(table_name)s__%(column_0_N_name)s",
    "ck": "ck_%(table_name)s__%(constraint_name)s",
    "fk": "fk_%(table_name)s__%(column_0_N_name)s",
    "pk": "pk_%(table_name)s",
}

_IDENTIFIER: Final = re.compile(r"^[a-z_][a-z0-9_]*$")

DEFAULT_SOURCE: Final = "manual"


def _validate_identifier(value: str, *, what: str) -> str:
    if not _IDENTIFIER.match(value):
        raise ValueError(f"{what} {value!r} is not a valid snake_case identifier")
    return value


class Base(DeclarativeBase):
    """Declarative base for every table in the system."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    type_annotation_map: ClassVar[dict[Any, Any]] = {
        uuid.UUID: postgresql.UUID(as_uuid=True),
        # Every timestamp is tz-aware and stored UTC. A naive datetime column is how an
        # SLA clock ends up an hour wrong twice a year, and most of this product is date
        # logic.
        datetime: postgresql.TIMESTAMP(timezone=True),
        dict[str, Any]: postgresql.JSONB,
        # Postgres text and varchar perform identically, and a length limit invented at
        # design time is a migration later.
        str: Text,
    }


class UUIDPrimaryKey:
    """A UUIDv7 primary key, generated in the application (ADR-0002)."""

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)


class Timestamped:
    """``created_at`` and ``updated_at``, tz-aware, defaulted by the database."""

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )


class TenantScoped:
    """``tenant_id``, on every tenant-owned table (rule 1).

    The foreign key resolves once the ``tenancy`` module defines ``tenants``. It is
    declared here rather than left as a bare UUID column with a promise, because the
    promise is the part that does not get kept.

    ``ON DELETE CASCADE`` serves tenant teardown, which is the one hard delete
    docs/conventions/database.md permits.
    """

    @declared_attr
    def tenant_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            ForeignKey(f"{TENANT_TABLE}.id", ondelete="CASCADE"),
            nullable=False,
        )


class Integratable:
    """``source``, ``external_id``, ``synced_at`` — present from day one.

    docs/conventions/database.md: every table that could ever receive a row from an
    outside system carries these, even while it is manual-only. It is what makes every
    future connector an idempotent upsert against a table that already exists, so no
    migration is ever "the integration migration".

    Pair with :func:`integration_unique` for the ``(tenant_id, source, external_id)``
    constraint that makes the upsert idempotent.
    """

    source: Mapped[str] = mapped_column(nullable=False, server_default=text(f"'{DEFAULT_SOURCE}'"))
    external_id: Mapped[str | None] = mapped_column(default=None)
    synced_at: Mapped[datetime | None] = mapped_column(default=None)


def tenant_index(table_name: str, *columns: str, unique: bool = False) -> Index:
    """A composite index with ``tenant_id`` leading.

    ``tenant_id`` is always the first column (docs/conventions/database.md). A plan
    that filters on tenant last is a performance bug waiting for the largest customer,
    and it is invisible until that customer arrives.

    Raises:
        ValueError: if no columns are given, or if ``tenant_id`` is passed explicitly —
            it is always added, and passing it invites putting it second.
    """
    if not columns:
        raise ValueError("a composite index needs at least one column besides tenant_id")
    if TENANT_ID_COLUMN in columns:
        raise ValueError(f"do not pass {TENANT_ID_COLUMN!r}; tenant_index always puts it first")
    _validate_identifier(table_name, what="table name")
    for name in columns:
        _validate_identifier(name, what="column name")
    prefix = "uq" if unique else "ix"
    index_name = f"{prefix}_{table_name}__{TENANT_ID_COLUMN}_{'_'.join(columns)}"
    return Index(index_name, TENANT_ID_COLUMN, *columns, unique=unique)


def integration_unique(table_name: str) -> UniqueConstraint:
    """The ``(tenant_id, source, external_id)`` uniqueness a connector upsert needs."""
    _validate_identifier(table_name, what="table name")
    return UniqueConstraint(
        TENANT_ID_COLUMN,
        "source",
        "external_id",
        name=f"uq_{table_name}__{TENANT_ID_COLUMN}_source_external_id",
    )


def status_check(table_name: str, column_name: str, allowed: Sequence[str]) -> CheckConstraint:
    """A ``CHECK`` constraint restricting a status column to ``allowed``.

    Status fields are text with a check, never a Postgres enum
    (docs/conventions/database.md). This product will grow states, and adding one must
    be a constraint change rather than a type migration — altering an enum under load
    is painful in a way that altering a check constraint is not.
    """
    if not allowed:
        raise ValueError("a status check needs at least one allowed value")
    _validate_identifier(table_name, what="table name")
    _validate_identifier(column_name, what="column name")
    # Built through the expression language, so the values are rendered as literals by
    # the DDL compiler rather than pasted into a string.
    return CheckConstraint(
        column(column_name).in_(list(allowed)),
        name=f"ck_{table_name}__{column_name}_valid",
    )
