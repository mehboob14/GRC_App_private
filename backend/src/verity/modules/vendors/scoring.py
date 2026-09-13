"""Vendor scoring — inherent tiering (V6) and residual risk (V7).

No session, no I/O, no imports from anything that touches a database. Mirrors
``vulnerabilities/scoring.py``, and for the same reason: that module proved that a
score whose derivation is thrown away cannot be explained on screen afterwards,
and a tier a reviewer cannot interrogate is a tier they will not defend to an
auditor.

Every intermediate step is returned rather than discarded — each factor's answer,
its weight, the points it contributed and the points it could have contributed —
so the tiering panel can show the sum and the register can explain itself.

**The tier is not a label.** It decides assessment depth, how many reviewers are
required, and how often the vendor is reassessed (spec ¶82). A product that tiers
without changing the workload has added a dropdown, not a control. This module
computes the number; ``lifecycle.py`` is where it changes the work.

Weights and thresholds are the reference product's shipped ``DEFAULT_TIERING_CONFIG``
(V6) — a port, not an invention. They are defaults, not constants: a tenant row in
``vendor_tiering_policies`` overrides them, and every scored assessment stores the
values it used so a later retune cannot rewrite the past.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

# The five factors of spec ¶82, in the order they are shown, with the ER's 0..4
# scale. Order is part of the contract: the panel renders them in this sequence
# and the register's explain-text reads down it.
FACTOR_KEYS: Final[tuple[str, ...]] = (
    "data_sensitivity",
    "business_criticality",
    "system_access",
    "regulatory_scope",
    "fourth_party_reliance",
)

FACTOR_LABELS: Final[dict[str, str]] = {
    "data_sensitivity": "Data sensitivity",
    "business_criticality": "Business criticality",
    "system_access": "System access",
    "regulatory_scope": "Regulatory scope",
    "fourth_party_reliance": "Fourth-party reliance",
}

FACTOR_SCALE_MAX: Final = 4
"""The ER's ``0 to 4`` answer scale. An answer outside it is clamped, not refused —
a bad import should produce a defensible number, not a failed import."""

DEFAULT_WEIGHTS: Final[dict[str, float]] = {
    "data_sensitivity": 0.30,
    "business_criticality": 0.25,
    "system_access": 0.20,
    "regulatory_scope": 0.15,
    "fourth_party_reliance": 0.10,
}

DEFAULT_THRESHOLDS: Final[dict[str, float]] = {"critical": 75.0, "high": 50.0, "medium": 25.0}
"""Lower bounds, worst first. Below the lowest is ``low``; the ER calls this
"critical high medium ordered" and gives no values, so these are V6's."""

# Worst first, so index order is severity order everywhere in the module.
TIER_ORDER: Final[tuple[str, ...]] = ("critical", "high", "medium", "low")


@dataclass(frozen=True, slots=True)
class TieringFactor:
    """One row of the arithmetic, with everything the panel needs to draw a bar."""

    key: str
    label: str
    answer: int
    """What the assessor entered, before clamping — shown as given."""
    clamped: int
    weight: float
    points: float
    """``clamped / 4 * weight * 100`` -- what this factor put into the score."""
    max_points: float
    """``weight * 100`` -- what it would contribute at the top of the scale."""


@dataclass(frozen=True, slots=True)
class TieringBreakdown:
    factors: tuple[TieringFactor, ...]
    score: float
    tier: str
    thresholds: dict[str, float]
    points_to_higher_tier: float | None
    """How many points would push this into the next tier up. ``None`` at critical.

    Spec ¶82's second scenario asks for this by name: the reviewer must be able to
    answer "what would change this" without re-running the form."""
    points_to_lower_tier: float | None
    """How far it is above the band it sits in. ``None`` at low."""


def _clamp(value: int) -> int:
    return max(0, min(FACTOR_SCALE_MAX, value))


def _tier_for(score: float, thresholds: dict[str, float]) -> str:
    """Band the score, falling back per-band to the shipped default.

    Total by design. ``thresholds`` can arrive from tenant-editable JSON, and a
    partial override there must retune the band it names rather than raising a
    KeyError from inside a compliance calculation.
    """
    for tier in TIER_ORDER[:-1]:
        if score >= thresholds.get(tier, DEFAULT_THRESHOLDS[tier]):
            return tier
    return TIER_ORDER[-1]


