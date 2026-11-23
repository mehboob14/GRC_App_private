"""Suggestions from the profile, and what people decided about them (PL-1 to PL-5, SC-5, SC-7).

Candidates are computed on every read from the profile answers, the active frameworks and the
workspace's state, so they cannot drift. A candidate whose change is already in place is not
shown. Only decisions are stored. Accepting calls the owning service (compliance), which writes
its own audit row; the decision row and its audit row land in the same transaction.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.modules.audit.service import Actor, AuditService, audit_service
from verity.modules.compliance.control_service import control_service
from verity.modules.compliance.engagement_service import engagement_service
from verity.modules.compliance.framework_service import framework_service
from verity.modules.compliance.programme_service import programme_service
from verity.modules.iam.service import iam_service
from verity.modules.onboarding.models import ProposalDecision
from verity.modules.onboarding.rules import SOC2_CATEGORIES, Rule, firing, supplier_name
from verity.modules.tenancy.service import tenancy_service
from verity.shared.ids import uuid7

OBJECT_TYPE: Final = "onboarding_proposal"
REASON_MAX: Final = 2000
_SNAPSHOT: Final = ("dedupe_key", "decision", "reason", "payload")


@dataclass(frozen=True, slots=True)
class Candidate:
    key: str
    rule_key: str
    kind: str
    subject: str
    subject_name: str
    change: str
    because: str
    reason: str
    payload: dict[str, Any]
    bulk_ok: bool
    framework: str | None
    target_id: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class ProposalView:
    key: str
    rule_key: str
    kind: str
    subject: str
    subject_name: str
    change: str
    because: str
    reason: str
    bulk_ok: bool
    framework: str | None
    state: str
    """``open``, ``accepted``, ``rejected`` or ``review_needed``."""
    decided_by_name: str | None = None
    decided_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ProposalsView:
    proposals: list[ProposalView]
    open: int
    review_needed: int


def _change(kind: str, payload: dict[str, Any], subject: str) -> str:
    if kind == "control_status":
        return "Mark not applicable"
    if kind == "soc2_category":
        return f"Add {subject} to your SOC 2 scope"
    if payload.get("applicable"):
        return "Applicable, operated by a supplier"
    return "Exclude from the Statement of Applicability"


class ProposalsService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service

    async def _candidates(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> tuple[list[Candidate], dict[str, Rule], int | None, dict[str, uuid.UUID]]:
        profile = await tenancy_service.get_own_company_profile(session, tenant_id)
        answers = dict(profile.answers or {})
        company = profile.display_name or profile.legal_name or "The company"
        frameworks = {
            v.code
            for v in await framework_service.list_for_tenant(session, tenant_id=tenant_id)
            if v.added
        }
        controls = await control_service.states_by_code(session, tenant_id=tenant_id)
        iso = (
            await framework_service.applicability_decisions(
                session, tenant_id=tenant_id, framework_code="ISO27001"
            )
            if "ISO27001" in frameworks
            else None
        )
        iso_rows = {d.code: d for d in iso[2]} if iso else {}
        frameworks_by_id = {"ISO27001": iso[0]} if iso else {}
        fill = {"company": company, "supplier": supplier_name(answers)}
        rules = firing(answers, frameworks)
        found: list[Candidate] = []
        for rule in rules:
            for subject in rule.subjects:
                key = f"{rule.key}:{subject}"
                reason = rule.reason.format(**fill)
                if rule.kind == "control_status":
                    held = controls.get(subject)
                    if held is None:
                        continue
                    cid, status, name = held
                    # Only an untouched control: a person who moved it on has decided.
                    if status != "not_started":
                        continue
                    target, subject_name = cid, name
                else:
                    row = iso_rows.get(subject)
                    # A reviewed row is a person's decision; never propose over it.
                    if row is None or row.locked or row.reviewed_at is not None:
                        continue
                    target, subject_name = row.requirement_id, row.name
                found.append(
                    Candidate(
                        key=key,
                        rule_key=rule.key,
                        kind=rule.kind,
                        subject=subject,
                        subject_name=subject_name,
                        change=_change(rule.kind, rule.payload, subject),
                        because=rule.because,
                        reason=reason,
                        payload=dict(rule.payload),
                        bulk_ok=rule.bulk_ok,
                        framework=rule.framework,
                        target_id=target,
                    )
                )
        if "SOC2" in frameworks:
            soc2 = await engagement_service.get(session, tenant_id=tenant_id, framework_code="SOC2")
            elected = set(soc2.categories_in_scope) if soc2 else set()
            by_key = {c.lower().replace(" ", "_"): c for c in SOC2_CATEGORIES}
            for c in await programme_service.commitments(session, tenant_id=tenant_id):
                for point in c.points_at or []:
                    category = by_key.get(str(point).lower().replace(" ", "_"))
                    if category is None or category in elected:
                        continue
                    found.append(
                        Candidate(
                            key=f"commitment.category:{category}",
                            rule_key="commitment.category",
                            kind="soc2_category",
                            subject=category,
                            subject_name=category,
                            change=_change("soc2_category", {}, category),
                            because=f"You promise customers: {c.statement}",
                            reason=f"Added because {company} commits to it: {c.statement}",
                            payload={"category": category},
                            bulk_ok=True,
                            framework="SOC2",
                        )
                    )
                    elected.add(category)
        return found, {r.key: r for r in rules}, profile.version, frameworks_by_id

    async def _decisions(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[str, ProposalDecision]:
        rows = await session.execute(
            select(ProposalDecision).where(ProposalDecision.tenant_id == tenant_id)
        )
        return {d.dedupe_key: d for d in rows.scalars()}

    async def view(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> ProposalsView:
        candidates, rules, _, _ = await self._candidates(session, tenant_id)
        decisions = await self._decisions(session, tenant_id)
        names = {
            m.membership_id: m.full_name
            for m in await iam_service.list_members(session, tenant_id=tenant_id)
        }
        out: list[ProposalView] = []
        seen: set[str] = set()
        for c in candidates:
            seen.add(c.key)
            d = decisions.get(c.key)
            # An accepted change a person later undid by hand fires again: ask again.
            state = "rejected" if d and d.decision == "rejected" else "open"
            out.append(self._view(c, state, d, names))
        for key, d in decisions.items():
            if key in seen:
                continue
            # Accepted, and the answer behind it has since changed: someone should look again.
            lapsed = d.rule_key != "commitment.category" and d.rule_key not in rules
            state = "review_needed" if d.decision == "accepted" and lapsed else d.decision
            out.append(
                ProposalView(
                    key=key,
                    rule_key=d.rule_key,
                    kind=d.kind,
                    subject=d.subject_key,
                    subject_name=d.subject_key,
                    change=_change(d.kind, d.payload, d.subject_key),
                    because=d.because,
                    reason=d.reason,
                    bulk_ok=False,
                    framework=None,
                    state=state,
                    decided_by_name=names.get(d.decided_by_membership_id)
                    if d.decided_by_membership_id
                    else None,
                    decided_at=d.updated_at,
                )
            )
        return ProposalsView(
            proposals=out,
            open=sum(1 for p in out if p.state == "open"),
            review_needed=sum(1 for p in out if p.state == "review_needed"),
        )

    @staticmethod
    def _view(
        c: Candidate, state: str, d: ProposalDecision | None, names: dict[uuid.UUID, str]
    ) -> ProposalView:
        return ProposalView(
            key=c.key,
            rule_key=c.rule_key,
            kind=c.kind,
            subject=c.subject,
            subject_name=c.subject_name,
            change=c.change,
            because=c.because,
            reason=d.reason if d else c.reason,
            bulk_ok=c.bulk_ok,
            framework=c.framework,
            state=state,
            decided_by_name=names.get(d.decided_by_membership_id)
            if d and d.decided_by_membership_id
            else None,
            decided_at=d.updated_at if d else None,
        )

    # -- decisions -----------------------------------------------------------------

    @staticmethod
    def _clean(reason: str | None, fallback: str) -> str:
        cleaned = (reason or "").strip() or fallback
        if len(cleaned) > REASON_MAX:
            raise InvalidInput(
                f"Keep the reason under {REASON_MAX} characters.", detail="reason too long"
            )
        return cleaned

    async def _record(  # noqa: PLR0913 — who, which suggestion, what and why
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        membership_id: uuid.UUID,
        c: Candidate,
        decision: str,
        reason: str,
        profile_version: int | None,
    ) -> None:
        row = (await self._decisions(session, tenant_id)).get(c.key)
        before = AuditService.snapshot(row, fields=_SNAPSHOT) if row else None
        if row is None:
            row = ProposalDecision(
                id=uuid7(),
                tenant_id=tenant_id,
                dedupe_key=c.key,
                rule_key=c.rule_key,
                kind=c.kind,
                subject_key=c.subject,
                payload=c.payload,
                because=c.because,
            )
            session.add(row)
        row.decision = decision
        row.reason = reason
        row.profile_version = profile_version
        row.decided_by_membership_id = membership_id
        await session.flush([row])
        await self._audit.record(
            session,
            action="create" if before is None else "update",
            object_type=OBJECT_TYPE,
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(row, fields=_SNAPSHOT),
        )

    async def _apply(  # noqa: PLR0913 — who, which and why
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        c: Candidate,
        reason: str,
        frameworks: dict[str, uuid.UUID],
    ) -> None:
        if c.kind == "control_status":
            assert c.target_id is not None  # noqa: S101 — set for every control candidate
            await control_service.update_control(
                session,
                tenant_id=tenant_id,
                actor=actor,
                control_id=c.target_id,
                status=c.payload["status"],
            )
        elif c.kind == "iso_applicability":
            assert c.target_id is not None  # noqa: S101 — set for every requirement candidate
            await framework_service.set_applicability(
                session,
                tenant_id=tenant_id,
                actor=actor,
                framework_id=frameworks["ISO27001"],
                requirement_id=c.target_id,
                applicable=c.payload["applicable"],
                justification=reason,
                provided_by=c.payload["provided_by"],
                owner_membership_id=None,
                reviewed=True,
            )
        else:
            await engagement_service.add_category(
                session, tenant_id=tenant_id, actor=actor, category=c.payload["category"]
            )

    async def decide(  # noqa: PLR0913 — who, which, what and why
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        membership_id: uuid.UUID,
        keys: list[str],
        accept: bool,
        reason: str | None,
        bulk: bool = False,
    ) -> int:
        """Accept or reject suggestions. Accepting more than one at a time is refused for any
        suggestion a person must decide on its own (``bulk_ok`` false). Rejecting needs a reason."""
        candidates, _, version, frameworks = await self._candidates(session, tenant_id)
        by_key = {c.key: c for c in candidates}
        chosen = [by_key.get(k) for k in keys]
        if not keys or None in chosen:
            raise NotFound(
                "That suggestion no longer applies. Refresh the list.",
                detail=f"suggestions {keys!r}",
            )
        picked = [c for c in chosen if c is not None]
        if accept and bulk and any(not c.bulk_ok for c in picked):
            raise Conflict(
                "Some of these need a decision one at a time. Open each one to accept it.",
                detail="bulk accept of a suggestion that is not bulk_ok",
            )
        if not accept and not (reason or "").strip():
            raise InvalidInput("Say why this does not fit.", detail="reject without a reason")
        for c in picked:
            # One accepted can carry an edited reason; several take their own prefilled one.
            why = self._clean(reason if len(picked) == 1 or not accept else None, c.reason)
            if accept:
                await self._apply(
                    session,
                    tenant_id=tenant_id,
                    actor=actor,
                    c=c,
                    reason=why,
                    frameworks=frameworks,
                )
            await self._record(
                session,
                tenant_id=tenant_id,
                actor=actor,
                membership_id=membership_id,
                c=c,
                decision="accepted" if accept else "rejected",
                reason=why,
                profile_version=version,
            )
        return len(picked)


proposals_service = ProposalsService()
