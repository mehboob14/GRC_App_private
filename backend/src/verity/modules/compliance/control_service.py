"""The tenant's working control library: adopt, list, author, edit, retire.

Every state change here writes an audit row on the caller's session, inside the
caller's transaction (rule 5). Nothing is hard-deleted (rule 6): a control is
retired with ``disable``, which records who did it and why.

Template text is **copied** into the tenant's control, never referenced. A
tenant edits its own wording, and a later content-pack update must not silently
rewrite what an auditor already reviewed.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Final

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.modules.audit.service import Actor, AuditService, audit_service
from verity.modules.compliance.models import (
    Control,
    ControlRequirement,
    ControlTemplate,
    Requirement,
    TemplateRequirementMap,
)
from verity.shared.ids import uuid7

_CONTROL_SNAPSHOT: Final = (
    "id",
    "code",
    "name",
    "category",
    "control_type",
    "control_sub_type",
    "status",
    "owner_membership_id",
    "origin",
    "disabled_at",
    "disabled_reason",
)


@dataclass(frozen=True, slots=True)
class ControlView:
    """A control plus the criteria it satisfies and its owner's name.

    The criteria travel with the row because the Controls table shows them per
    control; fetching them per row would be an N+1 on a 114-row list.
    """

    id: uuid.UUID
    code: str
    name: str
    description: str
    implementation_guidance: str | None
    category: str
    control_type: str | None
    control_sub_type: str | None
    status: str
    origin: str
    owner_membership_id: uuid.UUID | None
    owner_name: str | None
    disabled_at: datetime | None
    disabled_reason: str | None
    template_id: uuid.UUID | None
    requirement_keys: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class AdoptionResult:
    """What ``instantiate_library`` did. ``created`` counts controls actually
    inserted — a second run reports zero rather than duplicating the library."""

    created: int
    already_present: int
    mappings_created: int


class ControlService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service

    # -- adoption ----------------------------------------------------------------

    async def instantiate_library(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        requirement_ids: list[uuid.UUID] | None = None,
    ) -> AdoptionResult:
        """Copy the shipped templates into this tenant's library.

        Idempotent on ``(tenant_id, template_id)``: adopting twice adds nothing,
        which is what makes this safe to call from signup, from a re-scope, and
        from an operator's hand.

        ``requirement_ids`` narrows adoption to the templates that satisfy those
        criteria — the scoping path. ``None`` adopts the whole library.
        """
        templates = await self._templates_for(session, requirement_ids)
        existing = await session.execute(
            select(Control.template_id).where(
                Control.tenant_id == tenant_id, Control.template_id.is_not(None)
            )
        )
        already = {row[0] for row in existing}

        crosswalk = await self._crosswalk(session, [t.id for t in templates])

        created = 0
        mappings = 0
        for template in templates:
            if template.id in already:
                continue
            control = Control(
                id=uuid7(),
                tenant_id=tenant_id,
                template_id=template.id,
                code=template.code,
                name=template.name,
                description=template.description,
                implementation_guidance=template.implementation_guidance,
                category=template.category,
                control_type=template.control_type,
                control_sub_type=template.control_sub_type,
                status="not_started",
                origin="template",
            )
            session.add(control)
            await session.flush([control])
            created += 1

            for requirement_id in crosswalk.get(template.id, []):
                session.add(
                    ControlRequirement(
                        id=uuid7(),
                        tenant_id=tenant_id,
                        control_id=control.id,
                        requirement_id=requirement_id,
                    )
                )
                mappings += 1

        if created:
            # One audit row for the adoption, not 114: the event is "the library
            # was instantiated", and the controls it created are themselves rows.
            await self._audit.record(
                session,
                action="create",
                object_type="control_library",
                object_id=tenant_id,
                actor=actor,
                tenant_id=tenant_id,
                before=None,
                after={"controls_created": created, "mappings_created": mappings},
            )

        return AdoptionResult(
            created=created, already_present=len(already), mappings_created=mappings
        )

    async def _templates_for(
        self, session: AsyncSession, requirement_ids: list[uuid.UUID] | None
    ) -> list[ControlTemplate]:
        statement = select(ControlTemplate)
        if requirement_ids is not None:
            statement = statement.where(
                ControlTemplate.id.in_(
                    select(TemplateRequirementMap.template_id).where(
                        TemplateRequirementMap.requirement_id.in_(requirement_ids)
                    )
                )
            )
        result = await session.execute(statement.order_by(ControlTemplate.code))
        return list(result.scalars())

    async def _crosswalk(
        self, session: AsyncSession, template_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[uuid.UUID]]:
        if not template_ids:
            return {}
        result = await session.execute(
            select(TemplateRequirementMap.template_id, TemplateRequirementMap.requirement_id).where(
                TemplateRequirementMap.template_id.in_(template_ids)
            )
        )
        crosswalk: dict[uuid.UUID, list[uuid.UUID]] = {}
        for template_id, requirement_id in result:
            crosswalk.setdefault(template_id, []).append(requirement_id)
        return crosswalk

    # -- reads --------------------------------------------------------------------

    async def list_controls(  # noqa: PLR0913 — one argument per documented filter
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        status: str | None = None,
        category: str | None = None,
        control_type: str | None = None,
        control_sub_type: str | None = None,
        owner_membership_id: uuid.UUID | None = None,
        include_disabled: bool = False,
        search: str | None = None,
    ) -> list[ControlView]:
        statement = select(Control).where(Control.tenant_id == tenant_id)
        if not include_disabled:
            statement = statement.where(Control.disabled_at.is_(None))
        if status is not None:
            statement = statement.where(Control.status == status)
        if category is not None:
            statement = statement.where(Control.category == category)
        if control_type is not None:
            statement = statement.where(Control.control_type == control_type)
        if control_sub_type is not None:
            statement = statement.where(Control.control_sub_type == control_sub_type)
        if owner_membership_id is not None:
            statement = statement.where(Control.owner_membership_id == owner_membership_id)
        if search:
            statement = statement.where(
                func.lower(Control.name).like(f"%{search.strip().lower()}%")
            )

        controls = list((await session.execute(statement.order_by(Control.code))).scalars())
        keys = await self._requirement_keys(session, tenant_id)
        owners = await self._owner_names(session, tenant_id)
        return [self._view(control, keys, owners) for control in controls]

    async def get_control(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, control_id: uuid.UUID
    ) -> ControlView:
        control = await self._load(session, tenant_id, control_id)
        keys = await self._requirement_keys(session, tenant_id)
        owners = await self._owner_names(session, tenant_id)
        return self._view(control, keys, owners)

    async def _requirement_keys(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, list[str]]:
        """Every control's mapped criteria in one query — the table shows them
        per row, and a per-row fetch would be an N+1 across the whole library."""
        result = await session.execute(
            select(ControlRequirement.control_id, Requirement.requirement_key)
            .join(Requirement, Requirement.id == ControlRequirement.requirement_id)
            .where(ControlRequirement.tenant_id == tenant_id)
            .order_by(Requirement.code)
        )
        keys: dict[uuid.UUID, list[str]] = {}
        for control_id, requirement_key in result:
            keys.setdefault(control_id, []).append(requirement_key)
        return keys

    async def _owner_names(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        """Owner display names, resolved through IAM's *service* — never its
        models or repository (rule 4, enforced by import-linter).

        Imported inside the function because the two modules would otherwise
        import each other at module load; the call itself is the sanctioned
        service-to-service direction.
        """
        from verity.modules.iam.service import iam_service  # noqa: PLC0415

        members = await iam_service.list_members(session, tenant_id=tenant_id)
        return {member.membership_id: member.full_name for member in members}

    @staticmethod
    def _view(
        control: Control,
        keys: dict[uuid.UUID, list[str]],
        owners: dict[uuid.UUID, str],
    ) -> ControlView:
        return ControlView(
            id=control.id,
            code=control.code,
            name=control.name,
            description=control.description,
            implementation_guidance=control.implementation_guidance,
            category=control.category,
            control_type=control.control_type,
            control_sub_type=control.control_sub_type,
            status=control.status,
            origin=control.origin,
            owner_membership_id=control.owner_membership_id,
            owner_name=(
                owners.get(control.owner_membership_id) if control.owner_membership_id else None
            ),
            disabled_at=control.disabled_at,
            disabled_reason=control.disabled_reason,
            template_id=control.template_id,
            requirement_keys=keys.get(control.id, []),
        )

    async def _load(
        self, session: AsyncSession, tenant_id: uuid.UUID, control_id: uuid.UUID
    ) -> Control:
        control = await session.get(Control, control_id)
        if control is None or control.tenant_id != tenant_id:
            raise NotFound(detail=f"control {control_id}")
        return control

    # -- writes --------------------------------------------------------------------

    async def create_custom_control(  # noqa: PLR0913 — the control's own fields
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        code: str,
        name: str,
        description: str,
        category: str,
        control_type: str | None = None,
        control_sub_type: str | None = None,
        implementation_guidance: str | None = None,
        owner_membership_id: uuid.UUID | None = None,
        requirement_ids: list[uuid.UUID] | None = None,
    ) -> ControlView:
        clash = await session.execute(
            select(Control.id).where(Control.tenant_id == tenant_id, Control.code == code.strip())
        )
        if clash.first() is not None:
            raise Conflict(detail=f"a control with code {code!r} already exists")

        control = Control(
            id=uuid7(),
            tenant_id=tenant_id,
            template_id=None,
            code=code.strip(),
            name=name.strip(),
            description=description.strip(),
            implementation_guidance=implementation_guidance,
            category=category,
            control_type=control_type,
            control_sub_type=control_sub_type,
            status="not_started",
            owner_membership_id=owner_membership_id,
            origin="custom",
        )
        session.add(control)
        await session.flush([control])

        await self._map_requirements(session, tenant_id, control.id, requirement_ids or [])
        await self._audit.record(
            session,
            action="create",
            object_type="control",
            object_id=control.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after=AuditService.snapshot(control, fields=_CONTROL_SNAPSHOT),
        )
        return await self.get_control(session, tenant_id=tenant_id, control_id=control.id)

    async def update_control(  # noqa: PLR0913 — the editable fields, no more
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        control_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        implementation_guidance: str | None = None,
        category: str | None = None,
        control_type: str | None = None,
        control_sub_type: str | None = None,
        status: str | None = None,
        owner_membership_id: uuid.UUID | None = None,
        clear_owner: bool = False,
        requirement_ids: list[uuid.UUID] | None = None,
    ) -> ControlView:
        control = await self._load(session, tenant_id, control_id)
        if control.disabled_at is not None:
            raise InvalidInput(detail="a disabled control cannot be edited; re-enable it first")

        before = AuditService.snapshot(control, fields=_CONTROL_SNAPSHOT)
        for attribute, value in (
            ("name", name),
            ("description", description),
            ("implementation_guidance", implementation_guidance),
            ("category", category),
            ("control_type", control_type),
            ("control_sub_type", control_sub_type),
            ("status", status),
        ):
            if value is not None:
                setattr(control, attribute, value)
        if clear_owner:
            control.owner_membership_id = None
        elif owner_membership_id is not None:
            control.owner_membership_id = owner_membership_id

        if requirement_ids is not None:
            await self._map_requirements(
                session, tenant_id, control.id, requirement_ids, replace=True
            )

        after = AuditService.snapshot(control, fields=_CONTROL_SNAPSHOT)
        if before != after or requirement_ids is not None:
            await self._audit.record(
                session,
                action="update",
                object_type="control",
                object_id=control.id,
                actor=actor,
                tenant_id=tenant_id,
                before=before,
                after=after,
            )
        return await self.get_control(session, tenant_id=tenant_id, control_id=control.id)

    async def disable_control(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        control_id: uuid.UUID,
        reason: str,
    ) -> ControlView:
        """Retire a control with a recorded justification (rule 6).

        The reason is required by the signature and by the table's CHECK, so a
        control cannot be retired without one at either layer.
        """
        justification = reason.strip()
        if not justification:
            raise InvalidInput(detail="a reason is required to disable a control")

        control = await self._load(session, tenant_id, control_id)
        if control.disabled_at is not None:
            raise Conflict(detail="control is already disabled")

        before = AuditService.snapshot(control, fields=_CONTROL_SNAPSHOT)
        control.disabled_at = datetime.now(UTC)
        control.disabled_reason = justification
        await self._audit.record(
            session,
            action="update",
            object_type="control",
            object_id=control.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(control, fields=_CONTROL_SNAPSHOT),
        )
        return await self.get_control(session, tenant_id=tenant_id, control_id=control.id)

    async def enable_control(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        control_id: uuid.UUID,
    ) -> ControlView:
        control = await self._load(session, tenant_id, control_id)
        if control.disabled_at is None:
            raise Conflict(detail="control is not disabled")

        before = AuditService.snapshot(control, fields=_CONTROL_SNAPSHOT)
        control.disabled_at = None
        control.disabled_reason = None
        await self._audit.record(
            session,
            action="update",
            object_type="control",
            object_id=control.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(control, fields=_CONTROL_SNAPSHOT),
        )
        return await self.get_control(session, tenant_id=tenant_id, control_id=control.id)

    async def _map_requirements(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        control_id: uuid.UUID,
        requirement_ids: list[uuid.UUID],
        *,
        replace: bool = False,
    ) -> None:
        current = await session.execute(
            select(ControlRequirement).where(
                ControlRequirement.tenant_id == tenant_id,
                ControlRequirement.control_id == control_id,
            )
        )
        rows = {row.requirement_id: row for row in current.scalars()}

        if replace:
            for requirement_id, row in rows.items():
                if requirement_id not in requirement_ids:
                    await session.delete(row)

        for requirement_id in requirement_ids:
            if requirement_id not in rows:
                session.add(
                    ControlRequirement(
                        id=uuid7(),
                        tenant_id=tenant_id,
                        control_id=control_id,
                        requirement_id=requirement_id,
                    )
                )


control_service = ControlService()