def compute_tier(
    answers: dict[str, int],
    *,
    weights: dict[str, float] | None = None,
    thresholds: dict[str, float] | None = None,
) -> TieringBreakdown:
    """Score the five factors and band the result.

    ``inherent = sum(clamp(f, 0, 4) / 4 * w) * 100`` (V6).

    A missing factor is scored as 0 rather than refused: a half-filled assessment
    should produce the low number it has earned, so the gap shows up as a low tier
    that a reviewer questions, not as an error that hides the record.
    """
    weights = weights or DEFAULT_WEIGHTS
    thresholds = thresholds or DEFAULT_THRESHOLDS

    factors: list[TieringFactor] = []
    score = 0.0
    for key in FACTOR_KEYS:
        answer = int(answers.get(key, 0))
        clamped = _clamp(answer)
        weight = float(weights.get(key, 0.0))
        points = (clamped / FACTOR_SCALE_MAX) * weight * 100
        score += points
        factors.append(
            TieringFactor(
                key=key,
                label=FACTOR_LABELS[key],
                answer=answer,
                clamped=clamped,
                weight=weight,
                points=round(points, 2),
                max_points=round(weight * 100, 2),
            )
        )

    score = round(score, 2)
    tier = _tier_for(score, thresholds)
    index = TIER_ORDER.index(tier)

    # Distance up is to the bottom of the band above; distance down is to the
    # bottom of this band, which is how far the score could fall before dropping.
    bands = {**DEFAULT_THRESHOLDS, **thresholds}
    to_higher = round(bands[TIER_ORDER[index - 1]] - score, 2) if index > 0 else None
    to_lower = round(score - bands[tier], 2) if tier in bands else None

    return TieringBreakdown(
        factors=tuple(factors),
        score=score,
        tier=tier,
        thresholds=bands,
        points_to_higher_tier=to_higher,
        points_to_lower_tier=to_lower,
    )


# ---------------------------------------------------------------------------
# Residual scoring (V7) — what the completed review leaves behind
# ---------------------------------------------------------------------------

ANSWER_VALUES: Final[dict[str, float]] = {"yes": 1.0, "partial": 0.5, "no": 0.0}
"""``na`` is deliberately absent: it leaves both sides of the average, rather than
scoring zero. A question that does not apply must not look like a control that is
missing."""

CONTROL_CEILING: Final = 0.70
"""The most that perfect answers may reduce inherent risk.

A vendor answering everything ``yes`` still carries 30% of its inherent risk,
because a questionnaire is a claim and not a proof. This number is the single
most consequential judgement in the module, which is why it is named, reported as
its own step, and stored on every assessment that used it.
"""

DEFAULT_DOMAIN_WEIGHTS: Final[dict[str, float]] = {
    "information_security": 1.2,
    "access_control": 1.5,
    "data_protection_privacy": 1.5,
    "business_continuity": 1.0,
    "incident_response": 1.2,
    "secure_development": 1.0,
    "infrastructure_cloud": 1.0,
    "personnel_security": 0.8,
    "compliance_legal": 1.0,
    "fourth_party_management": 0.8,
}
"""How much each domain counts in the roll-up. Access control and data protection
carry most because that is where a third-party breach actually happens; personnel
security and fourth-party management carry least because they are attested rather
than evidenced."""

GRADE_BOUNDS: Final[tuple[tuple[str, float], ...]] = (
    ("A", 20.0),
    ("B", 40.0),
    ("C", 60.0),
    ("D", 80.0),
)
"""Upper bounds, best first. At or above the last one is ``F`` (V7)."""

GRADES: Final[tuple[str, ...]] = ("A", "B", "C", "D", "F")

CRITICAL_FAIL_FLOOR_TIER: Final = "high"
"""A ``no`` on any critical-control question floors the residual at the bottom of
this band, however good the rest of the answers are.

V7 applies this **after** the clamp, so the floor can lift the residual above the
inherent score. That is deliberate rather than an ordering accident: inherent
tiering measures exposure, while a missing critical control is a specific known
weakness the exposure factors never saw. The step list reports both, so the reader
can see the floor was what did it."""


@dataclass(frozen=True, slots=True)
class Answer:
    """One scored response. The pure input; nothing here knows about a database."""

    question_key: str
    domain: str
    answer: str
    weight: float = 1.0
    critical_control: bool = False


@dataclass(frozen=True, slots=True)
class DomainPosture:
    """One domain's contribution, with the arithmetic kept."""

    domain: str
    answered: int
    not_applicable: int
    unanswered: int
    posture: float | None
    """0..1, weight-averaged over answered questions. ``None`` when every question
    in the domain was ``na`` or unanswered — which is not the same as zero, and the
    roll-up drops the domain rather than scoring it badly."""
    residual: float | None
    weight: float


