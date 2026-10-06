"""When a document's review falls due, and when an unsigned acknowledgement is chased.

Pure rules with no database and no clock of their own: every function takes the
instant (or the day) it is asked about, so the service and the daily sweeps share one
definition and a test can pin it to any date. Days are UTC days, the same calendar
the sweeps and the audit trail run on.
"""

from __future__ import annotations

import calendar
from datetime import UTC, date, datetime, timedelta
from typing import Final, Literal

# ponytail: one interval for every document. Make it a column on the document, or a
# default per document type, the day a client wants an annual policy and a biennial
# charter side by side.
REVIEW_INTERVAL_MONTHS: Final = 12
"""How long a policy is good for once it is approved and published."""

REVIEW_SOON_DAYS: Final = 30
"""A review this close is flagged "Due soon" in the register and counted as such."""

REVIEW_NOTICE_DAYS: Final = 14
"""The owner is told this many days before the review date, then once it has passed."""

REMINDER_LEAD_DAYS: Final = 3
"""The first automatic acknowledgement reminder, ahead of the due date."""

REMINDER_REPEAT_DAYS: Final = 7
"""While a campaign is overdue, an unsigned recipient is chased this often."""

REMINDER_COOLDOWN: Final = timedelta(hours=24)
"""A manual reminder skips anyone who was chased more recently than this."""

ReviewStatus = Literal["overdue", "due_soon"]
ReviewNotice = Literal["due", "overdue"]


def add_months(day: date, months: int) -> date:
    """``day`` plus whole months, clipped to the end of a shorter month
    (31 Jan plus one month is 28 or 29 Feb, never an error)."""
    index = day.year * 12 + (day.month - 1) + months
    year, month = divmod(index, 12)
    month += 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def next_review_on_publish(current: date | None, approved_on: date) -> date:
    """The review date a document carries once it is published.

    A date a person chose that still lies ahead is theirs and is kept. Empty, or no
    longer ahead of the approval (a lapsed review being re-approved today starts a
    new cycle rather than coming back overdue tomorrow), it restarts from the
    approval date."""
    if current is not None and current > approved_on:
        return current
    return add_months(approved_on, REVIEW_INTERVAL_MONTHS)


def review_status(renewal_date: date | None, today: date) -> ReviewStatus | None:
    """``overdue`` once the date has passed, ``due_soon`` inside the next 30 days
    (today included), nothing otherwise. A review due today is not yet late."""
    if renewal_date is None:
        return None
    if renewal_date < today:
        return "overdue"
    if renewal_date <= today + timedelta(days=REVIEW_SOON_DAYS):
        return "due_soon"
    return None


def review_notice(renewal_date: date | None, today: date) -> ReviewNotice | None:
    """Which notice the owner is owed today: ``due`` from 14 days out up to and
    including the date itself, ``overdue`` once it has passed."""
    if renewal_date is None:
        return None
    if renewal_date < today:
        return "overdue"
    if renewal_date <= today + timedelta(days=REVIEW_NOTICE_DAYS):
        return "due"
    return None


def campaign_overdue(due_at: datetime | None, now: datetime) -> bool:
    """The due day is behind us. A due date names a day, not a minute: a campaign due
    on the 20th is still on time at noon on the 20th."""
    return due_at is not None and due_at.astimezone(UTC).date() < now.astimezone(UTC).date()


def latest_reminder_day(due_at: datetime, now: datetime) -> date | None:
    """The most recent day on the reminder calendar that has arrived, if any.

    The calendar is three days before the due date, the due date itself, then every
    seven days after it while the campaign stays open. It is a set of dates rather
    than a count of reminders sent, so a manual reminder never shifts it."""
    today = now.astimezone(UTC).date()
    due_day = due_at.astimezone(UTC).date()
    first = due_day - timedelta(days=REMINDER_LEAD_DAYS)
    if today < first:
        return None
    if today < due_day:
        return first
    late_cycles = (today - due_day).days // REMINDER_REPEAT_DAYS
    return due_day + timedelta(days=late_cycles * REMINDER_REPEAT_DAYS)


def reminders_due(now: datetime, due_at: datetime, last_contact_at: datetime) -> bool:
    """Whether an unsigned recipient is owed an automatic reminder at ``now``.

    ``last_contact_at`` is the last time they were told about the campaign: the
    reminder before this one, or the day it was sent if they have had none. Someone
    contacted on or after the latest date on the calendar has had their turn;
    anyone who last heard before it is owed one."""
    milestone = latest_reminder_day(due_at, now)
    return milestone is not None and last_contact_at.astimezone(UTC).date() < milestone
