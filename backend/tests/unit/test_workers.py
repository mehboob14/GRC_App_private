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
