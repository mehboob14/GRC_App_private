"""Scope items shared by every framework, with in or out decided per framework.

Guided onboarding SC-0 and SC-2 (decision D-6, checked against AICPA and ISO accreditation
sources on 2026-11-21, ``research_notes/Guided onboarding plan/shared_scope_check.md``):

* one list of items for the workspace; in or out, and why, is recorded per engagement;
* an item out of scope needs a reason (CHECK and here);
* changing a decision asks what it means for that framework: inside a SOC 2 Type 2 period it is a
  change the description has to disclose; for a certified ISO scope the certification body has to
  review it. The product says so; it never decides for the person;
* items are retired with a reason, never deleted; every change is audited.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.modules.audit.service import Actor, AuditService, audit_service
from verity.modules.compliance.engagement_service import engagement_service
from verity.modules.compliance.models import (
    SCOPE_ITEM_KINDS,
    Engagement,
    Framework,
    FrameworkVersion,
    ScopeDecision,
    ScopeItem,
)
from verity.shared.ids import uuid7

NAME_MAX: Final = 200
REASON_MAX: Final = 1000

NOTICE_PERIOD: Final = (
    "This change falls inside your SOC 2 observation period. Your system description has to "
    "disclose it."
)
NOTICE_CERTIFICATION: Final = (
    "Tell your certification body. A change to a certified scope needs their review."
)


@dataclass(frozen=True, slots=True)
class OtherDecision:
    framework_code: str
    in_scope: bool


@dataclass(frozen=True, slots=True)
class ScopeItemView:
    id: uuid.UUID
    kind: str
    name: str
    origin: str
    in_scope: bool | None
    """This framework's decision; None until someone decides."""
    reason: str | None
    decided_at: datetime | None
    others: list[OtherDecision] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class DecisionResult:
    item: ScopeItemView
    notices: list[str]


def _clean(value: str | None, *, limit: int, what: str) -> str | None:
    text = (value or "").strip()
    if len(text) > limit:
        raise InvalidInput(f"Keep the {what} under {limit} characters.", detail=f"{what} too long")
    return text or None


