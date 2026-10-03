"""Which severity a task ends up with.

Impact and urgency resolve to a severity through the tenant's matrix, and a person may
choose a different one. Choosing a different one is an override and has to say why: a
severity quietly softer than the matrix is the exact gap the reason exists to close, and
the database refuses an override with no reason as well (``ck_tasks__override_has_reason``).
A severity chosen with nothing to resolve against is not an override, because there is
nothing for it to differ from.

Pure, so the rule is testable without a database; the matrix lookup that feeds it is the
service's.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from verity.core.errors import InvalidInput

_REASON_ERROR: Final = (
    "The matrix gives a different severity for this impact and urgency. "
    "Say why you are overriding it, so the change can be reviewed later."
)


@dataclass(frozen=True, slots=True)
class SeverityDecision:
    """What to store: the severity shown everywhere, and the override with its reason
    when a person chose one."""

    severity: str | None
    override: str | None = None
    override_reason: str | None = None


def decide_severity(
    *, resolved: str | None, requested: str | None, reason: str | None
) -> SeverityDecision:
    """The severity for a task given the matrix result (``resolved``), the severity the
    person picked (``requested``) and the reason they gave for departing from the matrix."""
    if requested is None or requested == resolved:
        return SeverityDecision(severity=resolved)
    if resolved is None:
        return SeverityDecision(severity=requested)
    cleaned = (reason or "").strip()
    if not cleaned:
        raise InvalidInput(_REASON_ERROR, detail="severity override without a reason")
    return SeverityDecision(severity=requested, override=requested, override_reason=cleaned)
