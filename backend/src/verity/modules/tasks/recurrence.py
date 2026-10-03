"""Repeat rules for tasks: a restricted RRULE and the date maths behind it.

The rule is stored as RFC 5545 text so any calendar tool can read it, but only four
parts are ever written or accepted: ``FREQ``, ``INTERVAL`` and one of ``UNTIL`` or
``COUNT``. That is everything the form can say, and refusing the rest means a stored rule
can never mean something the job below does not understand. Quarterly is not a frequency
of its own on the wire: it is monthly with three times the interval, which is also how a
calendar spells it.

Everything here is pure and uses only the standard library. The schedule is a function of
an *anchor* (the date the first task is due) and a position: occurrence ``k`` is the anchor
moved ``k`` steps. Computing each occurrence from the anchor, rather than from the one
before it, is what lets a monthly task due on the 31st land on the 28th in February and
back on the 31st in March, instead of drifting to the 28th for good.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Final

FREQUENCIES: Final[tuple[str, ...]] = ("daily", "weekly", "monthly", "quarterly", "yearly")

MAX_INTERVAL: Final = 999
MAX_COUNT: Final = 999

_RRULE_FREQ: Final[dict[str, str]] = {
    "daily": "DAILY",
    "weekly": "WEEKLY",
    "monthly": "MONTHLY",
    "yearly": "YEARLY",
}
_FREQ_FROM_RRULE: Final[dict[str, str]] = {v: k for k, v in _RRULE_FREQ.items()}

_UNIT: Final[dict[str, tuple[str, str]]] = {
    "daily": ("day", "days"),
    "weekly": ("week", "weeks"),
    "monthly": ("month", "months"),
    "yearly": ("year", "years"),
}
_ADVERB: Final[dict[str, str]] = {
    "daily": "Daily",
    "weekly": "Weekly",
    "monthly": "Monthly",
    "quarterly": "Quarterly",
    "yearly": "Yearly",
}

_UNTIL_LENGTH_DATE: Final = 8  # YYYYMMDD
_UNTIL_LENGTH_DATETIME: Final = 16  # YYYYMMDDTHHMMSSZ


@dataclass(frozen=True, slots=True)
class Repeat:
    """How a task repeats. ``count`` is the total number of tasks in the series, the
    first one included, as RFC 5545 counts it."""

    frequency: str
    interval: int = 1
    until: date | None = None
    count: int | None = None

    def __post_init__(self) -> None:
        if self.frequency not in FREQUENCIES:
            raise ValueError(f"unknown repeat frequency {self.frequency!r}")
        if not 1 <= self.interval <= MAX_INTERVAL:
            raise ValueError(f"repeat interval must be 1 to {MAX_INTERVAL}")
        if self.count is not None and not 1 <= self.count <= MAX_COUNT:
            raise ValueError(f"repeat count must be 1 to {MAX_COUNT}")
        if self.until is not None and self.count is not None:
            raise ValueError("a repeat ends on a date or after a count, not both")


def to_rrule(repeat: Repeat) -> str:
    """The stored form, for example ``FREQ=MONTHLY;INTERVAL=3;COUNT=4``."""
    if repeat.frequency == "quarterly":
        freq, interval = "MONTHLY", 3 * repeat.interval
    else:
        freq, interval = _RRULE_FREQ[repeat.frequency], repeat.interval
    parts = [f"FREQ={freq}", f"INTERVAL={interval}"]
    if repeat.until is not None:
        parts.append(f"UNTIL={repeat.until:%Y%m%d}")
    if repeat.count is not None:
        parts.append(f"COUNT={repeat.count}")
    return ";".join(parts)


def _parse_until(value: str) -> date:
    if len(value) == _UNTIL_LENGTH_DATETIME and value.endswith("Z") and value[8] == "T":
        value = value[:_UNTIL_LENGTH_DATE]
    if len(value) != _UNTIL_LENGTH_DATE or not value.isdigit():
        raise ValueError(f"unsupported UNTIL {value!r}")
    return date(int(value[:4]), int(value[4:6]), int(value[6:]))


def parse_rrule(rule: str) -> Repeat:
    """Read a stored rule back. Anything outside the restricted grammar is a
    ``ValueError``, so the caller can treat a hand-edited or imported rule as unreadable
    rather than guess what it meant."""
    text = rule.strip()
    if text.upper().startswith("RRULE:"):
        text = text[len("RRULE:") :]
    parts: dict[str, str] = {}
    for item in text.split(";"):
        key, sep, value = item.partition("=")
        key = key.strip().upper()
        if not sep or not value or key in parts:
            raise ValueError(f"unreadable repeat rule {rule!r}")
        parts[key] = value.strip()
    if parts.keys() - {"FREQ", "INTERVAL", "UNTIL", "COUNT"} or "FREQ" not in parts:
        raise ValueError(f"unsupported repeat rule {rule!r}")
    freq = _FREQ_FROM_RRULE.get(parts["FREQ"].upper())
    if freq is None:
        raise ValueError(f"unsupported FREQ in {rule!r}")
    interval = int(parts.get("INTERVAL", "1"))
    if freq == "monthly" and interval % 3 == 0:
        freq, interval = "quarterly", interval // 3
    return Repeat(
        frequency=freq,
        interval=interval,
        until=_parse_until(parts["UNTIL"]) if "UNTIL" in parts else None,
        count=int(parts["COUNT"]) if "COUNT" in parts else None,
    )


def _add_months(anchor: date, months: int) -> date:
    """``anchor`` moved by whole months, keeping its day of month where the month has it
    and clamping to the month's last day where it does not."""
    year, month_index = divmod(anchor.year * 12 + (anchor.month - 1) + months, 12)
    month = month_index + 1
    return date(year, month, min(anchor.day, calendar.monthrange(year, month)[1]))


