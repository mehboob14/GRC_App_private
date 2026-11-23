"""Assessment objective outcomes, derived and never stored (guided onboarding AO-1 to AO-5).

Pure functions over facts the service gathers: no database. An artifact is satisfied when any
of its sources is current and accepted and none contradicts it (a failing check wins). An
objective is satisfied when every artifact its examine, test or observe methods name is
satisfied; interview alone never satisfies. A control is objective ready when a person says it
is implemented and every applicable design and operating objective is satisfied.

Two automation rules are computed side by side until the owner chooses (report, "Decisions the
owner must make"): under rule B a passing check may satisfy its artifact; under rule A a check
can only take satisfaction away, so every artifact still needs a person's evidence or an
approved document.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final, Literal

Rule = Literal["A", "B"]

# Worst first: a deviation found by a check outranks not knowing, which outranks staleness.
_REASON_RANK: Final[dict[str, int]] = {
    "deviation": 0,
    "insufficient_information": 1,
    "stale": 2,
    "awaiting_review": 3,
    "missing": 4,
}


@dataclass(frozen=True, slots=True)
class ArtifactState:
    key: str
    state: str
    """``satisfied`` or ``not_satisfied``."""
    reason: str | None
    """For not satisfied: deviation, insufficient_information, stale, awaiting_review or
    missing."""


@dataclass(frozen=True, slots=True)
class Facts:
    check_states: Mapping[str, str]
    """Check key to pass, fail, error, stale, not_applicable, pending, not_connected."""
    tagged: Mapping[str, Sequence[str]]
    """Artifact key to the state of each evidence row a person filed for it: current
    (reviewed and approved), pending (not reviewed yet) or lapsed."""
    approved_templates: frozenset[str]


def artifact_state(  # noqa: PLR0912 — one branch per source kind and result
    artifact: Mapping[str, Any], facts: Facts, rule: Rule = "B"
) -> ArtifactState:
    satisfied = False
    reasons: list[str] = []
    for source in artifact.get("sources", []):
        kind = source.get("kind")
        if kind == "check":
            states = [facts.check_states.get(k, "not_available") for k in source.get("checks", [])]
            if "fail" in states:
                return ArtifactState(artifact["key"], "not_satisfied", "deviation")
            if "error" in states or "stale" in states:
                reasons.append("insufficient_information")
            elif "pass" in states and rule == "B":
                satisfied = True
        elif kind == "person":
            rows = facts.tagged.get(artifact["key"], ())
            if "current" in rows:
                satisfied = True
            elif "pending" in rows:
                # Only reviewed evidence counts (owner decision, 2026-11-23).
                reasons.append("awaiting_review")
            elif rows:
                reasons.append("stale")
        elif kind == "document":
            if source.get("template") in facts.approved_templates:
                satisfied = True
    if reasons and not satisfied:
        reasons.sort(key=_REASON_RANK.__getitem__)
        return ArtifactState(artifact["key"], "not_satisfied", reasons[0])
    if satisfied and "insufficient_information" not in reasons:
        return ArtifactState(artifact["key"], "satisfied", None)
    if satisfied:
        # A current record with a check that could not be read: the check may yet contradict it.
        return ArtifactState(artifact["key"], "not_satisfied", "insufficient_information")
    return ArtifactState(artifact["key"], "not_satisfied", "missing")


def required_artifacts(objective: Mapping[str, Any]) -> list[str]:
    """The artifacts an objective rests on: those named by examine, test or observe."""
    out: list[str] = []
    for method in objective.get("methods", []):
        if method.get("method") == "interview":
            continue
        for key in method.get("artifacts", []):
            if key not in out:
                out.append(key)
    return out


def objective_outcome(
    objective: Mapping[str, Any],
    states: Mapping[str, ArtifactState],
    *,
    not_applicable: bool = False,
) -> tuple[str, str | None]:
    """``(outcome, reason)``: satisfied, not_satisfied (with its worst reason),
    not_applicable (only by a recorded decision) or not_tested (nothing observed yet)."""
    if not_applicable:
        return "not_applicable", None
    needed = [states[k] for k in required_artifacts(objective) if k in states]
    if not needed:
        return "not_tested", None
    if all(s.state == "satisfied" for s in needed):
        return "satisfied", None
    reasons = sorted(
        (s.reason or "missing" for s in needed if s.state != "satisfied"),
        key=_REASON_RANK.__getitem__,
    )
    if all(s.reason == "missing" for s in needed):
        return "not_tested", None
    return "not_satisfied", reasons[0]


def control_readiness(status: str, outcomes: Sequence[tuple[str, str]]) -> tuple[bool, bool, bool]:
    """``(design_ready, operating_ready, ready)`` from ``(assurance, outcome)`` pairs.

    Not applicable objectives count as satisfied. A control with no design objective is not
    design ready, because nothing shows its design; one with no operating objective written
    yet is not held back on operation."""

    def ready(kind: str) -> bool:
        defined = [o for a, o in outcomes if a == kind]
        if not defined:
            return kind == "operating"
        return all(o in {"satisfied", "not_applicable"} for o in defined)

    design, operating = ready("design"), ready("operating")
    return design, operating, status == "implemented" and design and operating
