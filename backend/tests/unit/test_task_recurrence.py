"""The repeat rule of a task: its stored text and the dates it produces.

The date maths is the part of recurring tasks that fails quietly, as a task on the wrong
day or one that never comes, so it is pinned here without a database: month ends, the
quarter, leap days, where a series stops, and the round trip through the stored RRULE.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from verity.modules.tasks.recurrence import (
    Repeat,
    next_after,
    occurrence,
    parse_rrule,
    summary,
    to_rrule,
)

# -- month ends ---------------------------------------------------------------


def test_a_monthly_task_due_on_the_31st_lands_on_the_last_day_of_a_short_month() -> None:
    anchor = date(2027, 1, 31)
    repeat = Repeat("monthly")
    assert occurrence(anchor, repeat, 1) == date(2027, 2, 28)
    assert occurrence(anchor, repeat, 3) == date(2027, 4, 30)


def test_the_31st_comes_back_after_a_short_month_rather_than_drifting() -> None:
    """Each date is counted from the anchor, not from the one before it. Counted from the
    one before, February's 28th would carry on into March, April and every month after."""
    anchor = date(2027, 1, 31)
    repeat = Repeat("monthly")
    assert occurrence(anchor, repeat, 2) == date(2027, 3, 31)
    assert occurrence(anchor, repeat, 12) == date(2028, 1, 31)


def test_february_in_a_leap_year_keeps_the_29th() -> None:
    assert occurrence(date(2028, 1, 31), Repeat("monthly"), 1) == date(2028, 2, 29)
    assert occurrence(date(2028, 1, 29), Repeat("monthly"), 1) == date(2028, 2, 29)
    assert occurrence(date(2027, 1, 29), Repeat("monthly"), 1) == date(2027, 2, 28)


def test_a_leap_day_task_is_due_on_the_28th_until_the_next_leap_year() -> None:
    anchor = date(2028, 2, 29)
    repeat = Repeat("yearly")
    assert occurrence(anchor, repeat, 1) == date(2029, 2, 28)
    assert occurrence(anchor, repeat, 4) == date(2032, 2, 29)


# -- the quarter ----------------------------------------------------------------


def test_quarterly_is_every_three_months() -> None:
    anchor = date(2026, 11, 30)
    repeat = Repeat("quarterly")
    assert occurrence(anchor, repeat, 1) == date(2027, 2, 28)
    assert occurrence(anchor, repeat, 2) == date(2027, 5, 30)
    assert occurrence(anchor, repeat, 4) == date(2027, 11, 30)


def test_quarterly_with_an_interval_counts_quarters() -> None:
    assert occurrence(date(2026, 1, 15), Repeat("quarterly", interval=2), 1) == date(2026, 7, 15)


def test_quarterly_is_stored_as_monthly_with_three_times_the_interval() -> None:
    assert to_rrule(Repeat("quarterly")) == "FREQ=MONTHLY;INTERVAL=3"
    assert to_rrule(Repeat("quarterly", interval=2)) == "FREQ=MONTHLY;INTERVAL=6"


# -- the other frequencies --------------------------------------------------------


def test_daily_and_weekly_step_by_the_interval() -> None:
    anchor = date(2026, 10, 5)
    assert occurrence(anchor, Repeat("daily", interval=3), 2) == date(2026, 10, 11)
    assert occurrence(anchor, Repeat("weekly"), 1) == date(2026, 10, 12)
    assert occurrence(anchor, Repeat("weekly", interval=2), 2) == date(2026, 11, 2)


def test_position_zero_is_the_anchor_itself() -> None:
    anchor = date(2026, 10, 5)
    for frequency in ("daily", "weekly", "monthly", "quarterly", "yearly"):
        assert occurrence(anchor, Repeat(frequency), 0) == anchor


# -- where a series stops ------------------------------------------------------


def test_until_is_inclusive_and_nothing_follows_it() -> None:
    anchor = date(2026, 10, 5)
    repeat = Repeat("weekly", until=date(2026, 10, 19))
    assert occurrence(anchor, repeat, 2) == date(2026, 10, 19)
    assert occurrence(anchor, repeat, 3) is None
    assert next_after(anchor, repeat, date(2026, 10, 19)) is None


def test_count_includes_the_first_task() -> None:
    """Three in the series is the head and two more, as RFC 5545 counts."""
    anchor = date(2026, 10, 5)
    repeat = Repeat("daily", count=3)
    assert [occurrence(anchor, repeat, k) for k in range(4)] == [
        date(2026, 10, 5),
        date(2026, 10, 6),
        date(2026, 10, 7),
        None,
    ]


def test_a_series_of_one_never_repeats() -> None:
    assert next_after(date(2026, 10, 5), Repeat("daily", count=1), date(2026, 10, 5)) is None


def test_a_series_that_runs_off_the_calendar_ends_instead_of_raising() -> None:
    assert occurrence(date(9999, 12, 31), Repeat("daily"), 1) is None
    assert occurrence(date(9999, 6, 1), Repeat("yearly"), 1) is None


# -- the next date -----------------------------------------------------------------


def test_next_after_the_anchor_is_the_first_step() -> None:
    anchor = date(2027, 1, 31)
    assert next_after(anchor, Repeat("monthly"), anchor) == date(2027, 2, 28)


