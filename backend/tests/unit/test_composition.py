"""What evidences a control: the rules that turn checks and evidence into a composition."""

from __future__ import annotations

from typing import Any

from verity.modules.connectors.composition import (
    CapabilityFacts,
    CheckFacts,
    availability,
    capability_state,
    compose,
    is_platform,
    item_state,
    provider_state,
    sources_for,
)

VCS = CapabilityFacts(
    "version_control",
    "Version control",
    [
        {"key": "github", "name": "GitHub", "status": "available", "phase": None},
        {"key": "gitlab", "name": "GitLab", "status": "planned", "phase": "Phase 2"},
    ],
)
CI = CapabilityFacts(
    "ci_cd",
    "CI and CD",
    [{"key": "github", "name": "GitHub", "status": "planned", "phase": "Phase 2"}],
)
HR = CapabilityFacts(
    "hr_system", "HR system", [{"key": "workday", "name": "Workday", "status": "not_planned"}]
)
PLATFORM = CapabilityFacts(
    "verity_policies",
    "Verity policies",
    [{"key": "verity", "name": "Verity (built in)", "status": "planned", "phase": "Phase 2"}],
)
CAPS = {c.key: c for c in (VCS, CI, HR, PLATFORM)}

REVIEW = CheckFacts("vcs.review_required", ["version_control"], ["github"])
PIPELINE = CheckFacts("ci.required_checks_passed", ["ci_cd"], [])
LEAVERS = CheckFacts("people.leavers", ["hr_system"], [])


def test_a_connected_provider_that_runs_the_check_makes_it_running() -> None:
    assert availability(REVIEW, CAPS, {"github"}) == "running"


def test_a_collector_that_ships_but_is_not_connected_is_ready() -> None:
    assert availability(REVIEW, CAPS, set()) == "ready"


def test_a_check_with_no_collector_is_planned_while_its_systems_are_in_the_plan() -> None:
    assert availability(PIPELINE, CAPS, {"github"}) == "planned"


def test_a_check_needing_a_system_outside_the_plan_is_not_planned() -> None:
    assert availability(LEAVERS, CAPS, set()) == "not_planned"


def test_a_connected_provider_is_not_connected_for_a_capability_it_has_no_collector_for() -> None:
    """GitHub is connected, but its pipeline checks are only planned."""
    github_for_pipelines = CI.providers[0]
    assert provider_state(github_for_pipelines, {"github"}) == "planned"
    assert capability_state(CI, {"github"}) == "planned"
    assert capability_state(VCS, {"github"}) == "connected"


def test_verity_is_always_connected_once_its_collector_ships() -> None:
    shipped = {"key": "verity", "name": "Verity (built in)", "status": "available"}
    assert provider_state(shipped, set()) == "connected"
    assert provider_state(PLATFORM.providers[0], set()) == "planned"


def test_platform_checks_are_those_that_read_only_verity_modules() -> None:
    assert is_platform(["verity_policies"])
    assert not is_platform(["version_control", "verity_policies"])
    assert not is_platform([])


def test_sources_list_each_capability_once_best_connected_first() -> None:
    sources = sources_for([REVIEW, PIPELINE, LEAVERS], CAPS, {"github"})
    assert [(s.key, s.state) for s in sources] == [
        ("version_control", "connected"),
        ("ci_cd", "planned"),
        ("hr_system", "not_planned"),
    ]
    assert sources[0].providers == ("GitHub",)
    assert sources[0].kind == "connector"


def test_an_item_only_part_collected_by_running_checks_says_so() -> None:
    item = {"automated_by": ["a", "b"], "source": "upload"}
    assert item_state(item, {"a": "running", "b": "running"}) == "automatic"
    assert item_state(item, {"a": "running", "b": "planned"}) == "partial"
    assert item_state(item, {"a": "ready", "b": "planned"}) == "when_connected"


def test_an_item_a_running_check_collects_is_automatic() -> None:
    item = {"automated_by": ["vcs.review_required"], "source": "upload"}
    assert item_state(item, {"vcs.review_required": "running"}) == "automatic"
    assert item_state(item, {"vcs.review_required": "ready"}) == "when_connected"
    assert item_state(item, {"vcs.review_required": "planned"}) == "planned"
    assert item_state(item, {"vcs.review_required": "not_planned"}) == "manual"


def test_an_item_no_check_collects_is_a_module_or_a_person() -> None:
    assert item_state({"source": "platform"}, {}) == "platform"
    assert item_state({"source": "upload"}, {}) == "manual"


def test_a_control_with_no_checks_is_manual() -> None:
    composition = compose([], CAPS, set(), [{"assurance": "design", "source": "upload"}])
    assert composition.mode == "manual"
    assert composition.items_manual == 1
    assert composition.sources == []


def test_a_policy_a_module_holds_does_not_make_an_automated_control_hybrid() -> None:
    evidence: list[dict[str, Any]] = [
        {"assurance": "design", "source": "platform", "module": "documents"},
        {"assurance": "operating", "source": "upload", "automated_by": ["vcs.review_required"]},
    ]
    composition = compose([REVIEW], CAPS, {"github"}, evidence)
    assert composition.mode == "automated"
    assert composition.items_automatic == 1
    assert composition.items_platform == 1


def test_operating_evidence_only_a_person_can_supply_makes_it_hybrid() -> None:
    evidence = [{"assurance": "operating", "source": "upload", "key": "sample"}]
    composition = compose([REVIEW], CAPS, set(), evidence)
    assert composition.mode == "hybrid"
    assert composition.items_manual == 1


def test_the_mode_is_by_design_and_the_counts_say_what_runs_today() -> None:
    evidence = [{"assurance": "operating", "source": "upload", "automated_by": ["x"]}]
    planned = CheckFacts("x", ["ci_cd"], [])
    composition = compose([planned], CAPS, {"github"}, evidence)
    assert composition.mode == "automated"
    assert (composition.checks_running, composition.checks_ready, composition.checks_planned) == (
        0,
        0,
        1,
    )
    assert composition.items_planned == 1
