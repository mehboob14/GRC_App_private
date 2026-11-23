"""One condition grammar for profile driven content (guided onboarding design 3.1).

``{"all": [...]}``, ``{"any": [...]}`` or a leaf ``{"fact": key, "op": op, "value": v}`` with
``eq``, ``in``, ``contains``, ``any_in`` and ``exists``. Country and region codes are expanded on
both sides, so ``EU`` matches a German operating country and the other way round. An answer of
"not sure", or no answer, makes a leaf unknown (``None``); callers decide what unknown means.
Pure: it never reads the database.
"""

from __future__ import annotations

from typing import Any, Final

from verity.shared.countries import expand

UNKNOWN: Final = "not_sure"


def _codes(value: object) -> set[str]:
    items = value if isinstance(value, list | set | tuple) else [value]
    return expand([str(v) for v in items])


def holds(cond: dict[str, Any], facts: dict[str, Any]) -> bool | None:  # noqa: PLR0911
    """True, False, or None when a fact it needs is unknown."""
    if "all" in cond:
        results = [holds(c, facts) for c in cond["all"]]
        if False in results:
            return False
        return None if None in results else True
    if "any" in cond:
        results = [holds(c, facts) for c in cond["any"]]
        if True in results:
            return True
        return None if None in results else False
    value = facts.get(cond["fact"])
    op = cond["op"]
    if op == "exists":
        return value not in (None, "", [], UNKNOWN)
    if value is None or value == UNKNOWN:
        return None
    wanted = cond["value"]
    if op == "eq":
        return bool(value == wanted) or (isinstance(value, str) and value in _codes(wanted))
    if op == "in":
        return value in wanted or (isinstance(value, str) and value in _codes(wanted))
    if op == "contains":
        return isinstance(value, list | set | tuple) and wanted in value
    if op == "any_in":
        if not isinstance(value, list | set | tuple):
            value = [value]
        return bool(set(map(str, value)) & set(map(str, wanted))) or bool(
            _codes(value) & _codes(wanted)
        )
    msg = f"unknown operator {op!r}"
    raise ValueError(msg)
