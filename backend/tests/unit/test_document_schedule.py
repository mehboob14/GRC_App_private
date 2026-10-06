"""Review dates and the acknowledgement reminder calendar.

Both are pure rules that take the instant they are asked about, so every case below
pins its own clock. What they decide is what a person is told and when, which is why
the edges (a review due today, a reminder on the due date, the day after a manual
nudge) are spelled out rather than sampled.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from verity.modules.documents import schedule

TODAY = date(2026, 10, 6)


def _at(day: int, hour: int = 0, *, month: int = 10) -> datetime:
    return datetime(2026, month, day, hour, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Months
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("start", "months", "expected"),
    [
        (date(2026, 10, 6), 12, date(2027, 10, 6)),
        (date(2026, 1, 31), 1, date(2026, 2, 28)),
        (date(2024, 1, 31), 1, date(2024, 2, 29)),
        (date(2024, 2, 29), 12, date(2025, 2, 28)),
        (date(2026, 11, 30), 3, date(2027, 2, 28)),
        (date(2026, 12, 15), 1, date(2027, 1, 15)),
    ],
)
def test_adding_months_clips_to_the_end_of_a_shorter_month(
    start: date, months: int, expected: date
) -> None:
    assert schedule.add_months(start, months) == expected


# ---------------------------------------------------------------------------
# The review date a published document carries
# ---------------------------------------------------------------------------


def test_publishing_without_a_review_date_sets_one_a_year_out() -> None:
    assert schedule.next_review_on_publish(None, TODAY) == date(2027, 10, 6)


@pytest.mark.parametrize("lapsed", [date(2026, 10, 5), date(2025, 1, 1), TODAY])
def test_a_review_date_that_is_not_ahead_of_the_approval_starts_a_new_cycle(
    lapsed: date,
) -> None:
    """Re-approving a lapsed policy restarts the year. A review due the very day it is
    re-approved would otherwise come straight back overdue tomorrow."""
    assert schedule.next_review_on_publish(lapsed, TODAY) == date(2027, 10, 6)


@pytest.mark.parametrize("chosen", [date(2026, 10, 7), date(2027, 3, 1), date(2031, 1, 1)])
def test_a_review_date_a_person_chose_that_lies_ahead_is_kept(chosen: date) -> None:
    assert schedule.next_review_on_publish(chosen, TODAY) == chosen


# ---------------------------------------------------------------------------
# Overdue and due soon
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("renewal", "expected"),
    [
        (None, None),
        (TODAY - timedelta(days=1), "overdue"),
        (TODAY - timedelta(days=400), "overdue"),
        (TODAY, "due_soon"),
        (TODAY + timedelta(days=30), "due_soon"),
        (TODAY + timedelta(days=31), None),
    ],
)
def test_a_review_is_overdue_once_the_day_has_passed_and_due_soon_inside_thirty_days(
    renewal: date | None, expected: str | None
) -> None:
    """A review due today is not yet late: it is the day to do it."""
    assert schedule.review_status(renewal, TODAY) == expected


@pytest.mark.parametrize(
    ("renewal", "expected"),
    [
        (None, None),
        (TODAY - timedelta(days=1), "overdue"),
        (TODAY, "due"),
        (TODAY + timedelta(days=14), "due"),
        (TODAY + timedelta(days=15), None),
    ],
)
def test_the_owner_is_owed_a_notice_from_two_weeks_out_and_again_once_it_is_past(
    renewal: date | None, expected: str | None
) -> None:
    assert schedule.review_notice(renewal, TODAY) == expected


# ---------------------------------------------------------------------------
# A campaign's due day
# ---------------------------------------------------------------------------


def test_a_campaign_is_still_on_time_all_day_on_its_due_date() -> None:
    due = _at(20)
    assert schedule.campaign_overdue(due, _at(20, 15)) is False
    assert schedule.campaign_overdue(due, _at(21, 0)) is True
    assert schedule.campaign_overdue(due, _at(19)) is False
    assert schedule.campaign_overdue(None, _at(30)) is False


def test_the_due_day_is_a_utc_day() -> None:
    """02:00 at UTC+5 is 21:00 the evening before at UTC, so that is the due day."""
    due = datetime(2026, 10, 20, 2, 0, tzinfo=timezone(timedelta(hours=5)))
    assert schedule.campaign_overdue(due, _at(19, 22)) is False
    assert schedule.campaign_overdue(due, _at(20, 1)) is True


# ---------------------------------------------------------------------------
# The reminder calendar
# ---------------------------------------------------------------------------

DUE = _at(20)


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (_at(16, 23), None),
        (_at(17), date(2026, 10, 17)),
        (_at(19, 23), date(2026, 10, 17)),
        (_at(20), date(2026, 10, 20)),
        (_at(26, 23), date(2026, 10, 20)),
        (_at(27), date(2026, 10, 27)),
        (_at(2, month=11), date(2026, 10, 27)),
        (_at(3, month=11), date(2026, 11, 3)),
    ],
)
def test_the_calendar_is_three_days_before_the_due_date_then_the_day_then_weekly(
    now: datetime, expected: date | None
) -> None:
    assert schedule.latest_reminder_day(DUE, now) == expected


@pytest.mark.parametrize(
    ("now", "last_contact", "owed"),
    [
        # Too early for the first one, whoever was told when.
        (_at(16, 23), _at(1), False),
        # Three days out: owed until they have been chased on or after that day.
        (_at(17, 2), _at(1), True),
        (_at(17, 2), _at(17, 1), False),
        (_at(19), _at(17), False),
        # On the due date.
        (_at(20, 2), _at(17), True),
        (_at(20, 20), _at(20, 2), False),
        # Overdue: weekly, not daily.
        (_at(26), _at(20), False),
        (_at(27), _at(20), True),
        (_at(2, month=11), _at(27), False),
        (_at(3, month=11), _at(27), True),
    ],
)
def test_a_recipient_is_owed_a_reminder_only_when_a_date_on_the_calendar_has_passed_since_the_last(
    now: datetime, last_contact: datetime, owed: bool
) -> None:
    assert schedule.reminders_due(now, DUE, last_contact) is owed


def test_a_campaign_sent_inside_the_lead_waits_for_the_due_date() -> None:
    """The recipient was told when it was sent, so the three day reminder is spent."""
    sent = _at(18)
    assert schedule.reminders_due(_at(18, 5), DUE, sent) is False
    assert schedule.reminders_due(_at(19), DUE, sent) is False
    assert schedule.reminders_due(_at(20), DUE, sent) is True


def test_a_manual_reminder_never_shifts_the_calendar() -> None:
    """Chased by hand well before the first date, a person is still owed the three day
    reminder: the schedule is dates, not a count of reminders sent."""
    nudged = _at(10)
    assert schedule.reminders_due(_at(17), DUE, nudged) is True
    # Chased by hand on the 19th, they still hear on the due date.
    assert schedule.reminders_due(_at(20), DUE, _at(19, 9)) is True


def test_a_campaign_sent_after_its_due_date_is_chased_on_the_next_weekly_date() -> None:
    """Sent on 4 November for a 20 October deadline: told now, chased on the 10th."""
    sent = _at(4, month=11)
    assert schedule.reminders_due(_at(4, month=11), DUE, sent) is False
    assert schedule.reminders_due(_at(9, month=11), DUE, sent) is False
    assert schedule.reminders_due(_at(10, month=11), DUE, sent) is True
