"""The register's pure rules: scales, bands, rescaling, status transitions.

No database here, so the unit suite covers every rule without a session and the
service stays about persistence and authority.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any, Final

from verity.core.errors import InvalidInput
from verity.modules.risk.models import MAX_LEVELS, MIN_LEVELS

BAND_KEYS: Final[tuple[str, ...]] = ("low", "medium", "high", "critical")
_BAND_LABELS: Final[dict[str, str]] = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "critical": "Critical",
}
# Fractions of the maximum score where each band after "low" starts. For 5 by 5
# this lands on the familiar 5, 10, 15.
_BAND_FRACTIONS: Final[tuple[float, ...]] = (0.2, 0.4, 0.6)

_LIKELIHOOD_LABELS: Final[dict[int, tuple[tuple[str, str], ...]]] = {
    3: (
        ("Unlikely", "Not expected in the next few years."),
        ("Possible", "Could happen within a year or two."),
        ("Likely", "Expected to happen within the year."),
    ),
    4: (
        ("Unlikely", "Not expected in the next few years."),
        ("Possible", "Could happen within a year or two."),
        ("Likely", "Expected to happen within the year."),
        ("Almost certain", "Happens several times a year."),
    ),
    5: (
        ("Rare", "Only in exceptional circumstances, less than once in ten years."),
        ("Unlikely", "Could happen, about once in five to ten years."),
        ("Possible", "Might happen, about once in one to five years."),
        ("Likely", "Will probably happen at least once a year."),
        ("Almost certain", "Expected to happen several times a year."),
    ),
    6: (
        ("Rare", "Only in exceptional circumstances."),
        ("Very unlikely", "About once in ten years."),
        ("Unlikely", "About once in five to ten years."),
        ("Possible", "About once in one to five years."),
        ("Likely", "At least once a year."),
        ("Almost certain", "Several times a year."),
    ),
}

_IMPACT_LABELS: Final[dict[int, tuple[tuple[str, str], ...]]] = {
    3: (
        ("Minor", "Contained, no customer or regulatory effect."),
        ("Moderate", "Noticeable disruption or cost, recoverable within weeks."),
        ("Major", "Customer, regulatory or financial harm that takes months to recover."),
    ),
    4: (
        ("Minor", "Contained, no customer or regulatory effect."),
        ("Moderate", "Noticeable disruption or cost, recoverable within weeks."),
        ("Major", "Customer or regulatory harm, significant cost."),
        ("Severe", "Threatens the business, its licence or its largest customers."),
    ),
    5: (
        ("Negligible", "No noticeable effect on operations or customers."),
        ("Minor", "Small, contained disruption or cost, fixed within days."),
        ("Moderate", "Noticeable disruption or cost, recoverable within weeks."),
        ("Major", "Customer, regulatory or financial harm that takes months to recover."),
        ("Severe", "Threatens the business, its licence or its largest customers."),
    ),
    6: (
        ("Negligible", "No noticeable effect."),
        ("Minor", "Small, contained disruption."),
        ("Moderate", "Noticeable disruption, recoverable within weeks."),
        ("Significant", "Customer or regulatory attention, material cost."),
        ("Major", "Serious harm that takes months to recover."),
        ("Severe", "Threatens the business or its licence."),
    ),
}

# Manual targets only. ``accepted`` is set by an approved acceptance and left by
# revoke or expiry, never picked from a list (R4).
STATUS_TRANSITIONS: Final[dict[str, tuple[str, ...]]] = {
    "open": ("in_treatment", "mitigated", "closed"),
    "in_treatment": ("open", "mitigated", "closed"),
    "mitigated": ("in_treatment", "closed"),
    "accepted": ("closed",),
    "closed": ("open",),
}

# The default taxonomy every new register starts with (R10), after GRC-Tenant.
DEFAULT_TAXONOMY: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("Strategic", ("Market", "Reputation", "Strategic planning", "Competitive", "Brand", "Other")),
    (
        "Operational",
        ("Process", "Human resources", "Supply chain", "Business continuity", "Quality", "Other"),
    ),
    ("Financial", ("Credit", "Market risk", "Liquidity", "Accounting", "Budget", "Other")),
    ("Compliance", ("Regulatory", "Legal", "Contractual", "Ethical", "Data privacy", "Other")),
    (
        "Technology",
        ("Cybersecurity", "Infrastructure", "Data", "System availability", "Software", "Other"),
    ),
    ("Third party", ("Vendor", "Outsourcing", "Partnership", "Contractor", "Other")),
    (
        "Project and change",
        ("Project delivery", "Change management", "Integration", "Scope", "Other"),
    ),
    ("Internal", ("Fraud", "Governance", "Culture", "Process integrity", "Other")),
)

LIBRARY_LEVELS: Final = 5
"""The scale the starter library's default scores are written on."""


