"""Custom field definitions, and the validation of the values written against them.

Storage and validation only. Defining a field *is* a state change, but the audit
row belongs to the module whose settings screen made it — the same arrangement
``links`` uses — so this service takes no dependency on ``audit`` and returns
domain dataclasses, never ORM rows.

``clean`` is the whole point of the module: whatever a form posts, what reaches
the record is a dict whose keys are fields this tenant actually defined and whose
values are the type the definition promised. A blob nobody validates becomes a
second schema with no constraints, and then a report nobody can run.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.modules.customfields.models import (
    FIELD_OBJECT_TYPES,
    FIELD_TYPES,
    CustomFieldDefinition,
)
from verity.shared.ids import uuid7

_MAX_TEXT = 2000
_MAX_LABEL = 80
_MAX_OPTIONS = 50
_GONE = "That field no longer exists."


@dataclass(frozen=True, slots=True)
class FieldDefinition:
    id: uuid.UUID
    object_type: str
    key: str
    label: str
    field_type: str
    options: list[str]
    help_text: str | None
    required: bool
    position: int
    archived: bool


@dataclass(frozen=True, slots=True)
class FieldInput:
    label: str
    field_type: str = "text"
    options: tuple[str, ...] = ()
    help_text: str | None = None
    required: bool = False
    position: int = 0


def _slug(label: str) -> str:
    """A key a person never types and never sees, derived from the first label."""
    out = "".join(ch.lower() if ch.isalnum() else "_" for ch in label.strip())
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_")[:48] or "field"


def _view(row: CustomFieldDefinition) -> FieldDefinition:
    return FieldDefinition(
        id=row.id,
        object_type=row.object_type,
        key=row.key,
        label=row.label,
        field_type=row.field_type,
        options=[str(o) for o in (row.options or [])],
        help_text=row.help_text,
        required=row.required,
        position=row.position,
        archived=row.archived_at is not None,
    )


class CustomFieldService:
    async def definitions(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        object_type: str,
        include_archived: bool = False,
    ) -> list[FieldDefinition]:
        """Every field defined for this kind of record, in display order."""
        self._check_object_type(object_type)
        stmt = (
            select(CustomFieldDefinition)
            .where(CustomFieldDefinition.tenant_id == tenant_id)
            .where(CustomFieldDefinition.object_type == object_type)
            .order_by(CustomFieldDefinition.position, CustomFieldDefinition.created_at)
        )
        if not include_archived:
            stmt = stmt.where(CustomFieldDefinition.archived_at.is_(None))
        return [_view(r) for r in (await session.execute(stmt)).scalars()]

    async def create(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        object_type: str,
        data: FieldInput,
    ) -> FieldDefinition:
        self._check_object_type(object_type)
        label, field_type, options = self._clean_definition(data)
        key = _slug(label)
        taken = {
            r.key
            for r in (
                await session.execute(
                    select(CustomFieldDefinition).where(
                        CustomFieldDefinition.tenant_id == tenant_id,
                        CustomFieldDefinition.object_type == object_type,
                    )
                )
            ).scalars()
        }
        if key in taken:
            # Two fields called "Owner" are a person's problem to name, not ours
            # to silently merge: the second becomes owner_2 and keeps its label.
            suffix = 2
            while f"{key}_{suffix}" in taken:
                suffix += 1
            key = f"{key}_{suffix}"
        row = CustomFieldDefinition(
            id=uuid7(),
            tenant_id=tenant_id,
            object_type=object_type,
            key=key,
            label=label,
            field_type=field_type,
            options=list(options),
            help_text=(data.help_text or "").strip() or None,
            required=bool(data.required),
            position=int(data.position),
        )
        session.add(row)
        await session.flush([row])
        return _view(row)

    async def update(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        field_id: uuid.UUID,
        data: FieldInput,
    ) -> FieldDefinition:
        """Rename, re-order, re-word. The key and the type never change.

        Changing the type would leave every value already written in the old
        shape, so the answer to "this should have been a date" is a new field.
        """
        row = await self._load(session, tenant_id, field_id)
        label, field_type, options = self._clean_definition(data)
        if field_type != row.field_type:
            raise Conflict(
                "A field's type cannot change once it exists. Add a new field instead.",
                detail=f"custom field {field_id} is {row.field_type}, asked for {field_type}",
            )
        row.label = label
        row.options = list(options)
        row.help_text = (data.help_text or "").strip() or None
        row.required = bool(data.required)
        row.position = int(data.position)
        await session.flush([row])
        return _view(row)

    async def set_archived(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        field_id: uuid.UUID,
        archived: bool,
    ) -> FieldDefinition:
        """Stop collecting a field, or start again. Values already written stay."""
        row = await self._load(session, tenant_id, field_id)
        row.archived_at = datetime.now(UTC) if archived else None
        await session.flush([row])
        return _view(row)

    async def clean(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        object_type: str,
        values: dict[str, Any] | None,
        previous: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Validate a form's custom values into what may be stored on the record.

        ``previous`` carries forward what an archived field already holds: the
        form no longer renders it, so a save must not be read as clearing it.
        """
        defs = await self.definitions(
            session, tenant_id=tenant_id, object_type=object_type, include_archived=True
        )
        if not defs:
            return {}
        active = {d.key: d for d in defs if not d.archived}
        supplied = dict(values or {})
        unknown = set(supplied) - {d.key for d in defs}
        if unknown:
            raise InvalidInput(
                "That form sent a field this workspace does not collect.",
                detail=f"unknown custom fields {sorted(unknown)} on {object_type}",
            )
        out: dict[str, Any] = {
            k: v for k, v in (previous or {}).items() if k not in active and k not in supplied
        }
        for key, definition in active.items():
            raw = supplied.get(key, (previous or {}).get(key))
            value = self._coerce(definition, raw)
            if value is None:
                if definition.required:
                    raise InvalidInput(
                        f"{definition.label} is required.",
                        detail=f"custom field {key} missing on {object_type}",
                    )
                continue
            out[key] = value
        return out

    # -- internals -------------------------------------------------------------

    @staticmethod
    def _check_object_type(object_type: str) -> None:
        if object_type not in FIELD_OBJECT_TYPES:
            raise InvalidInput(
                "That is not a record type that carries custom fields.",
                detail=f"object_type {object_type!r}",
            )

    async def _load(
        self, session: AsyncSession, tenant_id: uuid.UUID, field_id: uuid.UUID
    ) -> CustomFieldDefinition:
        row = await session.get(CustomFieldDefinition, field_id, populate_existing=True)
        if row is None or row.tenant_id != tenant_id:
            raise NotFound(_GONE, detail=f"custom field {field_id}")
        return row

    @staticmethod
    def _clean_definition(data: FieldInput) -> tuple[str, str, list[str]]:
        label = (data.label or "").strip()
        if not label:
            raise InvalidInput("Give the field a name.", detail="custom field with no label")
        if len(label) > _MAX_LABEL:
            raise InvalidInput(
                f"Keep the field name under {_MAX_LABEL} characters.",
                detail=f"custom field label of {len(label)}",
            )
        if data.field_type not in FIELD_TYPES:
            raise InvalidInput(
                "That is not a field type this platform offers.",
                detail=f"field_type {data.field_type!r}",
            )
        options: list[str] = []
        seen: set[str] = set()
        for option in data.options:
            text_value = str(option).strip()
            if not text_value or text_value in seen:
                continue
            seen.add(text_value)
            options.append(text_value)
        if data.field_type == "select":
            if not options:
                raise InvalidInput(
                    "A choice field needs at least one choice.",
                    detail="select custom field with no options",
                )
            if len(options) > _MAX_OPTIONS:
                raise InvalidInput(
                    f"Keep a choice field under {_MAX_OPTIONS} choices.",
                    detail=f"select custom field with {len(options)} options",
                )
        else:
            options = []
        return label, data.field_type, options

    @staticmethod
    def _coerce(definition: FieldDefinition, raw: object) -> object | None:
        """One value, as the definition promised it, or None for "not filled in"."""
        if raw is None:
            return None
        if definition.field_type == "checkbox":
            return _as_bool(definition, raw)
        if isinstance(raw, str) and not raw.strip():
            return None
        if definition.field_type == "number":
            return _as_number(definition, raw)
        if definition.field_type == "date":
            return _as_date(definition, raw)
        return _as_text(definition, raw)


