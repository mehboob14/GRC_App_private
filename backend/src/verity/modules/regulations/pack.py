"""The country reference pack: sealed JSON, read into memory once, never written to the database.

Matching (JC-2, JC-3, J3): each entry has triggers, each with a confidence (applies, likely
applies, check). An entry shows with the strongest confidence among its triggers that hold. A
trigger that cannot be decided because an answer is missing or "not sure" downgrades a first
tier entry to "check"; other tiers stay hidden until the answer is given.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from typing import Any, Final

from verity.seed.seal import CONTENT_ROOT, verify_pack
from verity.shared.conditions import holds
from verity.shared.countries import EU_MEMBERS

PACK: Final = CONTENT_ROOT / "regulations"
FILES: Final[tuple[str, ...]] = ("AU", "EU", "GB", "PK", "AE", "OM", "SA", "US", "GLOBAL")
COVERED: Final[frozenset[str]] = frozenset({"AU", "GB", "PK", "AE", "OM", "SA", "US"}) | EU_MEMBERS
_RANK: Final[dict[str, int]] = {"applies": 3, "likely_applies": 2, "check": 1}


@cache
def entries() -> tuple[dict[str, Any], ...]:
    """Every entry in the pack, after the seal check."""
    verify_pack(PACK)
    out: list[dict[str, Any]] = []
    for name in FILES:
        out.extend(json.loads((PACK / f"{name}.json").read_text(encoding="utf-8")))
    return tuple(out)


@dataclass(frozen=True, slots=True)
class Match:
    entry: dict[str, Any]
    confidence: str
    facts: tuple[str, ...]
    """The profile answers the deciding trigger read."""


def _facts_of(cond: dict[str, Any]) -> list[str]:
    if "all" in cond:
        return [f for c in cond["all"] for f in _facts_of(c)]
    if "any" in cond:
        return [f for c in cond["any"] for f in _facts_of(c)]
    return [cond["fact"]]


def match(entry: dict[str, Any], answers: dict[str, Any]) -> Match | None:
    best: Match | None = None
    for trigger in entry.get("triggers", []):
        cond = {k: trigger[k] for k in ("all", "any") if k in trigger}
        result = holds(cond, answers)
        if result is True:
            confidence = trigger["confidence"]
        elif result is None and entry.get("tier") == "most_should_know":
            confidence = "check"
        else:
            continue
        if best is None or _RANK[confidence] > _RANK[best.confidence]:
            best = Match(entry, confidence, tuple(dict.fromkeys(_facts_of(cond))))
    return best


def matches(answers: dict[str, Any]) -> list[Match]:
    found = [m for e in entries() if (m := match(e, answers)) is not None]
    return sorted(
        found, key=lambda m: (-_RANK[m.confidence], m.entry["jurisdiction"], m.entry["key"])
    )


def uncovered(answers: dict[str, Any]) -> list[str]:
    """Countries the company names that the pack does not cover yet (JC-7)."""
    named = [answers.get("hq_country"), *(answers.get("operating_countries") or [])]
    return sorted({c for c in named if isinstance(c, str) and len(c) == 2 and c not in COVERED})  # noqa: PLR2004
