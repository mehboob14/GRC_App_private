"""Assessment objectives for a workspace (guided onboarding AO-1 to AO-5).

Reads the sealed objectives pack and the workspace's own state through each module's service,
and derives, per request, every artifact's state, every objective's outcome, each control's
design and operating readiness, the next step for anything not satisfied, the Type 1 and Stage 1
views, and a comparison with today's readiness. Nothing here changes readiness: the switch waits
for the owner's choice of automation rule (AO-3), which the comparison report informs.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.modules.audit.service import Actor, AuditService, audit_service
from verity.modules.compliance.control_service import ControlView, control_service
from verity.modules.compliance.engagement_service import engagement_service
from verity.modules.compliance.framework_service import framework_service
from verity.modules.compliance.programme_service import programme_service
from verity.modules.compliance.readiness import BUILT_IN_SOURCE, control_ready
from verity.modules.connectors.service import connector_service
from verity.modules.documents.service import document_service
from verity.modules.evidence.service import evidence_service
from verity.modules.objectives import pack
from verity.modules.objectives.models import EvidenceArtifact, ObjectiveDecision
from verity.modules.objectives.outcomes import (
    ArtifactState,
    Facts,
    Rule,
    artifact_state,
    control_readiness,
    objective_outcome,
    required_artifacts,
)
from verity.modules.onboarding.owner_functions import FUNCTIONS
from verity.shared.ids import uuid7

REASON_MAX: Final = 1000
_FUNCTION_LABELS: Final[dict[str, str]] = dict(FUNCTIONS)
_DOC_LINK: Final = "/documents/required"


@dataclass(frozen=True, slots=True)
class NextStep:
    action: str
    """assign_owner, start_document, upload, connect, fix, decide."""
    label: str
    link: str
    artifact_key: str | None = None


@dataclass(frozen=True, slots=True)
class ArtifactView:
    key: str
    code: str
    name: str
    category: str
    state: str
    reason: str | None
    sources: list[str]
    """person, document or check, for display."""


@dataclass(frozen=True, slots=True)
class ObjectiveView:
    code: str
    key: str
    statement: str
    assurance: str
    methods: list[str]
    interview_with: list[str]
    """The owner functions an auditor would interview, by label."""
    outcome: str
    reason: str | None
    artifacts: list[ArtifactView]
    next_step: NextStep | None
    not_applicable_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ControlObjectivesView:
    control_id: uuid.UUID
    code: str
    name: str
    frameworks: list[str]
    objectives: list[ObjectiveView]
    design_ready: bool
    operating_ready: bool
    ready: bool
    """Implemented, and every applicable objective satisfied (under rule B)."""
    ready_today: bool
    """Today's rule: implemented, current evidence, no automated test against it."""
    review_status: str


@dataclass(frozen=True, slots=True)
class FrameworkObjectives:
    code: str
    name: str
    audit_type: str | None
    controls: int
    design_ready: int
    operating_ready: int
    objectives_total: int
    objectives_satisfied: int
    first_audit_ready: int
    """Type 1 (SOC 2) or Stage 1 (ISO): controls whose design objectives are satisfied."""
    first_audit_label: str
    first_audit_notes: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class OverviewView:
    frameworks: list[FrameworkObjectives]
    controls_with_objectives: int
    controls_total: int
    next: list[tuple[ControlObjectivesView, ObjectiveView]]
    review_status: str


@dataclass(frozen=True, slots=True)
class ComparisonRow:
    control_id: uuid.UUID
    code: str
    name: str
    ready_today: bool
    ready_rule_a: bool
    ready_rule_b: bool
    blocking: list[str]
    """Objective codes not satisfied under rule B."""


@dataclass(frozen=True, slots=True)
class ComparisonView:
    rows: list[ComparisonRow]
    compared: int
    differ_rule_a: int
    differ_rule_b: int


@dataclass
class _State:
    controls: list[ControlView]
    facts: Facts
    decisions: dict[str, ObjectiveDecision]
    today: dict[uuid.UUID, bool]
    frameworks: dict[str, str]
    """Active framework code to name."""


def _frameworks_of(control: ControlView, active: dict[str, str]) -> list[str]:
    prefixes = {k.split(":", 1)[0] for k in control.requirement_keys}
    return [code for code in active if code in prefixes]


