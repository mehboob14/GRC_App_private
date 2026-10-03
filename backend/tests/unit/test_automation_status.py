"""How a control's automated status is read from its tests, and what changes a run's evidence."""

from __future__ import annotations

from typing import Any

from verity.modules.compliance.readiness import BLOCKING_AUTOMATION, control_ready
from verity.modules.connectors import github
from verity.modules.connectors.service import _control_status, _digest, _test_status


def _result(detail: dict[str, object]) -> github.Result:
    return github.Result("vcs.review_required", "repository", "1", "acme/api", "pass", detail)


def test_a_test_whose_results_are_too_old_is_stale_not_pass_or_fail() -> None:
    kwargs: dict[str, Any] = {"implemented": True, "runners": True}
    assert _test_status(**kwargs, outcomes=["pass"], stale=True) == "stale"
    assert _test_status(**kwargs, outcomes=["fail"], stale=True) == "stale"
    assert _test_status(**kwargs, outcomes=["pass"]) == "pass"
    # Nothing to be stale about before a first run.
    assert _test_status(**kwargs, outcomes=[], stale=True) == "pending"


def test_a_finished_run_that_left_no_result_found_nothing_to_check_it_is_not_still_waiting() -> (
    None
):
    kwargs: dict[str, Any] = {"implemented": True, "runners": True, "outcomes": []}
    assert _test_status(**kwargs) == "pending"
    assert _test_status(**kwargs, ran=True) == "not_applicable"
    # A system that cannot run it, or no collector at all, says so before anything else.
    assert _test_status(implemented=True, runners=False, outcomes=[], ran=True) == "not_connected"
    assert _test_status(implemented=False, runners=False, outcomes=[], ran=True) == "not_available"


def test_a_control_with_a_stale_test_is_stale_unless_something_fresh_failed() -> None:
    assert _control_status(["pass", "stale"]) == "stale"
    assert _control_status(["stale"]) == "stale"
    assert _control_status(["fail", "stale"]) == "failing"
    assert _control_status(["error", "stale"]) == "error"
    assert _control_status(["pass", "pass"]) == "passing"


def test_a_stale_control_is_not_ready_however_it_is_marked() -> None:
    assert "stale" in BLOCKING_AUTOMATION
    assert not control_ready(status="implemented", has_current_evidence=True, automation="stale")
    assert control_ready(status="implemented", has_current_evidence=True, automation="passing")


def test_a_run_whose_detail_changed_under_an_unchanged_outcome_is_a_different_observation() -> None:
    same = _digest([_result({"summary": "1 approving review required to merge."})])
    assert same == _digest([_result({"summary": "1 approving review required to merge."})])
    assert same != _digest([_result({"summary": "2 approving reviews required to merge."})])
    assert same != _digest([_result({"summary": "1 approving review required to merge.", "x": 1})])
