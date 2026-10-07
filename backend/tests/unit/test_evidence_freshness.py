"""When evidence starts reading as aging: the last 30 days, or the last third of a shorter life."""

from __future__ import annotations

from datetime import date, timedelta

from verity.modules.evidence.service import freshness

TODAY = date(2026, 10, 6)


def test_an_item_with_no_renewal_date_never_expires() -> None:
    assert freshness(None, today=TODAY) == "no_expiry"


def test_a_long_lived_item_is_aging_only_in_its_last_thirty_days() -> None:
    collected = TODAY - timedelta(days=100)
    assert freshness(TODAY + timedelta(days=31), collected_at=collected, today=TODAY) == "current"
    assert freshness(TODAY + timedelta(days=30), collected_at=collected, today=TODAY) == "aging"
    assert freshness(TODAY - timedelta(days=1), collected_at=collected, today=TODAY) == "stale"


def test_a_connector_result_is_current_when_filed_and_aging_in_its_last_two_days() -> None:
    # Valid for a week, then replaced by the next run: it is not aging the moment it is filed.
    renewal = TODAY + timedelta(days=7)
    assert freshness(renewal, collected_at=TODAY, today=TODAY) == "current"
    assert freshness(renewal, collected_at=TODAY, today=TODAY + timedelta(days=4)) == "current"
    assert freshness(renewal, collected_at=TODAY, today=TODAY + timedelta(days=5)) == "aging"
    assert freshness(renewal, collected_at=TODAY, today=TODAY + timedelta(days=8)) == "stale"


def test_without_a_collection_date_the_thirty_day_window_applies() -> None:
    assert freshness(TODAY + timedelta(days=7), today=TODAY) == "aging"