class ObjectivesService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service

    # -- facts -----------------------------------------------------------------------

    async def _state(self, session: AsyncSession, tenant_id: uuid.UUID) -> _State:
        controls = await control_service.list_controls(session, tenant_id=tenant_id)
        tags = list(
            (
                await session.execute(
                    select(EvidenceArtifact).where(
                        EvidenceArtifact.tenant_id == tenant_id,
                        EvidenceArtifact.removed_at.is_(None),
                    )
                )
            ).scalars()
        )
        currency = await evidence_service.currency(
            session, tenant_id, [t.evidence_id for t in tags]
        )
        tagged: dict[str, list[str]] = defaultdict(list)
        for t in tags:
            if t.evidence_id in currency:
                tagged[t.artifact_key].append(currency[t.evidence_id])
        decisions = {
            d.objective_code: d
            for d in (
                await session.execute(
                    select(ObjectiveDecision).where(
                        ObjectiveDecision.tenant_id == tenant_id,
                        ObjectiveDecision.withdrawn_at.is_(None),
                    )
                )
            ).scalars()
        }
        with_current = await evidence_service.control_ids_with_current_evidence(
            session, tenant_id, exclude_source=BUILT_IN_SOURCE
        )
        automation = await connector_service.automation_statuses(session, tenant_id=tenant_id)
        today = {
            c.id: control_ready(
                status=c.status,
                has_current_evidence=c.id in with_current,
                automation=automation.get(c.id),
            )
            for c in controls
        }
        active = {
            v.code: v.name
            for v in sorted(
                await framework_service.list_for_tenant(session, tenant_id=tenant_id),
                key=lambda v: v.position,
            )
            if v.added
        }
        facts = Facts(
            check_states=await connector_service.check_states(session, tenant_id=tenant_id),
            tagged=dict(tagged),
            approved_templates=frozenset(
                await document_service.approved_template_keys(session, tenant_id=tenant_id)
            ),
        )
        return _State(controls, facts, decisions, today, active)

    # -- views -----------------------------------------------------------------------

    @staticmethod
    def _next_step(
        control: ControlView,
        objective: dict[str, Any],
        states: dict[str, ArtifactState],
        artifacts: dict[str, dict[str, Any]],
        facts: Facts,
    ) -> NextStep | None:
        """The one thing to do next for an objective not satisfied (AO-4)."""
        if control.owner_membership_id is None:
            return NextStep(
                "assign_owner", "Name an owner for this control", f"/controls/{control.id}"
            )
        for key in required_artifacts(objective):
            state = states.get(key)
            if state is None or state.state == "satisfied":
                continue
            artifact = artifacts[key]
            for source in artifact.get("sources", []):
                kind = source.get("kind")
                if kind == "document":
                    return NextStep(
                        "start_document",
                        f"Get {artifact['name']} approved",
                        _DOC_LINK,
                        key,
                    )
                if kind == "check":
                    checks = [facts.check_states.get(k, "not_available") for k in source["checks"]]
                    if "fail" in checks:
                        return NextStep(
                            "fix",
                            "Fix what the automated check found",
                            f"/controls/{control.id}",
                            key,
                        )
                    if any(s in {"not_connected", "pending"} for s in checks) and not any(
                        s.get("kind") == "person" for s in artifact["sources"]
                    ):
                        return NextStep(
                            "connect", "Connect the system that runs this check", "/connectors", key
                        )
                if kind == "person":
                    return NextStep(
                        "upload",
                        f"Upload {artifact['name'].lower()} and mark it as this record",
                        f"/controls/{control.id}?tab=evidence",
                        key,
                    )
        return None

    def _control(
        self, control: ControlView, st: _State, rule: Rule = "B"
    ) -> ControlObjectivesView | None:
        artifacts, by_control = pack.load()
        items = by_control.get(control.code)
        if not items:
            return None
        keys = {k for o in items for m in o["methods"] for k in m["artifacts"]}
        states = {k: artifact_state(artifacts[k], st.facts, rule) for k in keys}
        views: list[ObjectiveView] = []
        pairs: list[tuple[str, str]] = []
        for o in items:
            decision = st.decisions.get(o["code"])
            outcome, reason = objective_outcome(o, states, not_applicable=decision is not None)
            pairs.append((o["assurance"], outcome))
            views.append(
                ObjectiveView(
                    code=o["code"],
                    key=o["key"],
                    statement=o["statement"],
                    assurance=o["assurance"],
                    methods=[m["method"] for m in o["methods"]],
                    interview_with=[
                        _FUNCTION_LABELS.get(m.get("who", ""), m.get("who", ""))
                        for m in o["methods"]
                        if m["method"] == "interview" and m.get("who")
                    ],
                    outcome=outcome,
                    reason=reason,
                    artifacts=[
                        ArtifactView(
                            key=k,
                            code=artifacts[k]["code"],
                            name=artifacts[k]["name"],
                            category=artifacts[k]["category"],
                            state=states[k].state,
                            reason=states[k].reason,
                            sources=[s["kind"] for s in artifacts[k]["sources"]],
                        )
                        for k in required_artifacts(o)
                    ],
                    next_step=None
                    if outcome in {"satisfied", "not_applicable"}
                    else self._next_step(control, o, states, artifacts, st.facts),
                    not_applicable_reason=decision.reason if decision else None,
                )
            )
        design, operating, ready = control_readiness(control.status, pairs)
        return ControlObjectivesView(
            control_id=control.id,
            code=control.code,
            name=control.name,
            frameworks=_frameworks_of(control, st.frameworks),
            objectives=views,
            design_ready=design,
            operating_ready=operating,
            ready=ready,
            ready_today=st.today.get(control.id, False),
            review_status=str(pack.manifest().get("review_status", "draft_unreviewed")),
        )

    async def for_control(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, control_id: uuid.UUID
    ) -> ControlObjectivesView | None:
        st = await self._state(session, tenant_id)
        control = next((c for c in st.controls if c.id == control_id), None)
        if control is None:
            raise NotFound("That control is not in this workspace.", detail=str(control_id))
        return self._control(control, st)

    async def _first_audit(
        self, session: AsyncSession, tenant_id: uuid.UUID, code: str
    ) -> tuple[str | None, str, list[str]]:
        """The engagement's audit type, the first audit's label, and its extra conditions (AO-5)."""
        engagement = await engagement_service.get(session, tenant_id=tenant_id, framework_code=code)
        audit_type = engagement.audit_type if engagement else None
        if audit_type in {"type_1", "type_2"} or (engagement is None and code == "SOC2"):
            notes = (
                ["Operating objectives need evidence across the whole period."]
                if audit_type == "type_2"
                else ["Operating objectives need one current instance each."]
            )
            return audit_type, "Type 1 design", notes
        plan = await programme_service.milestones(session, tenant_id=tenant_id, framework_code=code)
        planned = {m.kind for m in plan if m.planned_on or m.actual_on}
        notes = [
            "Internal audit planned" if "internal_audit" in planned else "Plan the internal audit",
            "Management review planned"
            if "management_review" in planned
            else "Plan the management review",
        ]
        return audit_type, "Stage 1 design", notes

    async def overview(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> OverviewView:
        st = await self._state(session, tenant_id)
        views = [v for c in st.controls if (v := self._control(c, st)) is not None]
        frameworks: list[FrameworkObjectives] = []
        for code, name in st.frameworks.items():
            mine = [v for v in views if code in v.frameworks]
            objectives = [o for v in mine for o in v.objectives if o.outcome != "not_applicable"]
            audit_type, label, notes = await self._first_audit(session, tenant_id, code)
            frameworks.append(
                FrameworkObjectives(
                    code=code,
                    name=name,
                    audit_type=audit_type,
                    controls=len(mine),
                    design_ready=sum(1 for v in mine if v.design_ready),
                    operating_ready=sum(1 for v in mine if v.operating_ready),
                    objectives_total=len(objectives),
                    objectives_satisfied=sum(1 for o in objectives if o.outcome == "satisfied"),
                    first_audit_ready=sum(1 for v in mine if v.design_ready),
                    first_audit_label=label,
                    first_audit_notes=notes,
                )
            )
        waiting = [
            (v, o)
            for v in sorted(views, key=lambda v: (v.code.split("-")[0] != "GOV", v.code))
            for o in v.objectives
            if o.next_step is not None
        ]
        # Design first: an auditor reads the written procedure before testing its operation.
        waiting.sort(key=lambda p: p[1].assurance != "design")
        return OverviewView(
            frameworks=frameworks,
            controls_with_objectives=len(views),
            controls_total=len(st.controls),
            next=waiting[:25],
            review_status=str(pack.manifest().get("review_status", "draft_unreviewed")),
        )

    async def comparison(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> ComparisonView:
        """Every control with objectives, readiness today beside readiness under each rule
        (AO-3). The rows that differ are what the owner reviews before any switch."""
        st = await self._state(session, tenant_id)
        rows: list[ComparisonRow] = []
        for c in st.controls:
            b = self._control(c, st, "B")
            a = self._control(c, st, "A")
            if a is None or b is None:
                continue
            rows.append(
                ComparisonRow(
                    control_id=c.id,
                    code=c.code,
                    name=c.name,
                    ready_today=b.ready_today,
                    ready_rule_a=a.ready,
                    ready_rule_b=b.ready,
                    blocking=[
                        o.code
                        for o in b.objectives
                        if o.outcome not in {"satisfied", "not_applicable"}
                    ],
                )
            )
        rows.sort(key=lambda r: (r.ready_today == r.ready_rule_b, r.code))
        return ComparisonView(
            rows=rows,
            compared=len(rows),
            differ_rule_a=sum(1 for r in rows if r.ready_today != r.ready_rule_a),
            differ_rule_b=sum(1 for r in rows if r.ready_today != r.ready_rule_b),
        )

    async def progress(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> tuple[int, int]:
        """``(satisfied, applicable)`` objectives across the workspace, for Get Started."""
        st = await self._state(session, tenant_id)
        done = total = 0
        for c in st.controls:
            v = self._control(c, st)
            if v is None or not v.frameworks:
                continue
            for o in v.objectives:
                if o.outcome == "not_applicable":
                    continue
                total += 1
                done += o.outcome == "satisfied"
        return done, total

    # -- what a person records --------------------------------------------------------

    @staticmethod
    def _objective(code: str) -> dict[str, Any]:
        _, by_control = pack.load()
        control = code.split(".", 1)[0]
        found = next((o for o in by_control.get(control, []) if o["code"] == code), None)
        if found is None:
            raise NotFound("That objective does not exist.", detail=f"objective {code!r}")
        return found

    async def mark_not_applicable(  # noqa: PLR0913 — who, which objective and why
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        membership_id: uuid.UUID,
        objective_code: str,
        reason: str,
    ) -> None:
        self._objective(objective_code)
        cleaned = reason.strip()
        if not cleaned:
            raise InvalidInput("Say why this does not apply.", detail="empty reason")
        if len(cleaned) > REASON_MAX:
            raise InvalidInput(f"Keep the reason under {REASON_MAX} characters.", detail="long")
        open_ = (
            await session.execute(
                select(ObjectiveDecision).where(
                    ObjectiveDecision.tenant_id == tenant_id,
                    ObjectiveDecision.objective_code == objective_code,
                    ObjectiveDecision.withdrawn_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if open_ is not None:
            raise Conflict("This objective is already marked not applicable.", detail="exists")
        row = ObjectiveDecision(
            id=uuid7(),
            tenant_id=tenant_id,
            objective_code=objective_code,
            reason=cleaned,
            decided_by_membership_id=membership_id,
        )
        session.add(row)
        await session.flush([row])
        await self._audit.record(
            session,
            action="create",
            object_type="objective_decision",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"objective_code": objective_code, "reason": cleaned},
        )

    async def withdraw(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        membership_id: uuid.UUID,
        objective_code: str,
    ) -> None:
        row = (
            await session.execute(
                select(ObjectiveDecision).where(
                    ObjectiveDecision.tenant_id == tenant_id,
                    ObjectiveDecision.objective_code == objective_code,
                    ObjectiveDecision.withdrawn_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFound("This objective is not marked not applicable.", detail=objective_code)
        row.withdrawn_at = datetime.now(UTC)
        row.withdrawn_by_membership_id = membership_id
        await session.flush([row])
        await self._audit.record(
            session,
            action="update",
            object_type="objective_decision",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"objective_code": objective_code, "withdrawn": False},
            after={"objective_code": objective_code, "withdrawn": True},
        )

    async def tag_evidence(  # noqa: PLR0913 — who, which evidence, which artifact, on or off
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        membership_id: uuid.UUID,
        evidence_id: uuid.UUID,
        artifact_key: str,
        on: bool,
    ) -> None:
        """Say an evidence row is (or is no longer) a given artifact."""
        artifacts, _ = pack.load()
        if artifact_key not in artifacts:
            raise NotFound("That record type does not exist.", detail=artifact_key)
        if not any(s["kind"] == "person" for s in artifacts[artifact_key]["sources"]):
            raise InvalidInput(
                "This record comes from a system or an approved document, not an upload.",
                detail=f"artifact {artifact_key} takes no person evidence",
            )
        if evidence_id not in await evidence_service.currency(session, tenant_id, [evidence_id]):
            raise NotFound("That evidence is not in this workspace.", detail=str(evidence_id))
        row = (
            await session.execute(
                select(EvidenceArtifact).where(
                    EvidenceArtifact.tenant_id == tenant_id,
                    EvidenceArtifact.evidence_id == evidence_id,
                    EvidenceArtifact.artifact_key == artifact_key,
                    EvidenceArtifact.removed_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if on and row is None:
            row = EvidenceArtifact(
                id=uuid7(),
                tenant_id=tenant_id,
                evidence_id=evidence_id,
                artifact_key=artifact_key,
                tagged_by_membership_id=membership_id,
            )
            session.add(row)
            action: Literal["create", "update"] = "create"
        elif not on and row is not None:
            row.removed_at = datetime.now(UTC)
            action = "update"
        else:
            return
        await session.flush([row])
        await self._audit.record(
            session,
            action=action,
            object_type="evidence_artifact",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"evidence_id": str(evidence_id), "artifact_key": artifact_key, "on": on},
        )


objectives_service = ObjectivesService()
