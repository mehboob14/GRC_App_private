"""The Celery application and its one task."""

from __future__ import annotations

from verity.workers.celery_app import celery_app
from verity.workers.tasks import heartbeat


def test_only_json_is_accepted() -> None:
    """Pickle would let a compromised broker run code in a worker that holds the
    database credentials and the encryption master key."""
    assert celery_app.conf.task_serializer == "json"
    assert tuple(celery_app.conf.accept_content) == ("json",)


def test_times_are_utc() -> None:
    assert str(celery_app.conf.timezone) == "UTC"
    assert celery_app.conf.enable_utc is True


def test_a_task_is_acknowledged_only_after_it_finishes() -> None:
    """A worker killed mid-task gives the task back rather than losing it. Safe because
    every scheduled job is documented as idempotent (backend/CLAUDE.md)."""
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True


def test_workers_do_not_prefetch() -> None:
    assert celery_app.conf.worker_prefetch_multiplier == 1


def test_the_scheduler_has_an_entry() -> None:
    assert "platform-heartbeat" in celery_app.conf.beat_schedule


def test_the_task_is_registered_under_its_documented_name() -> None:
    assert "verity.workers.tasks.heartbeat" in celery_app.tasks


def test_heartbeat_touches_nothing() -> None:
    result = heartbeat.apply().get()
    assert result["status"] == "ok"
    assert result["at"].endswith("+00:00")


def test_the_task_jobs_run_daily_and_are_registered_under_the_names_the_scheduler_uses() -> None:
    """A beat entry naming a task nothing registers fails at the first tick, on a schedule
    nobody is watching, so the pair is checked here."""
    for entry in ("spawn-recurring-tasks", "raise-evidence-renewals"):
        scheduled = celery_app.conf.beat_schedule[entry]
        assert scheduled["schedule"] == 24 * 3600.0
        assert scheduled["task"] in celery_app.tasks


def test_the_document_jobs_run_daily_and_are_registered_under_their_scheduled_names() -> None:
    """The review notices and the acknowledgement reminders each have one daily entry,
    and the task it names exists, so the first tick does not fail on a typo."""
    for entry, task in (
        ("sweep-document-reviews", "verity.workers.tasks.sweep_document_reviews"),
        ("remind-pending-acknowledgements", "verity.workers.tasks.remind_pending_acknowledgements"),
    ):
        scheduled = celery_app.conf.beat_schedule[entry]
        assert scheduled["task"] == task
        assert scheduled["schedule"] == 24 * 3600.0
        assert task in celery_app.tasks