def test_next_after_is_strictly_later_than_the_date_given() -> None:
    anchor = date(2026, 10, 5)
    assert next_after(anchor, Repeat("weekly"), date(2026, 10, 12)) == date(2026, 10, 19)
    assert next_after(anchor, Repeat("weekly"), date(2026, 10, 11)) == date(2026, 10, 12)


def test_next_after_skips_every_date_already_past() -> None:
    anchor = date(2026, 10, 5)
    # 53 weeks on from the anchor is 11 Oct 2027, the first Monday after a year has gone.
    assert next_after(anchor, Repeat("weekly"), date(2027, 10, 5)) == date(2027, 10, 11)
    assert next_after(date(2027, 1, 31), Repeat("monthly"), date(2027, 3, 1)) == date(2027, 3, 31)


def test_next_after_a_long_gap_is_not_a_long_walk() -> None:
    far = date(2126, 1, 1)
    assert next_after(date(2026, 1, 1), Repeat("daily"), far) == far + timedelta(days=1)


@pytest.mark.parametrize("frequency", ["daily", "weekly", "monthly", "quarterly", "yearly"])
@pytest.mark.parametrize("anchor_day", [1, 15, 28, 29, 30, 31])
def test_every_next_date_is_later_than_the_one_before_it(frequency: str, anchor_day: int) -> None:
    anchor = date(2027, 1, anchor_day)
    repeat = Repeat(frequency, interval=2)
    seen = anchor
    for _ in range(40):
        following = next_after(anchor, repeat, seen)
        assert following is not None
        assert following > seen
        seen = following


# -- the stored rule -------------------------------------------------------------


def test_a_rule_reads_back_as_the_repeat_that_wrote_it() -> None:
    for repeat in (
        Repeat("daily"),
        Repeat("weekly", interval=2, until=date(2026, 12, 31)),
        Repeat("monthly", count=6),
        Repeat("quarterly", interval=2, count=4),
        Repeat("yearly", interval=3),
    ):
        assert parse_rrule(to_rrule(repeat)) == repeat


def test_the_rule_text_is_plain_rfc_5545() -> None:
    assert to_rrule(Repeat("weekly", interval=2, until=date(2026, 12, 31))) == (
        "FREQ=WEEKLY;INTERVAL=2;UNTIL=20261231"
    )
    assert to_rrule(Repeat("monthly", count=6)) == "FREQ=MONTHLY;INTERVAL=1;COUNT=6"


def test_a_rule_without_an_interval_repeats_every_one() -> None:
    assert parse_rrule("FREQ=DAILY") == Repeat("daily")
    assert parse_rrule("RRULE:FREQ=YEARLY") == Repeat("yearly")


def test_until_may_be_a_date_or_a_utc_timestamp() -> None:
    assert parse_rrule("FREQ=DAILY;UNTIL=20261231").until == date(2026, 12, 31)
    assert parse_rrule("FREQ=DAILY;UNTIL=20261231T235959Z").until == date(2026, 12, 31)


@pytest.mark.parametrize(
    "rule",
    [
        "",
        "nonsense",
        "FREQ=HOURLY",
        "FREQ=WEEKLY;BYDAY=MO",
        "FREQ=DAILY;COUNT=2;UNTIL=20261231",
        "FREQ=DAILY;FREQ=WEEKLY",
        "INTERVAL=2",
        "FREQ=DAILY;INTERVAL=0",
        "FREQ=DAILY;INTERVAL=two",
        "FREQ=DAILY;COUNT=0",
        "FREQ=DAILY;UNTIL=soon",
        "FREQ=DAILY;",
    ],
)
def test_a_rule_outside_what_this_module_writes_is_refused(rule: str) -> None:
    with pytest.raises(ValueError, match=r"."):
        parse_rrule(rule)


def test_a_repeat_has_to_make_sense() -> None:
    with pytest.raises(ValueError, match="frequency"):
        Repeat("hourly")
    with pytest.raises(ValueError, match="interval"):
        Repeat("daily", interval=0)
    with pytest.raises(ValueError, match="count"):
        Repeat("daily", count=0)
    with pytest.raises(ValueError, match="not both"):
        Repeat("daily", until=date(2026, 12, 31), count=3)


# -- the words ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("repeat", "words"),
    [
        (Repeat("daily"), "Daily"),
        (Repeat("weekly"), "Weekly"),
        (Repeat("monthly"), "Monthly"),
        (Repeat("quarterly"), "Quarterly"),
        (Repeat("yearly"), "Yearly"),
        (Repeat("daily", interval=3), "Every 3 days"),
        (Repeat("weekly", interval=2), "Every 2 weeks"),
        (Repeat("quarterly", interval=2), "Every 6 months"),
        (Repeat("monthly", until=date(2026, 12, 31)), "Monthly until 31 Dec 2026"),
        (Repeat("quarterly", count=4), "Quarterly, 4 times"),
        (Repeat("yearly", count=1), "Yearly, 1 time"),
    ],
)
def test_the_summary_reads_as_a_phrase(repeat: Repeat, words: str) -> None:
    assert summary(repeat) == words
