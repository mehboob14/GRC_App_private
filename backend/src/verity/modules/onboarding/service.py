"""Get Started status, computed on every read from the records each step counts.

Nothing here is stored except skips. Each step's done rule reads a summary that the
owning module exposes through its service (rule 4), and a summary the caller may not read
is never fetched: its steps come back ``not_permitted`` and the rest of the page still
loads (requirement GS-1). The number of queries is fixed: one summary per module, one
scope read per framework, whatever the number of controls (NF-8).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.deps import Principal
from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.modules.audit.service import Actor, AuditService, audit_service
from verity.modules.compliance.assurance_service import AssuranceSummary, assurance_service
from verity.modules.compliance.engagement_service import (
    FrameworkFigures,
    ProgramFigures,
    engagement_service,
)
from verity.modules.compliance.framework_service import framework_service
from verity.modules.compliance.programme_service import MilestoneView, programme_service
from verity.modules.connectors.service import connector_service
from verity.modules.documents.required_service import RequiredView, required_documents_service
from verity.modules.iam.service import iam_service
from verity.modules.objectives.service import objectives_service
from verity.modules.onboarding.models import OnboardingStepSkip
from verity.modules.onboarding.owner_functions import FUNCTIONS
from verity.modules.onboarding.ownership_service import ownership_service
from verity.modules.onboarding.plan_service import plan_service
from verity.modules.onboarding.proposals_service import proposals_service
from verity.modules.onboarding.steps import PHASES, STEP_KEYS, STEPS, StepDef
from verity.modules.risk.service import risk_service
from verity.modules.tenancy.profile_questions import core_progress
from verity.modules.tenancy.service import tenancy_service
from verity.shared.ids import uuid7

OBJECT_TYPE: Final = "onboarding_step"
REASON_MAX: Final = 500


def category_keys(names: list[str]) -> set[str]:
    """SOC 2 categories are stored by name ("Processing Integrity"); rules key on snake case."""
    return {n.lower().replace(" ", "_") for n in names}


@dataclass(frozen=True, slots=True)
class SkipView:
    by_membership_id: uuid.UUID | None
    by_name: str | None
    at: datetime
    reason: str


@dataclass(frozen=True, slots=True)
class StepView:
    key: str
    step: str
    phase: str
    title: str
    framework_code: str | None
    """Set on a step that belongs to one framework; None for a shared one."""
    frameworks: list[str]
    """The frameworks a shared step counts for, as chips."""
    state: str
    """``not_started``, ``in_progress``, ``done``, ``skipped`` or ``not_permitted``."""
    done_count: int | None
    total_count: int | None
    detail: str | None
    link: str
    can_act: bool
    skip: SkipView | None = None


@dataclass(frozen=True, slots=True)
class StatusView:
    frameworks: list[FrameworkFigures] | None
    """None when the caller cannot read frameworks."""
    steps: list[StepView]
    next_key: str | None
    controls_total: int | None = None
    checks_failing: int | None = None
    phases: list[str] = field(default_factory=list)
    milestones: dict[str, list[MilestoneView]] = field(default_factory=dict)
    """Per framework code: the audit plan, for the timeline (GS-11)."""


_BANDS: Final = ((10, "1_10"), (50, "11_50"), (200, "51_200"), (500, "201_500"),
                  (1000, "501_1000"), (10**9, "over_1000"))  # fmt: skip
_IDP_FROM: Final = {"okta": "okta", "entra": "microsoft_entra", "gws": "google_workspace"}
_HOSTING_FROM: Final = {"aws": "aws", "azure": "azure", "gcp": "gcp"}


@dataclass(frozen=True, slots=True)
class PrefillItem:
    key: str
    value: Any
    source: str


@dataclass(frozen=True, slots=True)
class MyItem:
    kind: str
    """approve, acknowledge or task."""
    title: str
    link: str


@dataclass(frozen=True, slots=True)
class MyPartView:
    items: list[MyItem]


@dataclass(frozen=True, slots=True)
class _Facts:
    """Everything the done rules read, fetched once per request, per permission."""

    profile: Any = None
    security_require_admin_mfa: bool | None = None
    own_mfa: bool | None = None
    active_members: int | None = None
    program: ProgramFigures | None = None
    risks: tuple[int, int] | None = None
    connected: int | None = None
    member_names: dict[uuid.UUID, str] = field(default_factory=dict)
    functions_assigned: int | None = None
    documents: tuple[int, int, int] | None = None
    """Required documents counted, approved, in review."""
    suggestions: tuple[int, int, int] | None = None
    """Suggestions open, needing review, decided."""
    baseline: tuple[str, int, int] | None = None
    """Baseline status, answered, total."""
    plan: tuple[int, int] | None = None
    """Plan items, raised."""
    assurance: dict[str, AssuranceSummary] = field(default_factory=dict)
    """Per framework code: records, findings and their state (steps 21 to 24)."""
    description_approved: bool | None = None
    issued: dict[str, bool] = field(default_factory=dict)
    objectives: tuple[int, int] | None = None
    """Assessment objectives satisfied, applicable."""
    """Per framework code: the current cycle's report or certificate decision is recorded."""