@dataclass(frozen=True, slots=True)
class ScoreStep:
    """One line of the explanation, in the order it applied."""

    label: str
    value: float
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class ResidualBreakdown:
    inherent: float
    domains: tuple[DomainPosture, ...]
    steps: tuple[ScoreStep, ...]
    """Every adjustment as its own line, including the ones that did not fire. A
    bar chart whose bars do not sum to the total is worse than no bar chart."""
    score: float
    grade: str
    clamped: bool
    critical_control_failed: bool
    failed_critical_keys: tuple[str, ...]


def grade_for(score: float) -> str:
    for grade, upper in GRADE_BOUNDS:
        if score < upper:
            return grade
    return "F"


def compute_residual(
    answers: Sequence[Answer],
    *,
    inherent: float,
    domain_weights: Mapping[str, float] | None = None,
    control_ceiling: float = CONTROL_CEILING,
    thresholds: Mapping[str, float] | None = None,
) -> ResidualBreakdown:
    """Roll the answers up into the risk the review leaves behind (V7).

    ``posture(domain) = sum(value * weight) / sum(weight)`` over answered questions;
    ``residual(domain) = inherent * (1 - ceiling * posture)``; then the weighted
    average across domains, clamped to at most ``inherent``, then floored if any
    critical control failed.

    The clamp and the floor are reported as their own steps rather than folded
    into the number, for the same reason the vulnerability module reports its KEV
    floor separately: an adjustment nobody can see is an adjustment nobody trusts.
    """
    weights = dict(DEFAULT_DOMAIN_WEIGHTS) | dict(domain_weights or {})
    bands = {**DEFAULT_THRESHOLDS, **dict(thresholds or {})}

    grouped: dict[str, list[Answer]] = {}
    for answer in answers:
        grouped.setdefault(answer.domain, []).append(answer)

    domains: list[DomainPosture] = []
    for domain in sorted(grouped):
        rows = grouped[domain]
        scored = [r for r in rows if r.answer in ANSWER_VALUES]
        total_weight = sum(r.weight for r in scored)
        posture = (
            sum(ANSWER_VALUES[r.answer] * r.weight for r in scored) / total_weight
            if total_weight
            else None
        )
        domains.append(
            DomainPosture(
                domain=domain,
                answered=len(scored),
                not_applicable=sum(1 for r in rows if r.answer == "na"),
                unanswered=sum(
                    1 for r in rows if r.answer not in ANSWER_VALUES and r.answer != "na"
                ),
                posture=round(posture, 4) if posture is not None else None,
                residual=round(inherent * (1 - control_ceiling * posture), 2)
                if posture is not None
                else None,
                weight=float(weights.get(domain, 1.0)),
            )
        )

    contributing = [d for d in domains if d.residual is not None]
    weight_sum = sum(d.weight for d in contributing)
    raw = (
        sum(d.residual * d.weight for d in contributing if d.residual is not None) / weight_sum
        if weight_sum
        else inherent
    )
    raw = round(raw, 2)

    steps: list[ScoreStep] = [
        ScoreStep("Inherent risk", round(inherent, 2), "Before any control answers."),
        ScoreStep(
            "Weighted domain residual",
            raw,
            f"Across {len(contributing)} scored domain(s); controls may remove at most "
            f"{int(control_ceiling * 100)}%.",
        ),
    ]

    score = raw
    clamped = score > inherent
    if clamped:
        score = round(inherent, 2)
    steps.append(
        ScoreStep(
            "Clamp to inherent",
            score,
            "Controls reduce risk, never add to it."
            if clamped
            else "Not applied. The roll-up was already at or below inherent.",
        )
    )

    failed = tuple(a.question_key for a in answers if a.critical_control and a.answer == "no")
    floor = bands.get(CRITICAL_FAIL_FLOOR_TIER, DEFAULT_THRESHOLDS[CRITICAL_FAIL_FLOOR_TIER])
    if failed and score < floor:
        score = round(floor, 2)
    steps.append(
        ScoreStep(
            "Critical-control floor",
            score,
            f"{len(failed)} critical control answered no, so the score cannot fall below {floor:g}."
            if failed
            else "Not applied. No critical control was answered no.",
        )
    )

    return ResidualBreakdown(
        inherent=round(inherent, 2),
        domains=tuple(domains),
        steps=tuple(steps),
        score=score,
        grade=grade_for(score),
        clamped=clamped,
        critical_control_failed=bool(failed),
        failed_critical_keys=failed,
    )
