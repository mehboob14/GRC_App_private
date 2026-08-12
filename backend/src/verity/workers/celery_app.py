"""The Celery application.

Start a worker::

    uv run celery -A verity.workers.celery_app:celery_app worker --loglevel=info

Start the scheduler::

    uv run celery -A verity.workers.celery_app:celery_app beat --loglevel=info
"""

from __future__ import annotations

from celery import Celery
from celery.signals import setup_logging

from verity.core.config import get_settings
from verity.core.logging import configure_logging

settings = get_settings()

celery_app = Celery(
    "verity",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=("verity.workers.tasks",),
)

celery_app.conf.update(
    # JSON only. Pickle would let a compromised broker execute arbitrary code in a
    # worker that holds the database credentials and the encryption master key.
    task_serializer="json",
    result_serializer="json",
    accept_content=("json",),
    timezone="UTC",
    enable_utc=True,
    task_default_queue=settings.celery.task_default_queue,
    # Acknowledge after the task finishes, so a worker killed mid-task gives the task
    # back to the queue instead of losing it. Every scheduled job is documented as
    # idempotent (backend/CLAUDE.md), which is what makes redelivery safe.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # These jobs are long and uneven — a prefetching worker sits on tasks another idle
    # worker could have run.
    worker_prefetch_multiplier=1,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    result_expires=60 * 60 * 24,
    beat_schedule={
        "platform-heartbeat": {
            "task": "verity.workers.tasks.heartbeat",
            "schedule": 300.0,
        },
    },
)


@setup_logging.connect
def _configure_worker_logging(**_kwargs: object) -> None:
    """Give workers the same structured, redacted log pipeline as the API.

    Celery installs its own logging by default. Without this a worker's output escapes
    the redaction processor, which is the one place a connector credential is most
    likely to be passed to a log call.
    """
    configure_logging(get_settings())
