"""Baseline, readiness snapshots, the work plan and the setup flow's place (PL-6 to PL-12).

The baseline asks, family by family, what is already in place. It is the person's own view and
never moves a control's status: only evidence and checks do that. Completing it freezes the
figures as a readiness snapshot, so later progress can be shown against the start.

The plan is computed from the baseline: a control not in place (or not known) gets a task to put
it in place; one in place but without current evidence gets an evidence request. Approving the
plan raises the tasks through the tasks service, keyed on ``(onboarding, item key)``, so approving
again makes nothing new. Owners come from the control, then from its function; due dates from the
nearest planned milestone.
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.modules.audit.service import Actor, AuditService, audit_service
from verity.modules.compliance.control_service import control_service
from verity.modules.compliance.engagement_service import engagement_service
from verity.modules.compliance.framework_service import framework_service
from verity.modules.compliance.programme_service import programme_service
from verity.modules.compliance.readiness import BUILT_IN_SOURCE
from verity.modules.connectors.service import connector_service
from verity.modules.evidence.service import evidence_service
from verity.modules.onboarding.models import (
    BASELINE_ANSWERS,
    Baseline,
    BaselineAnswer,
    OnboardingState,
    ReadinessSnapshot,
)
from verity.modules.onboarding.owner_functions import function_for
from verity.modules.onboarding.ownership_service import ownership_service
from verity.modules.tasks.service import PlannedTask, task_service
from verity.modules.tenancy.service import tenancy_service
from verity.shared.ids import uuid7

SOURCE: Final = "onboarding"
SETUP_STEPS: Final[tuple[str, ...]] = (
    "start",
    "frameworks",
    "import",
    "profile",
    "audit",
    "owners",
    "suggestions",
)
_NOT_YET: Final = frozenset({"partly", "not_in_place", "not_sure"})


@dataclass(frozen=True, slots=True)
class BaselineControl:
    id: uuid.UUID
    code: str
    name: str
    answer: str | None
    note: str | None


@dataclass(frozen=True, slots=True)
class BaselineFamily:
    family: str
    controls: list[BaselineControl]
    answered: int


@dataclass(frozen=True, slots=True)
class BaselineView:
    id: uuid.UUID | None
    status: str
    """``none``, ``open`` or ``complete``."""
    families: list[BaselineFamily]
    answered: int
    total: int
    counts: dict[str, int]
    completed_at: datetime | None


@dataclass(frozen=True, slots=True)
class PlanItem:
    key: str
    kind: str
    """``put_in_place`` or ``evidence``."""
    title: str
    control_code: str
    owner_membership_id: uuid.UUID | None
    due_on: date | None
    raised: bool


@dataclass(frozen=True, slots=True)
class PlanView:
    items: list[PlanItem]
    raised: int
    due_on: date | None
    due_label: str | None


@dataclass(frozen=True, slots=True)
class ConnectionSuggestion:
    key: str
    name: str
    because: str
    status: str
    """``available``, ``planned`` or ``not_planned``, from the catalogue."""
    connected: bool


_IDP: Final[dict[str, str]] = {
    "google_workspace": "gws",
    "microsoft_entra": "entra",
    "okta": "okta",
}
_HOSTING: Final[dict[str, str]] = {"aws": "aws", "azure": "azure", "gcp": "gcp"}


@dataclass(frozen=True, slots=True)
class SetupView:
    start_point: str | None
    setup_step: str | None
    completed_at: datetime | None
    steps: list[str]


class PlanService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service

    # -- baseline ----------------------------------------------------------------

    async def _latest(self, session: AsyncSession, tenant_id: uuid.UUID) -> Baseline | None:
        return (
            await session.execute(
                select(Baseline)
                .where(Baseline.tenant_id == tenant_id)
                .order_by(Baseline.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def _answers(
        self, session: AsyncSession, tenant_id: uuid.UUID, baseline_id: uuid.UUID
    ) -> dict[uuid.UUID, BaselineAnswer]:
        rows = await session.execute(
            select(BaselineAnswer).where(
                BaselineAnswer.tenant_id == tenant_id, BaselineAnswer.baseline_id == baseline_id
            )
        )
        return {a.control_id: a for a in rows.scalars()}

    async def baseline(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> BaselineView:
        latest = await self._latest(session, tenant_id)
        answers = await self._answers(session, tenant_id, latest.id) if latest else {}
        controls = [
            c
            for c in await control_service.list_controls(session, tenant_id=tenant_id)
            if c.status != "not_applicable"
        ]
        by_family: dict[str, list[BaselineControl]] = {}
        for c in sorted(controls, key=lambda c: c.code):
            a = answers.get(c.id)
            by_family.setdefault(c.category, []).append(
                BaselineControl(
                    c.id, c.code, c.name, a.answer if a else None, a.note if a else None
                )
            )
        families = [
            BaselineFamily(f, items, sum(1 for i in items if i.answer))
            for f, items in sorted(by_family.items())
        ]
        counts = Counter(a.answer for a in answers.values())
        return BaselineView(
            id=latest.id if latest else None,
            status=latest.status if latest else "none",
            families=families,
            answered=sum(f.answered for f in families),
            total=len(controls),
            counts={k: counts.get(k, 0) for k in BASELINE_ANSWERS},
            completed_at=latest.completed_at if latest else None,
        )

    async def _open(
        self, session: AsyncSession, tenant_id: uuid.UUID, actor: Actor, membership_id: uuid.UUID
    ) -> Baseline:
        latest = await self._latest(session, tenant_id)
        if latest is not None and latest.status == "open":
            return latest
        row = Baseline(id=uuid7(), tenant_id=tenant_id, taken_by_membership_id=membership_id)
        session.add(row)
        await session.flush([row])
        await self._audit.record(
            session,
            action="create",
            object_type="baseline",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"status": "open"},
        )
        return row

    async def answer(  # noqa: PLR0913 — who, which control, the answer and a note
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        membership_id: uuid.UUID,
        control_id: uuid.UUID,
        answer: str,
        note: str | None,
    ) -> None:
        if answer not in BASELINE_ANSWERS:
            raise InvalidInput("Choose one of the four answers.", detail=f"answer {answer!r}")
        live = {c.id for c in await control_service.list_controls(session, tenant_id=tenant_id)}
        if control_id not in live:
            raise NotFound("That control is not in this workspace.", detail=str(control_id))
        baseline = await self._open(session, tenant_id, actor, membership_id)
        row = (await self._answers(session, tenant_id, baseline.id)).get(control_id)
        before = {"answer": row.answer, "note": row.note} if row else None
        if row is None:
            row = BaselineAnswer(
                id=uuid7(), tenant_id=tenant_id, baseline_id=baseline.id, control_id=control_id
            )
            session.add(row)
        row.answer = answer
        row.note = (note or "").strip() or None
        row.answered_by_membership_id = membership_id
        await session.flush([row])
        await self._audit.record(
            session,
            action="create" if before is None else "update",
            object_type="baseline_answer",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after={"answer": row.answer, "note": row.note, "control_id": str(control_id)},
        )

    async def complete(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor
    ) -> BaselineView:
        latest = await self._latest(session, tenant_id)
        if latest is None or latest.status != "open":
            raise Conflict("There is no open baseline to finish.", detail="no open baseline")
        view = await self.baseline(session, tenant_id=tenant_id)
        if view.answered == 0:
            raise InvalidInput(
                "Answer at least one control before finishing.", detail="empty baseline"
            )
        latest.status = "complete"
        latest.completed_at = datetime.now(UTC)
        await session.flush([latest])
        await self.snapshot(session, tenant_id=tenant_id, actor=actor, label="Baseline")
        await self._audit.record(
            session,
            action="update",
            object_type="baseline",
            object_id=latest.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"status": "open"},
            after={"status": "complete", "answered": view.answered, "counts": view.counts},
        )
        return await self.baseline(session, tenant_id=tenant_id)

    # -- snapshots ---------------------------------------------------------------

    async def snapshot(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor, label: str
    ) -> ReadinessSnapshot:
        """Freeze each framework's figures now (PL-9). Append only."""
        codes = [
            v.code
            for v in await framework_service.list_for_tenant(session, tenant_id=tenant_id)
            if v.added
        ]
        figures = await engagement_service.program_figures(
            session, tenant_id=tenant_id, framework_codes=codes
        )
        data: dict[str, Any] = {
            "controls_total": figures.controls_total,
            "controls_owned": figures.controls_owned,
            "controls_evidenced": figures.controls_evidenced,
            "frameworks": {
                f.code: {
                    "requirements_total": f.requirements_total,
                    "requirements_met": f.requirements_met,
                    "controls_evidenced": f.controls_evidenced,
                }
                for f in figures.frameworks
            },
        }
        row = ReadinessSnapshot(id=uuid7(), tenant_id=tenant_id, label=label, figures=data)
        session.add(row)
        await session.flush([row])
        await self._audit.record(
            session,
            action="create",
            object_type="readiness_snapshot",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"label": label},
        )
        return row

    async def snapshots(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[ReadinessSnapshot]:
        return list(
            (
                await session.execute(
                    select(ReadinessSnapshot)
                    .where(ReadinessSnapshot.tenant_id == tenant_id)
                    .order_by(ReadinessSnapshot.created_at)
                )
            ).scalars()
        )

    # -- plan --------------------------------------------------------------------

    async def _due(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> tuple[date | None, str | None]:
        today = datetime.now(UTC).date()
        upcoming: list[tuple[date, str]] = []
        for v in await framework_service.list_for_tenant(session, tenant_id=tenant_id):
            if not v.added:
                continue
            for m in await programme_service.milestones(
                session, tenant_id=tenant_id, framework_code=v.code
            ):
                if m.planned_on and m.planned_on >= today and m.actual_on is None:
                    upcoming.append((m.planned_on, f"{v.name}: {m.label}"))
        if not upcoming:
            return None, None
        due, label = min(upcoming)
        return due, label

    async def _items(self, session: AsyncSession, tenant_id: uuid.UUID) -> PlanView:
        latest = await self._latest(session, tenant_id)
        answers = await self._answers(session, tenant_id, latest.id) if latest else {}
        controls = {
            c.id: c
            for c in await control_service.list_controls(session, tenant_id=tenant_id)
            if c.status != "not_applicable"
        }
        evidenced = await evidence_service.control_ids_with_current_evidence(
            session, tenant_id, exclude_source=BUILT_IN_SOURCE
        )
        members = await ownership_service.function_members(session, tenant_id=tenant_id)
        due, label = await self._due(session, tenant_id)
        planned: list[tuple[str, str, str, Any]] = []
        for cid, a in answers.items():
            c = controls.get(cid)
            if c is None:
                continue
            if a.answer in _NOT_YET:
                planned.append(
                    (f"control:{c.code}", "put_in_place", f"Put {c.code} in place: {c.name}", c)
                )
            elif cid not in evidenced:
                planned.append(
                    (f"evidence:{c.code}", "evidence", f"File evidence for {c.code}: {c.name}", c)
                )
        raised = await task_service.existing_keys(
            session, tenant_id=tenant_id, source=SOURCE, keys=[p[0] for p in planned]
        )
        items = [
            PlanItem(
                key=key,
                kind=kind,
                title=title,
                control_code=c.code,
                owner_membership_id=c.owner_membership_id
                or members.get(function_for(c.code) or ""),
                due_on=due,
                raised=key in raised,
            )
            for key, kind, title, c in sorted(planned, key=lambda p: p[0])
        ]
        return PlanView(items=items, raised=len(raised), due_on=due, due_label=label)

    async def plan(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> PlanView:
        return await self._items(session, tenant_id)

    async def approve_plan(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor
    ) -> int:
        view = await self._items(session, tenant_id)
        todo = [i for i in view.items if not i.raised]
        if not view.items:
            raise Conflict("Nothing to plan yet. Answer the baseline first.", detail="empty plan")
        controls = {
            c.code: c.id for c in await control_service.list_controls(session, tenant_id=tenant_id)
        }
        due_at = datetime.combine(view.due_on, time.min, tzinfo=UTC) if view.due_on else None
        made = await task_service.raise_planned(
            session,
            tenant_id=tenant_id,
            actor=actor,
            source=SOURCE,
            items=[
                PlannedTask(
                    key=i.key,
                    title=i.title,
                    description=(
                        "Upload the evidence on the control's page, or connect a system that "
                        "files it."
                        if i.kind == "evidence"
                        else "Your baseline said this is not fully in place yet."
                    ),
                    owner_membership_id=i.owner_membership_id,
                    due_at=due_at,
                    control_id=controls.get(i.control_code),
                )
                for i in todo
            ],
        )
        await self._audit.record(
            session,
            action="create",
            object_type="onboarding_plan",
            object_id=uuid7(),
            actor=actor,
            tenant_id=tenant_id,
            after={"tasks_raised": made, "keys": [i.key for i in todo]},
        )
        return made

    # -- a profile section given to someone (guided onboarding 2.8) ---------------

    async def assign_section(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        section: str,
        membership_id: uuid.UUID,
    ) -> bool:
        """Raise a task asking a member to answer one section of the company profile. Raised
        once per section and person: asking again while it is open makes nothing new."""
        from verity.modules.tenancy.profile_questions import SECTIONS  # noqa: PLC0415

        titles = dict(SECTIONS)
        if section not in titles:
            raise NotFound("That profile section does not exist.", detail=section)
        made = await task_service.raise_planned(
            session,
            tenant_id=tenant_id,
            actor=actor,
            source=SOURCE,
            items=[
                PlannedTask(
                    key=f"profile:{section}:{membership_id}",
                    title=f"Answer the company profile: {titles[section]}",
                    description="Settings, Organization, Company profile. Save your answers; "
                    "the admin confirms the profile.",
                    owner_membership_id=membership_id,
                    due_at=None,
                    control_id=None,
                )
            ],
        )
        return made > 0

    # -- connection suggestions (PL-10) -------------------------------------------

    async def connections(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[ConnectionSuggestion]:
        """Systems the profile says the company runs, matched to the integration catalogue,
        with whether they can be connected today and whether they already are."""
        profile = await tenancy_service.get_own_company_profile(session, tenant_id)
        answers = profile.answers or {}
        wanted: dict[str, str] = {}
        idp = _IDP.get(str(answers.get("identity_provider") or ""))
        if idp:
            wanted[idp] = "You sign in with it."
        for h in answers.get("hosting_providers") or []:
            if h in _HOSTING:
                wanted[_HOSTING[h]] = "You host on it."
        if answers.get("builds_software") == "yes":
            wanted["github"] = "You build software. Connect your code host."
        if not wanted:
            return []
        catalogue = {p.key: p for p in await connector_service.providers(session)}
        connected = await connector_service.connected_keys(session, tenant_id=tenant_id)
        return [
            ConnectionSuggestion(
                key=key,
                name=catalogue[key].name,
                because=why,
                status=catalogue[key].status,
                connected=key in connected,
            )
            for key, why in wanted.items()
            if key in catalogue
        ]

    # -- setup flow --------------------------------------------------------------

    async def _state(self, session: AsyncSession, tenant_id: uuid.UUID) -> OnboardingState | None:
        return (
            await session.execute(
                select(OnboardingState).where(OnboardingState.tenant_id == tenant_id)
            )
        ).scalar_one_or_none()

    async def setup(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> SetupView:
        row = await self._state(session, tenant_id)
        # Bringing a programme puts its reports, documents and baseline first (EX-1); starting
        # fresh skips that screen.
        existing = row is not None and row.start_point == "existing"
        return SetupView(
            start_point=row.start_point if row else None,
            setup_step=row.setup_step if row else None,
            completed_at=row.setup_completed_at if row else None,
            steps=[s for s in SETUP_STEPS if s != "import" or existing],
        )

    async def save_setup(  # noqa: PLR0913 — where the flow stands
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        start_point: str | None,
        setup_step: str | None,
        complete: bool,
    ) -> SetupView:
        if setup_step is not None and setup_step not in SETUP_STEPS:
            raise InvalidInput("That setup step does not exist.", detail=setup_step)
        if start_point is not None and start_point not in {"fresh", "existing"}:
            raise InvalidInput("Choose starting fresh or bringing a programme.", detail=start_point)
        row = await self._state(session, tenant_id)
        before = {"start_point": row.start_point, "setup_step": row.setup_step} if row else None
        if row is None:
            row = OnboardingState(id=uuid7(), tenant_id=tenant_id)
            session.add(row)
        if start_point is not None:
            row.start_point = start_point
        if setup_step is not None:
            row.setup_step = setup_step
        if complete and row.setup_completed_at is None:
            row.setup_completed_at = datetime.now(UTC)
        await session.flush([row])
        await self._audit.record(
            session,
            action="create" if before is None else "update",
            object_type="onboarding_state",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after={
                "start_point": row.start_point,
                "setup_step": row.setup_step,
                "completed": row.setup_completed_at is not None,
            },
        )
        return await self.setup(session, tenant_id=tenant_id)


plan_service = PlanService()