def _as_bool(definition: FieldDefinition, raw: object) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str) and raw.lower() in {"true", "false"}:
        return raw.lower() == "true"
    raise InvalidInput(
        f"{definition.label} is a yes or no field.",
        detail=f"custom field {definition.key} got {type(raw).__name__}",
    )


def _as_number(definition: FieldDefinition, raw: object) -> int | float:
    if not isinstance(raw, int | float | str):
        raise InvalidInput(
            f"{definition.label} takes a number.",
            detail=f"custom field {definition.key} got {type(raw).__name__}",
        )
    try:
        number = float(raw)
    except ValueError as exc:
        raise InvalidInput(
            f"{definition.label} takes a number.",
            detail=f"custom field {definition.key} got {raw!r}",
        ) from exc
    return int(number) if number.is_integer() else number


def _as_date(definition: FieldDefinition, raw: object) -> str:
    try:
        return date.fromisoformat(str(raw)).isoformat()
    except ValueError as exc:
        raise InvalidInput(
            f"{definition.label} takes a date.",
            detail=f"custom field {definition.key} got {raw!r}",
        ) from exc


def _as_text(definition: FieldDefinition, raw: object) -> str:
    """Free text, or one of the choices when the field is a choice field."""
    value = str(raw).strip()
    if definition.field_type == "select":
        if value not in definition.options:
            raise InvalidInput(
                f"{value} is not one of the choices for {definition.label}.",
                detail=f"custom field {definition.key} got {value!r}",
            )
        return value
    if len(value) > _MAX_TEXT:
        raise InvalidInput(
            f"Keep {definition.label} under {_MAX_TEXT} characters.",
            detail=f"custom field {definition.key} of {len(value)}",
        )
    return value


custom_field_service = CustomFieldService()
