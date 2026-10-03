"""What "ready" means, in one place.

The dashboard and the exported controls report both say how many controls are
"ready for audit", and an auditor holding both must not find two answers. Both
call these functions instead of each keeping its own reading of the word.

A control is ready when a person says it is implemented, there is evidence that
still counts, and no automated test says otherwise (AU-6). A requirement is met
only when every control that applies to it is ready (CF-4): one finished control
standing in for four unfinished ones is exactly the overstatement an auditor
finds on the first sample.

Automation can only take readiness away, never grant it. A control with no
connected provider, no run yet, or only "not applicable" results is "not
configured" (AU-5): it counts neither as passing nor as failing, and falls back
to its manual evidence path.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

# A failing test says the control is not working. An error says Verity could not
# tell, which is not a failure (rule 7) but is not a pass either, so a control
# nobody can currently verify is not claimed as ready. Stale says the last check
# is too old to say anything about now: a connection that stopped running a week
# ago must not keep a control green.
BLOCKING_AUTOMATION: Final = frozenset({"failing", "error", "stale"})

NOT_APPLICABLE: Final = "not_applicable"


def control_ready(*, status: str, has_current_evidence: bool, automation: str | None) -> bool:
    """Implemented, evidenced with something that still counts, and not contradicted."""
    return (
        status == "implemented" and has_current_evidence and automation not in BLOCKING_AUTOMATION
    )


def requirement_ready(controls: Iterable[tuple[str, bool]]) -> bool:
    """Whether a criterion is met, from its mapped controls as ``(status, ready)``.

    A control marked not applicable is out of scope for the criterion and is left
    out. A criterion with no applicable control left is not met: nothing is
    satisfying it, and "everything was ruled out" is a decision to be recorded,
    not a pass to be inferred.
    """
    applicable = [ready for status, ready in controls if status != NOT_APPLICABLE]
    return bool(applicable) and all(applicable)