class ScopeService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service

    async def _engagement(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, framework_code: str
    ) -> Engagement:
        engagement = await engagement_service.get(
            session, tenant_id=tenant_id, framework_code=framework_code
        )
        if engagement is None:
            raise Conflict(
                "Set up this framework's audit first, then decide what is in its scope.",
                detail=f"no engagement for {framework_code}",
            )
        return engagement

    async def _framework_codes(
        self, session: AsyncSession, engagement_ids: set[uuid.UUID]
    ) -> dict[uuid.UUID, str]:
        if not engagement_ids:
            return {}
        rows = await session.execute(
            select(Engagement.id, Framework.code)
            .join(FrameworkVersion, FrameworkVersion.id == Engagement.framework_version_id)
            .join(Framework, Framework.id == FrameworkVersion.framework_id)
            .where(Engagement.id.in_(engagement_ids))
        )
        return {row[0]: row[1] for row in rows.all()}

    async def _item(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, item_id: uuid.UUID
    ) -> ScopeItem:
        item = await session.get(ScopeItem, item_id)
        if item is None or item.tenant_id != tenant_id or item.retired_at is not None:
            raise NotFound("That scope item no longer exists.", detail=f"scope item {item_id}")
        return item

    async def list_items(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, framework_code: str
    ) -> list[ScopeItemView]:
        engagement = await engagement_service.get(
            session, tenant_id=tenant_id, framework_code=framework_code
        )
        items = list(
            (
                await session.execute(
                    select(ScopeItem)
                    .where(ScopeItem.tenant_id == tenant_id, ScopeItem.retired_at.is_(None))
                    .order_by(ScopeItem.kind, ScopeItem.name)
                )
            ).scalars()
        )
        decisions = list(
            (
                await session.execute(
                    select(ScopeDecision).where(
                        ScopeDecision.tenant_id == tenant_id,
                        ScopeDecision.scope_item_id.in_([i.id for i in items]),
                    )
                )
            ).scalars()
        )
        codes = await self._framework_codes(session, {d.engagement_id for d in decisions})
        out: list[ScopeItemView] = []
        for item in items:
            mine = next(
                (
                    d
                    for d in decisions
                    if d.scope_item_id == item.id
                    and engagement
                    and d.engagement_id == engagement.id
                ),
                None,
            )
            others = [
                OtherDecision(framework_code=codes[d.engagement_id], in_scope=d.in_scope)
                for d in decisions
                if d.scope_item_id == item.id
                and (engagement is None or d.engagement_id != engagement.id)
                and d.engagement_id in codes
            ]
            out.append(self._view(item, mine, others))
        return out

    @staticmethod
    def _view(
        item: ScopeItem, decision: ScopeDecision | None, others: list[OtherDecision]
    ) -> ScopeItemView:
        return ScopeItemView(
            id=item.id,
            kind=item.kind,
            name=item.name,
            origin=item.origin,
            in_scope=decision.in_scope if decision else None,
            reason=decision.reason if decision else None,
            decided_at=decision.decided_at if decision else None,
            others=others,
        )

    async def in_scope_for(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, ref_type: str
    ) -> dict[uuid.UUID, list[str]]:
        """For records of one type (asset, vendor, group): the frameworks whose current
        engagement holds a live scope item pointing at the record and decided in (SC-4)."""
        rows = await session.execute(
            select(ScopeItem.ref_id, FrameworkVersion.framework_id)
            .join(ScopeDecision, ScopeDecision.scope_item_id == ScopeItem.id)
            .join(Engagement, Engagement.id == ScopeDecision.engagement_id)
            .join(FrameworkVersion, FrameworkVersion.id == Engagement.framework_version_id)
            .where(
                ScopeItem.tenant_id == tenant_id,
                ScopeItem.ref_type == ref_type,
                ScopeItem.ref_id.is_not(None),
                ScopeItem.retired_at.is_(None),
                ScopeDecision.in_scope.is_(True),
                Engagement.is_current.is_(True),
            )
        )
        pairs = list(rows)
        if not pairs:
            return {}
        codes = dict(
            (
                await session.execute(
                    select(Framework.id, Framework.code).where(
                        Framework.id.in_({fid for _, fid in pairs})
                    )
                )
            ).tuples()
        )
        out: dict[uuid.UUID, list[str]] = {}
        for ref_id, fid in pairs:
            code = codes.get(fid)
            if ref_id is None or code is None:
                continue
            if code not in out.setdefault(ref_id, []):
                out[ref_id].append(code)
        return out

    async def add_item(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor, kind: str, name: str
    ) -> ScopeItem:
        if kind not in SCOPE_ITEM_KINDS:
            raise InvalidInput("Choose what kind of item this is.", detail=f"kind {kind!r}")
        cleaned = _clean(name, limit=NAME_MAX, what="name")
        if not cleaned:
            raise InvalidInput("Give the item a name.", detail="empty scope item name")
        item = ScopeItem(id=uuid7(), tenant_id=tenant_id, kind=kind, name=cleaned)
        session.add(item)
        await session.flush([item])
        await self._audit.record(
            session,
            action="create",
            object_type="scope_item",
            object_id=item.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"kind": kind, "name": cleaned},
        )
        return item

    @staticmethod
    def _notices(engagement: Engagement, framework_scope_model: str, today: date) -> list[str]:
        notices: list[str] = []
        if (
            engagement.audit_type == "type_2"
            and engagement.window_start is not None
            and engagement.window_end is not None
            and engagement.window_start <= today <= engagement.window_end
        ):
            notices.append(NOTICE_PERIOD)
        if framework_scope_model == "applicability" and engagement.assessor == "chosen":
            notices.append(NOTICE_CERTIFICATION)
        return notices

    async def decide(  # noqa: PLR0913 — who, which item, which framework, and the decision
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        membership_id: uuid.UUID,
        item_id: uuid.UUID,
        framework_code: str,
        in_scope: bool,
        reason: str | None,
    ) -> DecisionResult:
        item = await self._item(session, tenant_id=tenant_id, item_id=item_id)
        engagement = await self._engagement(
            session, tenant_id=tenant_id, framework_code=framework_code
        )
        cleaned = _clean(reason, limit=REASON_MAX, what="reason")
        if not in_scope and not cleaned:
            raise InvalidInput(
                "Say why this is out of scope. The reason is shown to your auditor.",
                detail="out of scope without a reason",
            )
        existing = (
            await session.execute(
                select(ScopeDecision).where(
                    ScopeDecision.tenant_id == tenant_id,
                    ScopeDecision.scope_item_id == item.id,
                    ScopeDecision.engagement_id == engagement.id,
                )
            )
        ).scalar_one_or_none()
        now = datetime.now(UTC)
        before = {"in_scope": existing.in_scope, "reason": existing.reason} if existing else None
        changed = existing is not None and existing.in_scope != in_scope
        if existing is None:
            existing = ScopeDecision(
                id=uuid7(),
                tenant_id=tenant_id,
                scope_item_id=item.id,
                engagement_id=engagement.id,
                in_scope=in_scope,
                reason=cleaned,
                decided_by_membership_id=membership_id,
                decided_at=now,
            )
            session.add(existing)
        else:
            existing.in_scope = in_scope
            existing.reason = cleaned
            existing.decided_by_membership_id = membership_id
            existing.decided_at = now
        await session.flush([existing])
        await self._audit.record(
            session,
            action="create" if before is None else "update",
            object_type="scope_decision",
            object_id=existing.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after={
                "scope_item_id": str(item.id),
                "framework": framework_code,
                "in_scope": in_scope,
                "reason": cleaned,
            },
        )
        framework = await self._scope_model(session, engagement)
        notices = self._notices(engagement, framework, now.date()) if changed else []
        return DecisionResult(item=self._view(item, existing, []), notices=notices)

    async def _scope_model(self, session: AsyncSession, engagement: Engagement) -> str:
        version = await session.get(FrameworkVersion, engagement.framework_version_id)
        framework = await session.get(Framework, version.framework_id) if version else None
        return framework.scope_model if framework else "categories"

    async def retire(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        item_id: uuid.UUID,
        reason: str,
    ) -> list[str]:
        """Retire an item from every framework's list. Returns what each framework it was in
        scope for has to do about it."""
        item = await self._item(session, tenant_id=tenant_id, item_id=item_id)
        cleaned = _clean(reason, limit=REASON_MAX, what="reason")
        if not cleaned:
            raise InvalidInput(
                "Say why you are removing this item.", detail="retire without reason"
            )
        decisions = list(
            (
                await session.execute(
                    select(ScopeDecision).where(
                        ScopeDecision.tenant_id == tenant_id,
                        ScopeDecision.scope_item_id == item.id,
                        ScopeDecision.in_scope.is_(True),
                    )
                )
            ).scalars()
        )
        item.retired_at = datetime.now(UTC)
        item.retired_reason = cleaned
        await session.flush([item])
        await self._audit.record(
            session,
            action="update",
            object_type="scope_item",
            object_id=item.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"retired_at": None},
            after={"retired_at": item.retired_at.isoformat(), "retired_reason": cleaned},
        )
        notices: list[str] = []
        for decision in decisions:
            engagement = await session.get(Engagement, decision.engagement_id)
            if engagement is None:
                continue
            scope_model = await self._scope_model(session, engagement)
            for notice in self._notices(engagement, scope_model, item.retired_at.date()):
                if notice not in notices:
                    notices.append(notice)
        return notices


scope_service = ScopeService()