@dataclass(frozen=True, slots=True)
class _Result:
    done: bool
    done_count: int | None = None
    total_count: int | None = None
    detail: str | None = None
    applies: bool = True


def _count(done: int, total: int, noun: str) -> _Result:
    return _Result(
        done=total > 0 and done >= total,
        done_count=done,
        total_count=total,
        detail=f"{done} of {total} {noun}",
    )


def _rule(step: StepDef, facts: _Facts, fw: FrameworkFigures | None) -> _Result:  # noqa: PLR0911, PLR0912, PLR0915 — one branch per step
    """The done rule for one step. Reads only facts; never queries."""
    key = step.key
    if key == "profile":
        profile = facts.profile
        answered, total = core_progress(profile.answers or {})
        if profile.status == "confirmed":
            return _Result(done=True, detail=f"Version {profile.version} confirmed")
        if profile.version:
            return _Result(
                done=False,
                done_count=answered,
                total_count=total,
                detail=f"Changes since version {profile.version} are not confirmed yet",
            )
        return _count(answered, total, "core questions answered")
    if key == "own_mfa":
        return _Result(done=bool(facts.own_mfa))
    if key == "admin_mfa":
        return _Result(done=bool(facts.security_require_admin_mfa))
    if key == "invite":
        members = facts.active_members or 0
        return _Result(
            done=members > 1,
            detail=f"{members} {'member' if members == 1 else 'members'}",
        )
    if key == "documents" and facts.documents is not None:
        counted, approved, in_review = facts.documents
        result = _count(approved, counted, "documents approved")
        if in_review:
            return _Result(
                done=result.done,
                done_count=approved,
                total_count=counted,
                detail=f"{approved} of {counted} approved, {in_review} waiting for approval",
            )
        return result
    if key == "suggestions" and facts.suggestions is not None:
        open_, review, decided = facts.suggestions
        if not (open_ or review or decided):
            return _Result(done=False, applies=False)
        waiting = open_ + review
        return _Result(
            done=waiting == 0,
            done_count=decided,
            total_count=decided + waiting,
            detail=f"{waiting} waiting for a decision" if waiting else f"{decided} decided",
        )
    if key == "baseline" and facts.baseline is not None:
        state, answered, total = facts.baseline
        if state == "complete":
            return _Result(done=True, detail=f"{answered} controls answered")
        return _count(answered, total, "controls answered")
    if key == "plan" and facts.plan is not None:
        items, raised = facts.plan
        if not items:
            return _Result(
                done=False, applies=facts.baseline is not None and facts.baseline[0] != "none"
            )
        return _count(raised, items, "planned tasks raised")
    if key == "objectives" and facts.objectives is not None:
        done, total = facts.objectives
        return _count(done, total, "objectives met")
    if key == "functions" and facts.functions_assigned is not None:
        return _count(facts.functions_assigned, len(FUNCTIONS), "functions have a person")
    program = facts.program
    if key == "owners" and program is not None:
        return _count(program.controls_owned, program.controls_total, "controls have an owner")
    if key == "evidence" and program is not None:
        return _count(
            program.controls_evidenced, program.controls_total, "controls have current evidence"
        )
    if key == "failing" and program is not None:
        # Shown only once an automated check has a result: with nothing running, "nothing
        # is failing" is not an achievement and would read done on day one.
        ran = any(f.checks_passing or f.checks_failing for f in program.frameworks)
        failing = program.checks_failing
        return _Result(
            done=failing == 0,
            detail=f"{failing} {'control' if failing == 1 else 'controls'} failing a check",
            applies=ran,
        )
    if key == "risks" and facts.risks is not None:
        total, assessed = facts.risks
        if total == 0:
            return _Result(done=False, detail="No risks recorded yet")
        return _count(assessed, total, "risks have an owner, a rating and a treatment")
    if key == "connect" and facts.connected is not None:
        connected = facts.connected
        return _Result(
            done=connected > 0,
            detail=f"{connected} connected" if connected else None,
        )
    if key == "close_findings" and facts.assurance:
        open_ = sum(a.findings_open for a in facts.assurance.values())
        overdue = sum(a.findings_overdue for a in facts.assurance.values())
        if not open_ and not overdue:
            return _Result(done=False, applies=False)
        return _Result(
            done=overdue == 0,
            detail=f"{overdue} past due, {open_} open"
            if overdue
            else f"{open_} open, none past due",
        )
    if fw is not None:
        a = facts.assurance.get(fw.code)
        if key == "live":
            today = datetime.now(UTC).date()
            if fw.live_date is None:
                return _Result(done=False)
            return _Result(done=fw.live_date <= today, detail=f"Live on {fw.live_date}")
        if key == "description":
            return _Result(done=bool(facts.description_approved))
        if key == "internal_audit":
            return _Result(done=bool(a and a.internal_audit_reported))
        if key == "management_review":
            return _Result(done=bool(a and a.review_minuted))
        if key == "next_cycle":
            # Shown once this cycle's report or certificate is in hand (GS-13); starting the
            # next cycle makes a new current engagement, and the step leaves with it.
            return _Result(done=False, applies=facts.issued.get(fw.code, False))
        if key == "audit":
            if a is None or not a.audit_recorded:
                return _Result(done=False)
            waiting = a.findings_open + a.majors_unverified
            return _Result(
                done=waiting == 0,
                detail=f"{a.findings_open} findings open" if a.findings_open else None,
            )
        if key == "report":
            # A decision of Security alone is a decision: an empty category list is valid
            # once the engagement exists (this read never ticked before). A Type 2 cannot
            # be saved without both period dates, so there is no separate period step.
            return _Result(done=fw.scope_set and fw.audit_type is not None)
        if key == "auditor":
            # Still deciding is an answer: it shows as in progress and never blocks.
            if fw.assessor == "chosen":
                return _Result(done=True, detail=fw.certification_body)
            if fw.assessor == "undecided":
                return _Result(done=False, done_count=0, detail="Still deciding")
            return _Result(done=False)
        if key == "scope_statement":
            # EN-11: written is not enough; a named member approves the wording.
            if fw.scope_statement_set and not fw.scope_statement_approved:
                return _Result(done=False, done_count=0, detail="Waiting for approval")
            return _Result(done=fw.scope_statement_set and fw.scope_statement_approved)
        if key == "applicability":
            return _count(fw.decisions_reviewed, fw.decisions_total, "decisions reviewed")
    return _Result(done=False)


