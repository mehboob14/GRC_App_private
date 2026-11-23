"""Owner functions mapped to members, and owners proposed onto controls from them (OW-1 to OW-4).

Applying owners goes through the compliance service, one audited change per control. An owner a
person already set is kept unless the caller asks otherwise.
"""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import InvalidInput
from verity.modules.audit.service import Actor, AuditService, audit_service
from verity.modules.compliance.control_service import control_service
from verity.modules.iam.service import iam_service
from verity.modules.onboarding.models import OwnerFunction
from verity.modules.onboarding.owner_functions import FUNCTION_KEYS, FUNCTIONS, function_for
from verity.shared.ids import uuid7

AUDITOR_CONTROL: Final = "GOV-13"
WARN_SHARE: Final = 0.5


@dataclass(frozen=True, slots=True)
class FunctionView:
    key: str
    label: str
    membership_id: uuid.UUID | None
    member_name: str | None
    controls: int
    """Controls whose owner this function proposes."""


@dataclass(frozen=True, slots=True)
class OwnershipView:
    functions: list[FunctionView]
    controls_total: int
    controls_unowned: int
    would_change: int
    """Controls with no owner that a mapped function would now fill."""
    warnings: list[str] = field(default_factory=list)
    reassign: list[str] = field(default_factory=list)
    """Work a member who is no longer active leaves behind (OW-7). Nothing moves silently."""


class OwnershipService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service

    async def _assigned(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[str, OwnerFunction]:
        rows = (
            await session.execute(select(OwnerFunction).where(OwnerFunction.tenant_id == tenant_id))
        ).scalars()
        return {row.function_key: row for row in rows}

    async def view(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> OwnershipView:
        assigned = await self._assigned(session, tenant_id)
        members = {
            m.membership_id: m for m in await iam_service.list_members(session, tenant_id=tenant_id)
        }
        controls = await control_service.owners_by_code(session, tenant_id=tenant_id)
        per_function = Counter(function_for(code) for _, code, _ in controls)
        mapping = {k: row.membership_id for k, row in assigned.items() if row.membership_id}
        would_change = sum(
            1
            for _, code, owner in controls
            if owner is None and mapping.get(function_for(code) or "")
        )
        functions = [
            FunctionView(
                key=key,
                label=label,
                membership_id=mapping.get(key),
                member_name=members[mapping[key]].full_name
                if mapping.get(key) in members
                else None,
                controls=per_function.get(key, 0),
            )
            for key, label in FUNCTIONS
        ]
        return OwnershipView(
            functions=functions,
            controls_total=len(controls),
            controls_unowned=sum(1 for _, _, owner in controls if owner is None),
            would_change=would_change,
            warnings=self._warnings(controls, members),
            reassign=await self._reassign(session, tenant_id, assigned, members, controls),
        )

    @staticmethod
    async def _reassign(
        session: AsyncSession,
        tenant_id: uuid.UUID,
        assigned: Mapping[str, OwnerFunction],
        members: Mapping[uuid.UUID, Any],
        controls: list[tuple[uuid.UUID, str, uuid.UUID | None]],
    ) -> list[str]:
        from verity.modules.documents.service import document_service  # noqa: PLC0415

        gone = {mid for mid, m in members.items() if m.status != "active"}
        if not gone:
            return []
        documents = await document_service.owned_counts(session, tenant_id=tenant_id)
        labels = dict(FUNCTIONS)
        out: list[str] = []
        for key, row in assigned.items():
            if row.membership_id in gone:
                out.append(f"{labels.get(key, key)} has no active member. Name someone new.")
        for mid in sorted(gone, key=str):
            owned = sum(1 for _, _, owner in controls if owner == mid)
            docs = documents.get(mid, 0)
            if owned or docs:
                name = members[mid].full_name
                out.append(
                    f"{name} is no longer active: {owned} controls and {docs} documents "
                    "need a new owner."
                )
        return out

    @staticmethod
    def _warnings(
        controls: list[tuple[uuid.UUID, str, uuid.UUID | None]], members: Mapping[uuid.UUID, object]
    ) -> list[str]:
        """The internal audit owner should not own most of what it audits (OW-4)."""
        auditor = next((owner for _, code, owner in controls if code == AUDITOR_CONTROL), None)
        if auditor is None or not controls:
            return []
        owned = sum(1 for _, _, owner in controls if owner == auditor)
        if owned / len(controls) <= WARN_SHARE:
            return []
        name = getattr(members.get(auditor), "full_name", "One person")
        return [
            f"{name} owns the internal audit and {owned} of the {len(controls)} controls "
            "it checks. Most small companies ask an outside reviewer to do the internal audit."
        ]

    async def assign(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        function_key: str,
        membership_id: uuid.UUID | None,
    ) -> None:
        if function_key not in FUNCTION_KEYS:
            raise InvalidInput("That owner function does not exist.", detail=function_key)
        if membership_id is not None:
            members = {
                m.membership_id: m
                for m in await iam_service.list_members(session, tenant_id=tenant_id)
            }
            member = members.get(membership_id)
            if member is None or member.status == "disabled":
                raise InvalidInput(
                    "Choose an active member of this workspace.", detail=f"member {membership_id}"
                )
        assigned = await self._assigned(session, tenant_id)
        row = assigned.get(function_key)
        before = {"membership_id": str(row.membership_id) if row and row.membership_id else None}
        if row is None:
            row = OwnerFunction(id=uuid7(), tenant_id=tenant_id, function_key=function_key)
            session.add(row)
        row.membership_id = membership_id
        await session.flush([row])
        await self._audit.record(
            session,
            action="update",
            object_type="owner_function",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after={
                "function": function_key,
                "membership_id": str(membership_id) if membership_id else None,
            },
        )

    async def apply(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor, keep_existing: bool
    ) -> int:
        """Give each control the member of its function. Returns how many controls changed."""
        mapping = {
            k: row.membership_id
            for k, row in (await self._assigned(session, tenant_id)).items()
            if row.membership_id
        }
        changed = 0
        for control_id, code, owner in await control_service.owners_by_code(
            session, tenant_id=tenant_id
        ):
            member = mapping.get(function_for(code) or "")
            if member is None or owner == member or (owner is not None and keep_existing):
                continue
            await control_service.update_control(
                session,
                tenant_id=tenant_id,
                actor=actor,
                control_id=control_id,
                owner_membership_id=member,
            )
            changed += 1
        return changed

    async def _active(self, session: AsyncSession, tenant_id: uuid.UUID) -> set[uuid.UUID]:
        return {
            m.membership_id
            for m in await iam_service.list_members(session, tenant_id=tenant_id)
            if m.status == "active"
        }

    async def assigned_count(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> int:
        """Functions held by an active member: a disabled holder leaves the function open."""
        active = await self._active(session, tenant_id)
        return sum(
            1
            for row in (await self._assigned(session, tenant_id)).values()
            if row.membership_id in active
        )

    async def function_members(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> dict[str, uuid.UUID]:
        """``{function: member}`` for the functions an active member holds (defaults for other
        modules: nothing is given to someone who has left)."""
        active = await self._active(session, tenant_id)
        return {
            k: row.membership_id
            for k, row in (await self._assigned(session, tenant_id)).items()
            if row.membership_id in active
        }


ownership_service = OwnershipService()
