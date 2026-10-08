"""Tenant-defined extra fields on a record (the ``custom_field_definitions`` table).

A primitive, like ``links``: it stores the *definition* of a field, and the
module that owns the record stores the value, in a ``custom_fields`` JSONB column
on that record's own row. Values beside the record they belong to means a read of
the record is still one row, and a tenant that defines no fields pays nothing.

Definitions are archived, never deleted (rule 6): a value written last year must
stay readable after somebody decides the field is no longer collected.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Final

from sqlalchemy import CheckConstraint, UniqueConstraint, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.elements import conv

from verity.db.base import (
    Base,
    TenantScoped,
    Timestamped,
    UUIDPrimaryKey,
    status_check,
    tenant_index,
)

# The records that can carry custom fields. A module adds itself here and to the
# check constraint, in a migration — a typo is then a constraint violation rather
# than a field nothing renders.
FIELD_OBJECT_TYPES: Final[tuple[str, ...]] = ("asset", "vulnerability", "risk")

# Deliberately small. Every type here is one HTML control and one JSON scalar;
# anything richer (a person, a linked record, a file) is a real column on the
# owning table, not a loose value in a blob.
FIELD_TYPES: Final[tuple[str, ...]] = (
    "text",
    "textarea",
    "number",
    "date",
    "select",
    "checkbox",
)


class CustomFieldDefinition(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One extra field a tenant collects on a kind of record."""

    __tablename__ = "custom_field_definitions"

    object_type: Mapped[str]
    #: Stable identifier for the value in the record's ``custom_fields`` blob.
    #: Immutable once created — the label is what a person renames.
    key: Mapped[str]
    label: Mapped[str]
    field_type: Mapped[str] = mapped_column(default="text")
    options: Mapped[list[Any]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    help_text: Mapped[str | None] = mapped_column(default=None)
    required: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    position: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    archived_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("custom_field_definitions", "object_type", FIELD_OBJECT_TYPES),
        status_check("custom_field_definitions", "field_type", FIELD_TYPES),
        # A choice field with nothing to choose is a field nobody can fill in.
        CheckConstraint(
            "field_type <> 'select' OR jsonb_array_length(options) > 0",
            name=conv("ck_custom_field_definitions__select_has_options"),
        ),
        UniqueConstraint(
            "tenant_id", "object_type", "key", name="uq_custom_field_definitions__key"
        ),
        tenant_index("custom_field_definitions", "object_type"),
    )

    def __repr__(self) -> str:
        return (
            f"CustomFieldDefinition(id={self.id!r}, "
            f"object_type={self.object_type!r}, key={self.key!r})"
        )