class OnboardingService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service

    # -- facts -------------------------------------------------------------------

    async def _facts(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, principal: Principal
    ) -> tuple[_Facts, list[str]]:
        can = principal.has
        profile = security = own_mfa = members = program = risks = connected = None
        codes: list[str] = []
        if can("tenant:read"):
            profile = await tenancy_service.get_own_company_profile(session, tenant_id)
            settings = await iam_service.get_security_settings(session, tenant_id)
            security = settings.require_admin_mfa
        # Members are read for the caller's own two factor state in every case; the count
        # is only shown to someone who may read the member list.
        member_rows = await iam_service.list_members(session, tenant_id=tenant_id)
        own_mfa = next(
            (m.mfa_enabled for m in member_rows if m.membership_id == principal.membership_id),
            False,
        )
        if can("members:read"):
            members = sum(1 for m in member_rows if m.status == "active")
        if can("frameworks:read"):
            views = await framework_service.list_for_tenant(session, tenant_id=tenant_id)
            codes = [v.code for v in sorted(views, key=lambda v: v.position) if v.added]
            program = await engagement_service.program_figures(
                session, tenant_id=tenant_id, framework_codes=codes
            )
        functions = None
        documents = None
        suggestions = baseline = plan = None
        if can("frameworks:read"):
            functions = await ownership_service.assigned_count(session, tenant_id=tenant_id)
            proposals = await proposals_service.view(session, tenant_id=tenant_id)
            suggestions = (
                proposals.open,
                proposals.review_needed,
                sum(1 for p in proposals.proposals if p.state in {"accepted", "rejected"}),
            )
            base = await plan_service.baseline(session, tenant_id=tenant_id)
            baseline = (base.status, base.answered, base.total)
            work = await plan_service.plan(session, tenant_id=tenant_id)
            plan = (len(work.items), sum(1 for i in work.items if i.raised))
        description_approved = None
        if can("documents:read") and can("frameworks:read"):
            required = await self.required_documents(session, tenant_id=tenant_id)
            documents = (required.counted, required.approved, required.in_review)
            description_approved = any(
                r.template == "soc2-system-description" and r.state == "approved"
                for r in required.rows
            )
        assurance = {}
        issued: dict[str, bool] = {}
        objectives = None
        if can("frameworks:read"):
            objectives = await objectives_service.progress(session, tenant_id=tenant_id)
            for code in codes:
                assurance[code] = await assurance_service.summary(
                    session, tenant_id=tenant_id, framework_code=code
                )
                dates = await programme_service.milestones(
                    session, tenant_id=tenant_id, framework_code=code
                )
                issued[code] = any(
                    m.kind in {"report_issued", "decision"} and m.actual_on is not None
                    for m in dates
                )
        if can("risks:read"):
            risks = await risk_service.assessment_counts(session, tenant_id=tenant_id)
        if can("connectors:read"):
            connected = await connector_service.connected_count(session, tenant_id=tenant_id)
        facts = _Facts(
            profile=profile,
            security_require_admin_mfa=security,
            own_mfa=own_mfa,
            active_members=members,
            program=program,
            risks=risks,
            connected=connected,
            member_names={m.membership_id: m.full_name for m in member_rows},
            functions_assigned=functions,
            documents=documents,
            suggestions=suggestions,
            baseline=baseline,
            plan=plan,
            assurance=assurance,
            description_approved=description_approved,
            issued=issued,
            objectives=objectives,
        )
        return facts, codes

    async def _open_skips(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[str, OnboardingStepSkip]:
        rows = (
            await session.execute(
                select(OnboardingStepSkip).where(
                    OnboardingStepSkip.tenant_id == tenant_id,
                    OnboardingStepSkip.reopened_at.is_(None),
                )
            )
        ).scalars()
        return {row.step_key: row for row in rows}

    # -- status ------------------------------------------------------------------

    async def status(  # noqa: PLR0912 — one branch per step state and permission
        self, session: AsyncSession, *, tenant_id: uuid.UUID, principal: Principal
    ) -> StatusView:
        facts, codes = await self._facts(session, tenant_id=tenant_id, principal=principal)
        skips = await self._open_skips(session, tenant_id)
        names = facts.member_names
        frameworks = facts.program.frameworks if facts.program else []
        steps: list[StepView] = []
        for step in STEPS:
            targets: list[FrameworkFigures | None]
            if step.each is None:
                targets = [None]
            else:
                targets = [f for f in frameworks if step.each in {"any", f.scope_model}]
                if not principal.has(step.read):
                    # Without the read there is no way to know which frameworks run; show
                    # the step once, as not permitted.
                    targets = [None]
            for fw in targets:
                key = f"{step.key}:{fw.code}" if fw else step.key
                link = step.link.replace("{framework}", fw.code if fw else "")
                if not principal.has(step.read):
                    steps.append(
                        StepView(
                            key=key,
                            step=step.key,
                            phase=step.phase,
                            title=step.title,
                            framework_code=fw.code if fw else None,
                            frameworks=[],
                            state="not_permitted",
                            done_count=None,
                            total_count=None,
                            detail=None,
                            link=link,
                            can_act=False,
                        )
                    )
                    continue
                result = _rule(step, facts, fw)
                if not result.applies:
                    continue
                skip = skips.get(key)
                if result.done:
                    state = "done"
                elif skip is not None:
                    state = "skipped"
                elif result.done_count or result.detail in {
                    "Still deciding",
                    "Waiting for approval",
                }:
                    state = "in_progress"
                else:
                    state = "not_started"
                steps.append(
                    StepView(
                        key=key,
                        step=step.key,
                        phase=step.phase,
                        title=step.title,
                        framework_code=fw.code if fw else None,
                        frameworks=[fw.code] if fw else self._shared_chips(step, codes),
                        state=state,
                        done_count=result.done_count,
                        total_count=result.total_count,
                        detail=result.detail,
                        link=link,
                        can_act=principal.has(step.act),
                        skip=(
                            SkipView(
                                by_membership_id=skip.skipped_by_membership_id,
                                by_name=names.get(skip.skipped_by_membership_id)
                                if skip.skipped_by_membership_id
                                else None,
                                at=skip.created_at,
                                reason=skip.reason,
                            )
                            if skip is not None and state == "skipped"
                            else None
                        ),
                    )
                )
        plans: dict[str, list[MilestoneView]] = {}
        if principal.has("frameworks:read"):
            for f in frameworks:
                plans[f.code] = await programme_service.milestones(
                    session, tenant_id=tenant_id, framework_code=f.code
                )
        return StatusView(
            frameworks=frameworks if principal.has("frameworks:read") else None,
            steps=steps,
            next_key=self._next(steps, self._nearest_framework(plans)),
            milestones=plans,
            controls_total=facts.program.controls_total if facts.program else None,
            checks_failing=facts.program.checks_failing if facts.program else None,
            phases=list(PHASES),
        )

    @staticmethod
    def _shared_chips(step: StepDef, codes: list[str]) -> list[str]:
        """A shared step counts for every framework the workspace runs, except the ones
        about the workspace itself rather than any programme."""
        if step.key in {"profile", "own_mfa", "admin_mfa", "invite"}:
            return []
        return list(codes)

    @staticmethod
    def _nearest_framework(plans: dict[str, list[MilestoneView]]) -> str | None:
        """The framework whose next planned date comes first, if any date is planned."""
        today = datetime.now(UTC).date()
        upcoming = [
            (m.planned_on, code)
            for code, plan in plans.items()
            for m in plan
            if m.planned_on is not None and m.planned_on >= today and m.actual_on is None
        ]
        return min(upcoming)[1] if upcoming else None

    @staticmethod
    def _next(steps: list[StepView], nearest: str | None = None) -> str | None:
        """The open step that blocks the nearest dated milestone (GS-8): with a date planned,
        the first open step the caller can act on that belongs to that framework or is shared;
        else the first open step the caller can act on; else the first open step at all."""
        open_steps = [s for s in steps if s.state in {"not_started", "in_progress"}]
        if nearest is not None:
            for s in open_steps:
                if s.can_act and s.framework_code == nearest:
                    return s.key
        actionable = next((s for s in open_steps if s.can_act), None)
        chosen = actionable or (open_steps[0] if open_steps else None)
        return chosen.key if chosen else None

    async def scope_notes(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> list[str]:
        """Control codes no requirement in the current scope needs (CL-7): with SOC 2 that is a
        category not elected, with ISO 27001 a requirement excluded. Only said once every active
        framework's scope is decided; until then every control may be needed."""
        from verity.modules.compliance.control_service import control_service  # noqa: PLC0415

        codes = [
            v.code
            for v in await framework_service.list_for_tenant(session, tenant_id=tenant_id)
            if v.added
        ]
        keys: set[str] = set()
        for code in codes:
            criteria = await engagement_service.criteria_in_scope(
                session, tenant_id=tenant_id, framework_code=code
            )
            if not criteria:
                return []
            keys |= {r.requirement_key for r in criteria}
        return sorted(
            c.code
            for c in await control_service.list_controls(session, tenant_id=tenant_id)
            if c.requirement_keys and not keys.intersection(c.requirement_keys)
        )

    async def profile_prefill(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[PrefillItem]:
        """Answers the workspace already implies, for questions not answered yet (PR-7): people
        from the member list, identity provider, hosting and code hosting from active
        connections. Offered for a person to confirm; never saved here, nothing fetched outside."""
        profile = await tenancy_service.get_own_company_profile(session, tenant_id)
        answers = profile.answers or {}
        out: list[PrefillItem] = []
        members = [
            m
            for m in await iam_service.list_members(session, tenant_id=tenant_id)
            if m.status == "active"
        ]
        if "headcount_band" not in answers and members:
            n = len(members)
            band = next(b for limit, b in _BANDS if n <= limit)
            out.append(PrefillItem("headcount_band", band, "From your member list, at least"))
        connected = await connector_service.connected_keys(session, tenant_id=tenant_id)
        idp = next((v for k, v in _IDP_FROM.items() if k in connected), None)
        if "identity_provider" not in answers and idp:
            out.append(PrefillItem("identity_provider", idp, "From your connections"))
        hosting = [v for k, v in _HOSTING_FROM.items() if k in connected]
        if "hosting_providers" not in answers and hosting:
            out.append(PrefillItem("hosting_providers", hosting, "From your connections"))
        if "builds_software" not in answers and connected & {"github", "gitlab"}:
            out.append(PrefillItem("builds_software", "yes", "From your connections"))
        return out

    async def my_part(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, membership_id: uuid.UUID
    ) -> MyPartView:
        """The open items assigned to one person, grouped (GS-12): tasks and evidence requests,
        documents waiting for their approval, and documents waiting for their acknowledgement."""
        from verity.modules.documents.service import document_service  # noqa: PLC0415
        from verity.modules.tasks.service import TaskFilters, task_service  # noqa: PLC0415

        tasks, _ = await task_service.list_tasks(
            session,
            tenant_id=tenant_id,
            filters=TaskFilters(
                assignee=str(membership_id),
                statuses=("open", "in_progress", "blocked", "under_review"),
            ),
            page_size=50,
            caller_membership_id=membership_id,
        )
        approvals = await document_service.my_pending_approvals(
            session, tenant_id=tenant_id, membership_id=membership_id
        )
        campaigns = await document_service.my_pending_campaigns(
            session, tenant_id=tenant_id, membership_id=membership_id
        )
        return MyPartView(
            items=[
                *(
                    MyItem("approve", f"Approve {a.document_title}", f"/documents/{a.document_id}")
                    for a in approvals
                ),
                *(
                    MyItem(
                        "acknowledge",
                        f"Read and sign {c.document_title}",
                        f"/documents/{c.document_id}",
                    )
                    for c in campaigns
                ),
                *(MyItem("task", f"{t.code} {t.title}", f"/tasks/{t.id}") for t in tasks),
            ]
        )

    async def required_documents(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> RequiredView:
        """The Required documents list, with the facts it depends on gathered here so the
        documents module reads only its own tables."""
        profile = await tenancy_service.get_own_company_profile(session, tenant_id)
        frameworks = {
            v.code
            for v in await framework_service.list_for_tenant(session, tenant_id=tenant_id)
            if v.added
        }
        soc2 = (
            await engagement_service.get(session, tenant_id=tenant_id, framework_code="SOC2")
            if "SOC2" in frameworks
            else None
        )
        return await required_documents_service.view(
            session,
            tenant_id=tenant_id,
            answers=dict(profile.answers or {}),
            frameworks=frameworks,
            soc2_categories=category_keys(soc2.categories_in_scope) if soc2 else set(),
        )

    # -- skip and reopen ---------------------------------------------------------

    @staticmethod
    def _check_key(step_key: str) -> None:
        base, _, framework = step_key.partition(":")
        if base not in STEP_KEYS or (framework and len(framework) > 40):  # noqa: PLR2004
            raise NotFound("That step does not exist.", detail=f"step {step_key!r}")

    async def skip(  # noqa: PLR0913 — who, where, which step and why
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        membership_id: uuid.UUID,
        step_key: str,
        reason: str,
    ) -> OnboardingStepSkip:
        self._check_key(step_key)
        cleaned = reason.strip()
        if not cleaned:
            raise InvalidInput("Say why you are skipping this step.", detail="empty reason")
        if len(cleaned) > REASON_MAX:
            raise InvalidInput(
                f"Keep the reason under {REASON_MAX} characters.", detail="reason too long"
            )
        open_skips = await self._open_skips(session, tenant_id)
        if step_key in open_skips:
            raise Conflict("This step is already skipped.", detail=f"step {step_key!r}")
        row = OnboardingStepSkip(
            id=uuid7(),
            tenant_id=tenant_id,
            step_key=step_key,
            reason=cleaned,
            skipped_by_membership_id=membership_id,
        )
        session.add(row)
        await session.flush()
        await self._audit.record(
            session,
            action="create",
            object_type=OBJECT_TYPE,
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"step_key": step_key, "reason": cleaned},
        )
        return row

    async def reopen(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        membership_id: uuid.UUID,
        step_key: str,
    ) -> None:
        self._check_key(step_key)
        row = (await self._open_skips(session, tenant_id)).get(step_key)
        if row is None:
            raise NotFound("This step is not skipped.", detail=f"step {step_key!r}")
        row.reopened_at = datetime.now(UTC)
        row.reopened_by_membership_id = membership_id
        await session.flush()
        await self._audit.record(
            session,
            action="update",
            object_type=OBJECT_TYPE,
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"step_key": step_key, "reopened_at": None},
            after={"step_key": step_key, "reopened_at": row.reopened_at.isoformat()},
        )


onboarding_service = OnboardingService()
