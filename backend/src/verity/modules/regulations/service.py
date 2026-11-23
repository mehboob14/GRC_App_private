"""The country reference panel (guided onboarding JC-1 to JC-9, J1 to J5).

Reads the profile, matches it against the sealed pack and returns what may apply, with the
answers behind each match, the controls the workspace runs that help, and the workspace's own
call on each. Entries not yet reviewed by a named reviewer are hidden unless the deployment
turns drafts on (task 6.7, decision D-8). A country outside the pack is logged by code only.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.config import get_settings
from verity.core.errors import InvalidInput, NotFound
from verity.core.logging import get_logger
from verity.modules.audit.service import Actor, AuditService, audit_service
from verity.modules.compliance.control_service import control_service
from verity.modules.iam.service import iam_service
from verity.modules.regulations.models import RegulationDecision
from verity.modules.regulations.pack import entries, matches, uncovered
from verity.modules.tenancy.profile_questions import QUESTIONS
from verity.modules.tenancy.service import tenancy_service
from verity.shared.ids import uuid7

logger = get_logger(__name__)

DISCLAIMER: Final = (
    "A starting point, not legal advice. Each entry names its sources; confirm with your "
    "lawyer before you rely on it."
)
DRAFT_NOTE: Final = (
    " These entries were drafted with AI from the sources shown and are not yet reviewed by "
    "a lawyer."
)
NOTE_MAX: Final = 1000
_LABELS: Final[dict[str, str]] = {q.key: q.label for q in QUESTIONS}


@dataclass(frozen=True, slots=True)
class RegulationView:
    key: str
    jurisdiction: str
    zone: str | None
    short_name: str
    official_name: str
    regulator: str | None
    kinds: list[str]
    topic_column: str
    force: str
    state: str
    state_note: str | None
    tier: str
    applies_to: str
    duties: list[dict[str, Any]]
    assurance: dict[str, Any]
    iso27001: dict[str, Any]
    soc2: dict[str, Any]
    helps: list[str]
    """Controls this workspace runs that help, wildcards expanded."""
    not_covered: list[str]
    milestones: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    review_status: str
    review_overdue: bool
    confidence: str
    because: list[str]
    relevance: str | None
    note: str | None
    decided_by_name: str | None
    decided_at: datetime | None
    in_register_since: datetime | None = None


@dataclass(frozen=True, slots=True)
class PanelView:
    regulations: list[RegulationView]
    hidden_drafts: int
    uncovered: list[str]
    disclaimer: str


def _helps(codes: list[str], running: set[str]) -> list[str]:
    out: list[str] = []
    for code in codes:
        if code.endswith("*"):
            out.extend(sorted(c for c in running if c.startswith(code[:-1])))
        elif code in running:
            out.append(code)
    return list(dict.fromkeys(out))


class RegulationsService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service

    async def _decisions(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[str, RegulationDecision]:
        rows = await session.execute(
            select(RegulationDecision).where(RegulationDecision.tenant_id == tenant_id)
        )
        return {d.regulation_key: d for d in rows.scalars()}

    async def panel(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> PanelView:
        profile = await tenancy_service.get_own_company_profile(session, tenant_id)
        answers = dict(profile.answers or {})
        show_drafts = get_settings().regulations_show_drafts
        running = set(await control_service.states_by_code(session, tenant_id=tenant_id))
        decisions = await self._decisions(session, tenant_id)
        names = {
            m.membership_id: m.full_name
            for m in await iam_service.list_members(session, tenant_id=tenant_id)
        }
        today = datetime.now(UTC).date().isoformat()
        out: list[RegulationView] = []
        hidden = 0
        # Without a single country there is nothing to place a law against: the page asks for
        # the countries instead of listing every first tier law as "check".
        located = bool(answers.get("hq_country") or answers.get("operating_countries"))
        for m in matches(answers) if located else []:
            e = m.entry
            review = e.get("review") or {}
            if review.get("status") != "reviewed" and not show_drafts:
                hidden += 1
                continue
            d = decisions.get(e["key"])
            out.append(
                RegulationView(
                    key=e["key"],
                    jurisdiction=e["jurisdiction"],
                    zone=e.get("zone"),
                    short_name=e["short_name"],
                    official_name=e["official_name"],
                    regulator=e.get("regulator"),
                    kinds=list(e.get("kinds") or []),
                    topic_column=e["topic_column"],
                    force=e["force"],
                    state=e["state"],
                    state_note=e.get("state_note"),
                    tier=e["tier"],
                    applies_to=e["applies_to"],
                    duties=list(e.get("duties") or []),
                    assurance=dict(e.get("assurance") or {}),
                    iso27001=dict(e.get("iso27001") or {}),
                    soc2=dict(e.get("soc2") or {}),
                    helps=_helps(list(e.get("helps") or []), running),
                    not_covered=list(e.get("not_covered") or []),
                    milestones=list(e.get("milestones") or []),
                    sources=list(e.get("sources") or []),
                    review_status=str(review.get("status") or "ai_drafted"),
                    review_overdue=bool(
                        review.get("next_review_due") and review["next_review_due"] < today
                    ),
                    confidence=m.confidence,
                    because=[_LABELS.get(f, f) for f in m.facts],
                    relevance=d.relevance if d else None,
                    note=d.note if d else None,
                    decided_by_name=names.get(d.decided_by_membership_id)
                    if d and d.decided_by_membership_id
                    else None,
                    decided_at=d.updated_at if d else None,
                    in_register_since=d.register_row_added_at
                    if d and d.relevance == "relevant"
                    else None,
                )
            )
        missing = uncovered(answers)
        if missing:
            # The country code only: no tenant detail leaves in the event (design 2.6).
            logger.info("regulations.uncovered_country", countries=missing)
        drafted = any(r.review_status != "reviewed" for r in out)
        return PanelView(
            regulations=out,
            hidden_drafts=hidden,
            uncovered=missing,
            disclaimer=DISCLAIMER + (DRAFT_NOTE if drafted else ""),
        )

    async def decide(  # noqa: PLR0913 — who, which law, the call and why
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        membership_id: uuid.UUID,
        key: str,
        relevance: str,
        note: str | None,
    ) -> None:
        if key not in {e["key"] for e in entries()}:
            raise NotFound("That law is not in the reference list.", detail=f"regulation {key!r}")
        if relevance not in {"relevant", "not_relevant"}:
            raise InvalidInput("Choose relevant or not relevant.", detail=relevance)
        cleaned = (note or "").strip() or None
        if relevance == "not_relevant" and cleaned is None:
            raise InvalidInput(
                "Say why this does not apply. The reason is kept with the decision.",
                detail="not relevant without a note",
            )
        if cleaned and len(cleaned) > NOTE_MAX:
            raise InvalidInput(f"Keep the note under {NOTE_MAX} characters.", detail="note")
        profile = await tenancy_service.get_own_company_profile(session, tenant_id)
        row = (await self._decisions(session, tenant_id)).get(key)
        before = {"relevance": row.relevance, "note": row.note} if row else None
        if row is None:
            row = RegulationDecision(id=uuid7(), tenant_id=tenant_id, regulation_key=key)
            session.add(row)
        row.relevance = relevance
        row.note = cleaned
        # Relevant laws form the obligations register (J5); the date it joined is kept.
        if relevance == "relevant" and row.register_row_added_at is None:
            row.register_row_added_at = datetime.now(UTC)
        row.decided_by_membership_id = membership_id
        row.profile_version = profile.version
        await session.flush([row])
        await self._audit.record(
            session,
            action="create" if before is None else "update",
            object_type="regulation_decision",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after={"regulation_key": key, "relevance": relevance, "note": cleaned},
        )


regulations_service = RegulationsService()