def occurrence(anchor: date, repeat: Repeat, position: int) -> date | None:
    """The date of occurrence ``position`` (0 is the anchor itself), or None once the
    series has ended or runs off the calendar."""
    if position < 0:
        raise ValueError("an occurrence position cannot be negative")
    if repeat.count is not None and position >= repeat.count:
        return None
    steps = repeat.interval * position
    try:
        if repeat.frequency == "daily":
            moved = anchor + timedelta(days=steps)
        elif repeat.frequency == "weekly":
            moved = anchor + timedelta(weeks=steps)
        elif repeat.frequency == "monthly":
            moved = _add_months(anchor, steps)
        elif repeat.frequency == "quarterly":
            moved = _add_months(anchor, 3 * steps)
        else:
            moved = _add_months(anchor, 12 * steps)
    except (OverflowError, ValueError):
        return None
    if repeat.until is not None and moved > repeat.until:
        return None
    return moved


def _first_position_after(anchor: date, repeat: Repeat, after: date) -> int:
    """A position at or before the first one dated after ``after``. Never past it, so
    the caller can walk forward from here; close enough that the walk is a few steps."""
    if after <= anchor:
        return 1
    if repeat.frequency in ("daily", "weekly"):
        days = 1 if repeat.frequency == "daily" else 7
        return max(1, (after - anchor).days // (days * repeat.interval) - 1)
    months = (after.year - anchor.year) * 12 + after.month - anchor.month
    per_step = {"monthly": 1, "quarterly": 3, "yearly": 12}[repeat.frequency] * repeat.interval
    return max(1, months // per_step - 1)


def next_after(anchor: date, repeat: Repeat, after: date) -> date | None:
    """The first occurrence dated strictly after ``after``, never the anchor itself, or
    None when the series has no more."""
    position = _first_position_after(anchor, repeat, after)
    while True:
        moved = occurrence(anchor, repeat, position)
        if moved is None or moved > after:
            return moved
        position += 1


def summary(repeat: Repeat) -> str:
    """A short phrase for a badge: ``Monthly``, ``Every 2 weeks until 31 Dec 2026``,
    ``Quarterly, 4 times``."""
    if repeat.frequency == "quarterly":
        base = "Quarterly" if repeat.interval == 1 else f"Every {3 * repeat.interval} months"
    elif repeat.interval == 1:
        base = _ADVERB[repeat.frequency]
    else:
        base = f"Every {repeat.interval} {_UNIT[repeat.frequency][1]}"
    if repeat.until is not None:
        return f"{base} until {repeat.until.day} {repeat.until:%b} {repeat.until.year}"
    if repeat.count is not None:
        return f"{base}, {repeat.count} {'time' if repeat.count == 1 else 'times'}"
    return base
