"""Which severity a task ends up with, given the matrix and what the person chose.

The rule is the compliance one: a severity different from the matrix is an override and
says why. It is pure, so it is pinned here; that the service feeds it the workspace's own
matrix is covered through the app in the integration suite.
"""

from __future__ import annotations

import pytest

from verity.core.errors import InvalidInput
from verity.modules.tasks.severity import SeverityDecision, decide_severity


def test_the_matrix_result_stands_when_nothing_else_was_chosen() -> None:
    assert decide_severity(resolved="high", requested=None, reason=None) == SeverityDecision("high")


def test_choosing_what_the_matrix_says_is_not_an_override() -> None:
    decision = decide_severity(resolved="high", requested="high", reason="irrelevant")
    assert decision == SeverityDecision("high")
    assert decision.override is None
    assert decision.override_reason is None


def test_choosing_something_else_is_an_override_with_its_reason() -> None:
    decision = decide_severity(resolved="high", requested="low", reason="  Compensating control  ")
    assert decision == SeverityDecision("low", "low", "Compensating control")


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_an_override_without_a_reason_is_refused(reason: str | None) -> None:
    with pytest.raises(InvalidInput, match="why"):
        decide_severity(resolved="high", requested="low", reason=reason)


def test_a_severity_with_nothing_to_resolve_against_is_simply_that_severity() -> None:
    """No impact and urgency means no matrix result, so there is nothing to override and
    no reason is asked for."""
    assert decide_severity(resolved=None, requested="medium", reason=None) == SeverityDecision(
        "medium"
    )


def test_no_severity_at_all_is_allowed() -> None:
    assert decide_severity(resolved=None, requested=None, reason=None) == SeverityDecision(None)
