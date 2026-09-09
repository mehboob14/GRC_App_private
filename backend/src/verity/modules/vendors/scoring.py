"""Inherent tiering — a pure function and its arithmetic (V6).

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
