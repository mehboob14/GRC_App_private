"""The twelve-stage lifecycle — the stage list, the exit rules, and the machine.

Pure: no session, no I/O. The service assembles ``StageFacts`` from the database
and this module decides what they mean, so every rule below is unit-testable
against synthetic facts and none of them can accidentally query.

**The lifecycle is data, not code** (ER ¶101): the twelve stages are rows in
``vendor_stages``, one set per engagement per cycle. What lives here is the
vocabulary, the exit rule per stage, and the three transitions — the things that
would be a `switch` in three files if they lived at the call sites.

**`approval` is the only gate (V2).** The ER's `is_gate` annotation names tiering
too, and ER ¶101 defines a gate as needing an approval record to exit — which
reads wrong for a calculation. So `tiering` is *required but not a gate*: it can
never be skipped, and it exits on "a tier has been computed" rather than on a
four-valued sign-off. Both sentences are satisfied without forcing a ceremony
onto arithmetic.

**A check that cannot be answered yet is not a check that passed.** Six stages
depend on tables that sections 3 and 4 build. Their rules are written and tested
here, and report ``satisfied=None`` until the facts exist — the same distinction
rule 7 draws between `error` and `fail`. A pending check never blocks an advance,
and it never renders as a tick either.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Final

# Spec ¶81 order. Index is progress: a send-back may only target a lower index.
STAGES: Final[tuple[str, ...]] = (
    "intake",
    "tiering",
    "diligence",
    "questionnaire",
    "scoring",
    "findings",
    "contracting",
    "approval",
    "onboarding",
    "monitoring",
    "reassessment",
    "offboarding",
)

STAGE_LABELS: Final[dict[str, str]] = {
    "intake": "Intake",
    "tiering": "Tiering",
    "diligence": "Diligence",
    "questionnaire": "Questionnaire",
    "scoring": "Scoring",
    "findings": "Findings",
    "contracting": "Contracting",
    "approval": "Approval",
    "onboarding": "Onboarding",
    "monitoring": "Monitoring",
    "reassessment": "Reassessment",
    "offboarding": "Offboarding",
}

GATES: Final[frozenset[str]] = frozenset({"approval"})
"""V2. A gate exits only on an approval decided for the current attempt, and a
database CHECK refuses to mark one skipped."""

REQUIRED_STAGES: Final[frozenset[str]] = frozenset({"intake", "tiering", "approval"})
"""Never skippable by any tier. ``tiering`` is here rather than in GATES — that is
the whole of V2."""

TERMINAL_STAGE: Final = "offboarding"
STEADY_STATE_STAGE: Final = "monitoring"
"""``monitoring`` never exits forward on its own; a signal or a due reassessment
moves it. Counting it as blocked would make every healthy vendor look stuck."""

STAGE_STATUSES: Final[tuple[str, ...]] = ("not_started", "in_progress", "complete", "skipped")
TRANSITION_ACTIONS: Final[tuple[str, ...]] = ("advance", "send_back", "skip")

# V9. A gate or a required stage is never in a skip list regardless of tier, and
# _skips_for enforces that rather than trusting the table.
DEFAULT_SKIP_MATRIX: Final[dict[str, tuple[str, ...]]] = {
    "critical": (),
    "high": (),
    "medium": ("diligence",),
    "low": ("diligence", "questionnaire", "scoring", "findings"),
}

DEFAULT_CADENCE_DAYS: Final[dict[str, int]] = {
    "critical": 180,
    "high": 365,
    "medium": 730,
    "low": 1095,
}

DEFAULT_REVIEWER_ROLES: Final[dict[str, tuple[str, ...]]] = {
    "critical": ("security", "privacy", "legal"),
    "high": ("security", "legal"),
    "medium": ("security",),
    "low": (),
}
"""Spec ¶82's "required reviewers", sized by tier. Roles, not people: a role is
resolved to a person through ``vendor_team_roster``, which is why this needs no
table of its own."""


def skips_for(
    tier: str | None, matrix: Mapping[str, Sequence[str]] | None = None
) -> frozenset[str]:
    """Which stages this tier skips, with gates and required stages removed.

    The removal is not belt-and-braces. ``vendor_tiering_policies`` is a tenant-
    editable row, so a customer could put ``approval`` in a skip list; spec ¶82
    says approval gates are never skipped, and that must hold against the data as
    configured, not only against the data as intended.
    """
    matrix = matrix or DEFAULT_SKIP_MATRIX
    candidates = set(matrix.get(tier or "", ()))
    return frozenset(candidates - GATES - REQUIRED_STAGES)


@dataclass(frozen=True, slots=True)
class ExitCheck:
    """One condition a stage must meet, in the shape the checklist row renders.

    ``satisfied`` is deliberately three-valued: ``True`` passed, ``False`` blocks,
    and ``None`` means the module that would answer it has not been built yet. A
    monitoring surface where "we checked and it is fine" looks like "we did not
    check" is worse than no surface.
    """

    code: str
    label: str
    satisfied: bool | None
    detail: str | None = None
    clears_with: str | None = None
    """The object type that clears this, so the interface can link straight to it
    rather than saying "2 blockers" and leaving the reader to find them."""
    clears_id: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class StageFacts:
    """Everything any stage's exit rule needs, gathered once by the service.

    The four ``*_available`` flags say whether the module that answers a group of
    checks exists yet. They are properties of the build, not of the vendor, and
    each is flipped by the section that lands it. Inferring the same thing from a
    ``None`` value would conflate "not built" with "built and empty", which is the
    exact confusion rule 7 exists to prevent.
    """

    vendor_id: uuid.UUID
    vendor_name: str
    tier: str | None = None
    business_owner_membership_id: uuid.UUID | None = None
    data_classification: str | None = None
    tiering_assessment_id: uuid.UUID | None = None
    stage_entered_at: datetime | None = None
    next_cycle_opened: bool = False

    # -- section 3: diligence, questionnaire, scoring, findings ---------------
    assessments_available: bool = False
    selected_bank_count: int = 0
    required_reviewer_roles: tuple[str, ...] = ()
    assigned_reviewer_roles: tuple[str, ...] = ()
    unanswered_question_count: int = 0
    missing_evidence_count: int = 0
    residual_score: float | None = None
    findings_available: bool = False
    open_critical_findings: int = 0

    # -- section 4: contracting, approval ------------------------------------
    contracts_available: bool = False
    contract_count: int = 0
    approvals_available: bool = False
    approval_decided_at: datetime | None = None


def _intake(f: StageFacts) -> list[ExitCheck]:
    return [
        ExitCheck(
            code="intake.named",
            label="The vendor has a name",
            satisfied=bool(f.vendor_name.strip()),
            clears_with="vendor",
            clears_id=f.vendor_id,
        ),
        ExitCheck(
            code="intake.owned",
            label="A business owner is named",
            satisfied=f.business_owner_membership_id is not None,
            detail=None
            if f.business_owner_membership_id
            else "Nobody is accountable for this vendor yet.",
            clears_with="vendor",
            clears_id=f.vendor_id,
        ),
        ExitCheck(
            code="intake.classified",
            label="The data we share is classified",
            satisfied=f.data_classification is not None,
            detail=None
            if f.data_classification
            else "Classification drives the tier, so tiering cannot run without it.",
            clears_with="vendor",
            clears_id=f.vendor_id,
        ),
    ]


def _tiering(f: StageFacts) -> list[ExitCheck]:
    return [
        ExitCheck(
            code="tiering.assessed",
            label="A tiering assessment exists for this cycle",
            satisfied=f.tiering_assessment_id is not None,
            detail=None if f.tiering_assessment_id else "Score the five factors to set the tier.",
            clears_with="vendor_tiering_assessment",
            clears_id=f.tiering_assessment_id,
        )
    ]


def _diligence(f: StageFacts) -> list[ExitCheck]:
    missing = tuple(r for r in f.required_reviewer_roles if r not in f.assigned_reviewer_roles)
    return [
        ExitCheck(
            code="diligence.bank_selected",
            label="A questionnaire bank is selected",
            satisfied=(f.selected_bank_count > 0) if f.assessments_available else None,
            clears_with="vendor_assessment",
        ),
        # Reviewers resolve through the tiering policy and the team roster, both
        # of which exist now, so this one is answerable today.
        ExitCheck(
            code="diligence.reviewers_assigned",
            label=f"The {f.tier or 'tier'} reviewers are assigned",
            satisfied=not missing,
            detail=f"Still unassigned: {', '.join(missing)}." if missing else None,
            clears_with="vendor_team_roster",
        ),
    ]


def _questionnaire(f: StageFacts) -> list[ExitCheck]:
    if not f.assessments_available:
        return [
            ExitCheck(
                code="questionnaire.answered", label="Every question is answered", satisfied=None
            ),
            ExitCheck(
                code="questionnaire.evidenced",
                label="Every answer that needs proof has it",
                satisfied=None,
            ),
        ]
    return [
        ExitCheck(
            code="questionnaire.answered",
            label="Every question is answered",
            satisfied=f.unanswered_question_count == 0,
            detail=f"{f.unanswered_question_count} still unanswered."
            if f.unanswered_question_count
            else None,
            clears_with="vendor_assessment",
        ),
        ExitCheck(
            code="questionnaire.evidenced",
            label="Every answer that needs proof has it",
            satisfied=f.missing_evidence_count == 0,
            detail=f"{f.missing_evidence_count} answers are missing their file."
            if f.missing_evidence_count
            else None,
            clears_with="vendor_assessment",
        ),
    ]


def _scoring(f: StageFacts) -> list[ExitCheck]:
    return [
        ExitCheck(
            code="scoring.residual",
            label="A residual score has been computed",
            satisfied=(f.residual_score is not None) if f.assessments_available else None,
            clears_with="vendor_assessment",
        )
    ]


def _findings(f: StageFacts) -> list[ExitCheck]:
    return [
        ExitCheck(
            code="findings.no_open_critical",
            label="No critical finding is open without an accepted risk",
            satisfied=(f.open_critical_findings == 0) if f.findings_available else None,
            detail=f"{f.open_critical_findings} open critical."
            if f.open_critical_findings
            else None,
            clears_with="vendor_finding",
        )
    ]


def _contracting(f: StageFacts) -> list[ExitCheck]:
    # A contract is only demanded of the tiers that carry real exposure. Requiring
    # paperwork from a low-tier vendor is exactly the disproportionate work
    # tiering exists to remove.
    if f.tier not in {"critical", "high"}:
        return [
            ExitCheck(
                code="contracting.not_required",
                label=f"No contract required at {f.tier or 'this'} tier",
                satisfied=True,
            )
        ]
    return [
        ExitCheck(
            code="contracting.contract_linked",
            label="A contract is linked",
            satisfied=(f.contract_count > 0) if f.contracts_available else None,
            clears_with="vendor_contract",
        )
    ]


def _approval(f: StageFacts) -> list[ExitCheck]:
    decided: bool | None
    if not f.approvals_available:
        decided = None
    elif f.approval_decided_at is None:
        decided = False
    elif f.stage_entered_at is None:
        # The stage has not been reached, so there is no attempt for a decision to
        # belong to. This is not the harmless case it looks like: a send-back
        # clears ``entered_at`` on every stage it resets, so treating "never
        # entered" as fresh would let a pre-send-back approval satisfy the gate
        # again the moment the engagement came back round to it.
        decided = False
    else:
        # The gate-freshness rule. A send-back restarts the stage, so an approval
        # decided before that restart no longer satisfies it — without ever
        # mutating the append-only approval row.
        decided = f.approval_decided_at >= f.stage_entered_at
    return [
        ExitCheck(
            code="approval.decided",
            label="An approver has decided, for this attempt",
            satisfied=decided,
            detail="The last decision predates the current attempt, so it no longer counts."
            if decided is False and f.approval_decided_at is not None
            else None,
            clears_with="vendor_approval",
        ),
        ExitCheck(
            code="approval.no_unmitigated_critical",
            label="No unmitigated critical finding remains",
            satisfied=(f.open_critical_findings == 0) if f.findings_available else None,
            clears_with="vendor_finding",
        ),
    ]


def _onboarding(_f: StageFacts) -> list[ExitCheck]:
    # A handoff, not a control. It passes so the rail shows it happening rather
    # than pretending it is a checkpoint.
    return [ExitCheck(code="onboarding.handoff", label="Handed over to the owner", satisfied=True)]


def _monitoring(_f: StageFacts) -> list[ExitCheck]:
    return [
        ExitCheck(
            code="monitoring.steady_state",
            label="Under monitoring, which is the resting state",
            satisfied=True,
        )
    ]


def _reassessment(f: StageFacts) -> list[ExitCheck]:
    return [
        ExitCheck(
            code="reassessment.cycle_opened",
            label="A new review cycle has been opened",
            satisfied=f.next_cycle_opened,
            clears_with="vendor_stage",
        )
    ]


def _offboarding(_f: StageFacts) -> list[ExitCheck]:
    return [
        ExitCheck(code="offboarding.terminal", label="The relationship has ended", satisfied=True)
    ]


_RULES: Final[dict[str, object]] = {
    "intake": _intake,
    "tiering": _tiering,
    "diligence": _diligence,
    "questionnaire": _questionnaire,
    "scoring": _scoring,
    "findings": _findings,
    "contracting": _contracting,
    "approval": _approval,
    "onboarding": _onboarding,
    "monitoring": _monitoring,
    "reassessment": _reassessment,
    "offboarding": _offboarding,
}


def evaluate_exit(stage: str, facts: StageFacts) -> tuple[ExitCheck, ...]:
    """Every condition on leaving ``stage``, computed and never stored.

    A stored blocker list is a cache that goes stale the moment the record that
    clears it changes, which is the one thing a blocker must never do.
    """
    rule = _RULES.get(stage)
    if rule is None:
        raise ValueError(f"unknown stage {stage!r}")
    return tuple(rule(facts))  # type: ignore[operator]


def blockers(checks: tuple[ExitCheck, ...]) -> tuple[ExitCheck, ...]:
    return tuple(c for c in checks if c.satisfied is False)


def pending(checks: tuple[ExitCheck, ...]) -> tuple[ExitCheck, ...]:
    return tuple(c for c in checks if c.satisfied is None)


@dataclass(frozen=True, slots=True)
class StageState:
    """The stored facts about one stage row that the machine needs."""

    stage: str
    status: str
    is_gate: bool
    is_required: bool


def allowed_transitions(
    current: StageState,
    checks: tuple[ExitCheck, ...],
    *,
    skippable: frozenset[str] = frozenset(),
    has_earlier_stage: bool = True,
) -> tuple[str, ...]:
    """What the machine will accept next, served so no client hardcodes it.

    The interface asks the server rather than reimplementing V2 and V9 in
    TypeScript, which is how the two drift apart and the UI offers a move the API
    then refuses.
    """
    moves: list[str] = []
    if current.status != "complete" and not blockers(checks) and current.stage != TERMINAL_STAGE:
        moves.append("advance")
    if has_earlier_stage:
        moves.append("send_back")
    if (
        current.stage in skippable
        and not current.is_gate
        and not current.is_required
        and current.status in {"not_started", "in_progress"}
    ):
        moves.append("skip")
    return tuple(moves)


@dataclass(frozen=True, slots=True)
class PlannedStage:
    """One row ``materialise`` will write."""

    stage: str
    is_gate: bool
    is_required: bool
    status: str
    skipped_by_policy: str | None = None


def plan_cycle(
    tier: str | None, matrix: Mapping[str, Sequence[str]] | None = None
) -> tuple[PlannedStage, ...]:
    """The twelve rows for one cycle, with this tier's skips already marked.

    Skipped rows are written, not omitted. *"Policy said this was
    disproportionate"* and *"someone forgot"* must never look the same to an
    auditor, and a stage that was never inserted cannot tell them apart.
    """
    skipped = skips_for(tier, matrix)
    reason = f"{tier} tier" if tier else None
    return tuple(
        PlannedStage(
            stage=stage,
            is_gate=stage in GATES,
            is_required=stage in REQUIRED_STAGES,
            status="skipped" if stage in skipped else "not_started",
            skipped_by_policy=reason if stage in skipped else None,
        )
        for stage in STAGES
    )


def next_actionable(stages: list[tuple[str, str]], after: str) -> str | None:
    """The next stage that is not skipped, walking forward from ``after``.

    ``stages`` is ``(stage, status)`` in STAGES order. Advancing walks *over*
    skipped rows rather than stopping on them, so a low-tier vendor goes from
    tiering to contracting in one move — which is the proportionality being
    visible rather than implied.
    """
    order = {stage: index for index, stage in enumerate(STAGES)}
    start = order[after]
    for stage, status in sorted(stages, key=lambda row: order[row[0]]):
        if order[stage] > start and status != "skipped":
            return stage
    return None
