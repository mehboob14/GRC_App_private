"""What evidences a control: its checks, the systems that can run them, and what people provide.

A control is rarely proven by one thing. Version control settings show a change was
reviewed, a ticket shows it was requested, a policy shows the process exists, and a
sample shows it was followed. This module says, for one control, which of those come
from a connected system, which from a Verity module, and which a person supplies.

Pure functions over content rows: no database and no network. The service reads the
rows, this module says what they mean, and the rules can be tested on their own.

Three words are used the same way everywhere:

* a **check** is one automatable assertion (``vcs.review_required``),
* a **source** is a capability a check needs (version control, ticketing) together with
  the best state any of its providers is in for this workspace,
* an **evidence item** is something an auditor expects to see for the control, and it
  is collected automatically, supplied by a Verity module, or provided by a person.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final

PLATFORM_PROVIDER: Final = "verity"
"""The provider every workspace has: Verity's own modules, always connected."""

PLATFORM_PREFIX: Final = "verity_"

_STATE_RANK: Final = {"connected": 0, "available": 1, "planned": 2, "not_planned": 3}


@dataclass(frozen=True, slots=True)
class CapabilityFacts:
    key: str
    name: str
    providers: Sequence[Mapping[str, Any]]
    """``{key, name, status, phase}``: status is available, planned or not_planned."""


@dataclass(frozen=True, slots=True)
class CheckFacts:
    key: str
    capabilities: Sequence[str]
    implementations: Sequence[str]


@dataclass(frozen=True, slots=True)
class Source:
    key: str
    name: str
    kind: str
    """``connector`` (a system the workspace connects) or ``platform`` (Verity itself)."""
    state: str
    """connected, available (can be connected now), planned, or not_planned."""
    providers: tuple[str, ...]
    """Names of the providers in that state, for display."""
    provider_keys: tuple[str, ...]
    """Their keys, in the same order, for logos and for acting on them."""
    checks: int


@dataclass(frozen=True, slots=True)
class Composition:
    mode: str
    """By design, once every planned system ships: automated, hybrid or manual."""
    checks_total: int
    checks_running: int
    checks_ready: int
    checks_planned: int
    sources: list[Source] = field(default_factory=list)
    items_total: int = 0
    items_automatic: int = 0
    items_planned: int = 0
    items_platform: int = 0
    items_manual: int = 0


def is_platform(capabilities: Iterable[str]) -> bool:
    """A check that reads only Verity's own modules."""
    keys = list(capabilities)
    return bool(keys) and all(key.startswith(PLATFORM_PREFIX) for key in keys)


def provider_state(provider: Mapping[str, Any], connected: set[str]) -> str:
    """One provider of a capability, for one workspace.

    ``connected`` only when a collector ships for this capability *and* the
    workspace has the provider connected: GitHub being connected says nothing about
    a pipeline check that is still planned for it. Verity is always connected.
    """
    status = str(provider["status"])
    if status == "available" and (
        provider["key"] in connected or provider["key"] == PLATFORM_PROVIDER
    ):
        return "connected"
    return status


def capability_state(capability: CapabilityFacts, connected: set[str]) -> str:
    """The best state any provider of the capability is in."""
    states = [provider_state(p, connected) for p in capability.providers]
    return min(states, key=_STATE_RANK.__getitem__, default="not_planned")


def availability(
    check: CheckFacts, capabilities: Mapping[str, CapabilityFacts], connected: set[str]
) -> str:
    """Whether a workspace can have this check run.

    ``running``: a connected system (or Verity) runs it. ``ready``: a collector ships
    and the workspace has only to connect it. ``planned``: no collector yet, but the
    systems it needs are in the plan. ``not_planned``: a system it needs is not.
    """
    if any(i in connected or i == PLATFORM_PROVIDER for i in check.implementations):
        return "running"
    if check.implementations:
        return "ready"
    states = [
        capability_state(capabilities[key], connected)
        for key in check.capabilities
        if key in capabilities
    ]
    return "not_planned" if "not_planned" in states or not states else "planned"


def sources_for(
    checks: Sequence[CheckFacts],
    capabilities: Mapping[str, CapabilityFacts],
    connected: set[str],
) -> list[Source]:
    """One source per capability the control's checks need, best connected first."""
    needed: dict[str, int] = {}
    for check in checks:
        for key in check.capabilities:
            needed[key] = needed.get(key, 0) + 1
    sources: list[Source] = []
    for key, count in needed.items():
        capability = capabilities.get(key)
        if capability is None:
            continue
        state = capability_state(capability, connected)
        best = [p for p in capability.providers if provider_state(p, connected) == state]
        sources.append(
            Source(
                key=key,
                name=capability.name,
                kind="platform" if key.startswith(PLATFORM_PREFIX) else "connector",
                state=state,
                providers=tuple(str(p["name"]) for p in best),
                provider_keys=tuple(str(p["key"]) for p in best),
                checks=count,
            )
        )
    return sorted(sources, key=lambda s: (_STATE_RANK[s.state], s.kind == "platform", s.name))


def item_state(item: Mapping[str, Any], availability_by_check: Mapping[str, str]) -> str:
    """How one expected piece of evidence reaches the control right now.

    ``automatic``: every check that collects it is running. ``partial``: some are, and
    a person supplies the rest. ``when_connected``: a check that can run today
    collects it once a system is connected. ``planned``: a check will, but not yet, so
    a person supplies it for now. ``platform``: a Verity module holds it. ``manual``: a
    person provides it, and no check is going to.
    """
    states = [availability_by_check.get(k, "not_planned") for k in item.get("automated_by", [])]
    if states and all(s == "running" for s in states):
        return "automatic"
    if "running" in states:
        return "partial"
    if "ready" in states:
        return "when_connected"
    if "planned" in states:
        return "planned"
    return "platform" if item.get("source") == "platform" else "manual"


def compose(
    checks: Sequence[CheckFacts],
    capabilities: Mapping[str, CapabilityFacts],
    connected: set[str],
    evidence: Sequence[Mapping[str, Any]],
) -> Composition:
    """The composition of one control from its checks and its expected evidence.

    The mode is by design, not by what is connected today: ``manual`` when no check
    can evidence the control, ``hybrid`` when checks exist and a person still has to
    supply operating evidence that no check will collect, and ``automated`` when the
    checks and the Verity modules cover the operating evidence. What is running today
    is stated beside it by the counts, never folded into the word.
    """
    by_check = {c.key: availability(c, capabilities, connected) for c in checks}
    states = [item_state(item, by_check) for item in evidence]
    person_supplies_operating = any(
        item.get("assurance") == "operating" and state == "manual"
        for item, state in zip(evidence, states, strict=True)
    )
    if not checks:
        mode = "manual"
    elif person_supplies_operating:
        mode = "hybrid"
    else:
        mode = "automated"
    return Composition(
        mode=mode,
        checks_total=len(checks),
        checks_running=sum(1 for v in by_check.values() if v == "running"),
        checks_ready=sum(1 for v in by_check.values() if v == "ready"),
        checks_planned=sum(1 for v in by_check.values() if v in ("planned", "not_planned")),
        sources=sources_for(checks, capabilities, connected),
        items_total=len(evidence),
        items_automatic=sum(1 for s in states if s in ("automatic", "partial", "when_connected")),
        items_planned=sum(1 for s in states if s == "planned"),
        items_platform=sum(1 for s in states if s == "platform"),
        items_manual=sum(1 for s in states if s == "manual"),
    )