def default_scale(kind: str, levels: int) -> list[dict[str, Any]]:
    """Labelled levels for a likelihood or impact axis of the given size."""
    labels = (_LIKELIHOOD_LABELS if kind == "likelihood" else _IMPACT_LABELS)[levels]
    return [
        {"level": i + 1, "label": label, "description": description}
        for i, (label, description) in enumerate(labels)
    ]


def default_bands(max_score: int) -> list[dict[str, Any]]:
    """Four bands whose thresholds scale with the matrix."""
    mins = [1, *(max(2, math.ceil(max_score * f)) for f in _BAND_FRACTIONS)]
    # Small matrices can collide; nudge upwards so thresholds stay strictly ascending.
    for i in range(1, len(mins)):
        mins[i] = max(mins[i], mins[i - 1] + 1)
    return [
        {"key": key, "label": _BAND_LABELS[key], "min_score": minimum}
        for key, minimum in zip(BAND_KEYS, mins, strict=True)
    ]


def band_for(bands: Sequence[dict[str, Any]], score: int | None) -> str | None:
    """The key of the highest band the score reaches, or None when unscored."""
    if score is None:
        return None
    reached = [b for b in bands if int(b["min_score"]) <= score]
    return str(reached[-1]["key"]) if reached else None


def band_ranges(bands: Sequence[dict[str, Any]], max_score: int) -> dict[str, tuple[int, int]]:
    """Inclusive score range per band, for filtering in SQL."""
    out: dict[str, tuple[int, int]] = {}
    for i, band in enumerate(bands):
        upper = int(bands[i + 1]["min_score"]) - 1 if i + 1 < len(bands) else max_score
        out[str(band["key"])] = (int(band["min_score"]), upper)
    return out


def rescale(value: int, to_levels: int, from_levels: int = LIBRARY_LEVELS) -> int:
    """Map a level from one scale size to another, keeping its relative position."""
    if to_levels == from_levels:
        return value
    return max(1, min(to_levels, round(value * to_levels / from_levels)))


def validate_levels(levels: int, *, axis: str) -> None:
    if not MIN_LEVELS <= levels <= MAX_LEVELS:
        raise InvalidInput(
            f"The {axis} scale needs between {MIN_LEVELS} and {MAX_LEVELS} levels.",
            detail=f"{axis} levels {levels} out of range",
        )


def validate_scale(
    scale: Sequence[dict[str, Any]], levels: int, *, axis: str
) -> list[dict[str, Any]]:
    """Normalise a submitted scale: one labelled entry per level, in order."""
    if len(scale) != levels:
        raise InvalidInput(
            f"Give every {axis} level a label.",
            detail=f"{axis} scale has {len(scale)} entries for {levels} levels",
        )
    out: list[dict[str, Any]] = []
    for i, entry in enumerate(scale):
        label = str(entry.get("label") or "").strip()
        if not label:
            raise InvalidInput(
                f"Give every {axis} level a label.", detail=f"{axis} level {i + 1} has no label"
            )
        out.append(
            {
                "level": i + 1,
                "label": label[:40],
                "description": str(entry.get("description") or "").strip()[:200],
            }
        )
    return out


def validate_bands(bands: Sequence[dict[str, Any]], max_score: int) -> list[dict[str, Any]]:
    """Exactly the four bands, ascending, starting at 1, within the matrix."""
    by_key = {str(b.get("key")): b for b in bands}
    if set(by_key) != set(BAND_KEYS):
        raise InvalidInput(
            "Set a starting score for low, medium, high and critical.",
            detail=f"bands {sorted(by_key)}",
        )
    out: list[dict[str, Any]] = []
    previous = 0
    for key in BAND_KEYS:
        band = by_key[key]
        try:
            minimum = int(band.get("min_score"))  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise InvalidInput(
                "Band thresholds must be whole numbers.", detail=f"band {key} min_score"
            ) from exc
        if key == "low":
            minimum = 1
        if minimum <= previous or minimum > max_score:
            raise InvalidInput(
                f"Band thresholds must rise from low to critical and stay within {max_score}.",
                detail=f"band {key} min_score {minimum} after {previous}",
            )
        label = str(band.get("label") or _BAND_LABELS[key]).strip()[:24]
        out.append({"key": key, "label": label, "min_score": minimum})
        previous = minimum
    return out


def check_transition(current: str, target: str) -> None:
    if target == current:
        return
    if target not in STATUS_TRANSITIONS.get(current, ()):
        raise InvalidInput(
            "That status change is not available from here.",
            detail=f"transition {current} -> {target} not allowed",
        )
