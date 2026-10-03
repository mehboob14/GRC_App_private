"""Tasks through the real app: severity, repeating tasks, the approval gate, evidence on a
task, and the renewal task raised for stale evidence.

The caller is a real signed-up admin whose session is validated against the database on
every request. The two scheduled jobs are the worker's own functions, run directly: what
matters is what they do to a workspace, not that Celery called them. Dates are relative to
today, because the schedule and staleness are functions of the clock.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text

from tests.support.audit import full_stream
from tests.support.iam import (
    INVITEE_PASSWORD,
    Workspace,
    invite_directly,
    signup_workspace,
    tenant_session_headers,
)
from verity.core.config import Settings
from verity.core.db import dispose_engine, session_scope
from verity.main import create_app
from verity.modules.iam.service import iam_auth_service
from verity.modules.links.service import link_service
from verity.modules.tasks.service import task_service
from verity.workers.tasks import _raise_evidence_renewals, _spawn_recurring_tasks

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
async def _clean_state(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> AsyncIterator[None]:
    await dispose_engine()
    yield
    await dispose_engine()


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
async def workspace() -> Workspace:
    return await signup_workspace(company="Tasks Ltd", email="founder@tasks.example")


def _client(app: FastAPI, headers: dict[str, str]) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test/api/v1", headers=headers
    )


@pytest.fixture
async def api(app: FastAPI, workspace: Workspace) -> AsyncIterator[httpx.AsyncClient]:
    async with _client(app, tenant_session_headers(workspace.membership_id)) as client:
        yield client


def _today() -> date:
    return datetime.now(UTC).date()


def _at(day: date) -> str:
    return f"{day.isoformat()}T00:00:00Z"


async def _create(api: httpx.AsyncClient, **fields: object) -> dict[str, Any]:
    response = await api.post("/tasks", json={"title": "Review the access list", **fields})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def _get(api: httpx.AsyncClient, task_id: str) -> dict[str, Any]:
    response = await api.get(f"/tasks/{task_id}")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def _move(
    api: httpx.AsyncClient, task_id: str, to_status: str, note: str | None = None
) -> httpx.Response:
    return await api.post(
        f"/tasks/{task_id}/transition", json={"to_status": to_status, "note": note}
    )


async def _all_tasks(api: httpx.AsyncClient) -> list[dict[str, Any]]:
    response = await api.get("/tasks", params={"page_size": 200})
    assert response.status_code == 200, response.text
    items: list[dict[str, Any]] = response.json()["items"]
    return items


# ---------------------------------------------------------------------------
# Severity
# ---------------------------------------------------------------------------


async def test_impact_and_urgency_resolve_a_severity_through_the_matrix(
    api: httpx.AsyncClient,
) -> None:
    created = await _create(api, task_kind="issue", impact="high", urgency="high")
    assert created["severity"] == "critical"
    assert created["impact"] == "high"
    assert created["severity_override"] is None

    # The register row carries it too, not only the detail.
    row = next(t for t in await _all_tasks(api) if t["id"] == created["id"])
    assert row["severity"] == "critical"

    # The workspace's own matrix wins over the built-in one.
    cell = await api.put(
        "/tasks/severity-matrix",
        json={
            "impact": "low",
            "urgency": "low",
            "severity": "high",
            "respond_hours": 1,
            "resolve_hours": 2,
        },
    )
    assert cell.status_code == 200, cell.text
    tuned = await _create(api, task_kind="issue", impact="low", urgency="low")
    assert tuned["severity"] == "high"


async def test_a_severity_against_the_matrix_is_an_override_that_says_why(
    api: httpx.AsyncClient,
) -> None:
    refused = await api.post(
        "/tasks",
        json={"title": "Soften", "impact": "high", "urgency": "high", "severity": "low"},
    )
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "invalid_input"
    assert "why" in refused.json()["error"]["message"]

    created = await _create(
        api,
        impact="high",
        urgency="high",
        severity="low",
        severity_reason="  Compensating control in place  ",
    )
    assert created["severity"] == "low"
    assert created["severity_override"] == "low"
    assert created["severity_override_reason"] == "Compensating control in place"

    # Choosing what the matrix says again clears the override, and the history says so.
    edited = await api.patch(
        f"/tasks/{created['id']}",
        json={"impact": "high", "urgency": "high", "severity": "critical"},
    )
    assert edited.status_code == 200, edited.text
    body = edited.json()
    assert body["severity"] == "critical"
    assert body["severity_override"] is None
    assert body["severity_override_reason"] is None
    assert {t["field_changed"] for t in body["transitions"]} >= {"created", "severity"}


async def test_a_severity_chosen_with_no_matrix_input_is_just_that_severity(
    api: httpx.AsyncClient,
) -> None:
    created = await _create(api, severity="medium")
    assert created["severity"] == "medium"
    assert created["severity_override"] is None

    # Editing something else leaves it alone; sending the severity block replaces it.
    untouched = await api.patch(f"/tasks/{created['id']}", json={"title": "Renamed"})
    assert untouched.json()["severity"] == "medium"
    cleared = await api.patch(f"/tasks/{created['id']}", json={"severity": None})
    assert cleared.json()["severity"] is None


@pytest.mark.parametrize(
    "fields",
    [{"severity": "extreme"}, {"impact": "huge"}, {"urgency": "now"}],
)
async def test_a_severity_outside_the_vocabulary_is_refused_with_copy(
    api: httpx.AsyncClient, fields: dict[str, str]
) -> None:
    response = await api.post("/tasks", json={"title": "Bad", **fields})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_input"
    assert "Pick" in response.json()["error"]["message"]


# ---------------------------------------------------------------------------
# Repeat rules
# ---------------------------------------------------------------------------


async def test_a_repeat_is_stored_as_a_restricted_rrule_and_read_back(
    api: httpx.AsyncClient,
) -> None:
    created = await _create(
        api,
        due_at="2030-01-31T00:00:00Z",
        repeat={"frequency": "monthly", "count": 6},
    )
    assert created["recurrence_rule"] == "FREQ=MONTHLY;INTERVAL=1;COUNT=6"
    assert created["repeat"] == {"frequency": "monthly", "interval": 1, "until": None, "count": 6}
    assert created["recurrence_summary"] == "Monthly, 6 times"
    # A task due on the 31st repeats on the last day of February.
    assert created["next_occurrence_at"] == "2030-02-28T00:00:00Z"
    assert created["recurrence_parent_id"] is None

    quarterly = await _create(
        api, due_at="2030-01-15T00:00:00Z", repeat={"frequency": "quarterly", "interval": 2}
    )
    assert quarterly["recurrence_rule"] == "FREQ=MONTHLY;INTERVAL=6"
    assert quarterly["repeat"]["frequency"] == "quarterly"
    assert quarterly["repeat"]["interval"] == 2
    assert quarterly["next_occurrence_at"] == "2030-07-15T00:00:00Z"


async def test_a_repeat_can_be_changed_and_cleared_on_edit(api: httpx.AsyncClient) -> None:
    task = await _create(
        api, due_at="2030-01-31T00:00:00Z", repeat={"frequency": "weekly", "interval": 2}
    )
    assert task["next_occurrence_at"] == "2030-02-14T00:00:00Z"

    changed = await api.patch(
        f"/tasks/{task['id']}", json={"repeat": {"frequency": "yearly", "until": "2035-01-01"}}
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["recurrence_rule"] == "FREQ=YEARLY;INTERVAL=1;UNTIL=20350101"
    assert changed.json()["next_occurrence_at"] == "2031-01-31T00:00:00Z"
    assert "repeat" in {t["field_changed"] for t in changed.json()["transitions"]}

    # The schedule follows the head's due date.
    moved = await api.patch(f"/tasks/{task['id']}", json={"due_at": "2030-03-31T00:00:00Z"})
    assert moved.json()["next_occurrence_at"] == "2031-03-31T00:00:00Z"

    cleared = await api.patch(f"/tasks/{task['id']}", json={"clear_repeat": True})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["recurrence_rule"] is None
    assert cleared.json()["repeat"] is None
    assert cleared.json()["next_occurrence_at"] is None
    assert cleared.json()["recurrence_summary"] is None


async def test_a_repeat_that_cannot_work_is_refused_with_copy(api: httpx.AsyncClient) -> None:
    both = await api.post(
        "/tasks",
        json={
            "title": "Both",
            "repeat": {"frequency": "daily", "until": "2031-01-01", "count": 3},
        },
    )
    assert both.status_code == 422
    assert "not both" in both.json()["error"]["message"]

    ends_first = await api.post(
        "/tasks",
        json={
            "title": "Ends before it starts",
            "due_at": "2030-06-01T00:00:00Z",
            "repeat": {"frequency": "daily", "until": "2030-06-01"},
        },
    )
    assert ends_first.status_code == 422
    assert "end date" in ends_first.json()["error"]["message"]

    unknown = await api.post("/tasks", json={"title": "x", "repeat": {"frequency": "hourly"}})
    assert unknown.status_code == 422


async def test_only_the_head_of_a_series_carries_the_repeat(api: httpx.AsyncClient) -> None:
    head = await _create(
        api,
        due_at=_at(_today() - timedelta(days=2)),
        repeat={"frequency": "daily"},
    )
    assert await _spawn_recurring_tasks() == {"tasks_created": 1}
    occurrence = next(t for t in await _all_tasks(api) if t["id"] != head["id"])

    refused = await api.patch(
        f"/tasks/{occurrence['id']}", json={"repeat": {"frequency": "weekly"}}
    )
    assert refused.status_code == 422
    assert "first task in the series" in refused.json()["error"]["message"]

    subtask = await api.post(f"/tasks/{head['id']}/subtasks", json={"title": "Part of it"})
    child_id = subtask.json()["subtasks"][0]["id"]
    on_subtask = await api.patch(f"/tasks/{child_id}", json={"repeat": {"frequency": "weekly"}})
    assert on_subtask.status_code == 422


# ---------------------------------------------------------------------------
# The spawn job
# ---------------------------------------------------------------------------


async def _daily_head(
    api: httpx.AsyncClient, workspace: Workspace, **fields: object
) -> dict[str, Any]:
    """A daily series whose first task fell due two days ago, so the next is due today."""
    return await _create(
        api,
        title="Quarterly access review",
        description="Walk the list and remove anyone who has left.",
        priority="high",
        category="security",
        owner_membership_id=str(workspace.membership_id),
        assignee_ids=[str(workspace.membership_id)],
        sla_level="P3 Standard",
        impact="high",
        urgency="medium",
        due_at=_at(_today() - timedelta(days=2)),
        repeat={"frequency": "daily"},
        **fields,
    )


async def test_the_spawn_job_raises_one_occurrence_and_a_second_run_raises_none(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    head = await _daily_head(api, workspace)
    # A rule on a task that was due two days ago does not raise the two days it missed.
    assert head["next_occurrence_at"] == _at(_today())

    assert await _spawn_recurring_tasks() == {"tasks_created": 1}
    assert await _spawn_recurring_tasks() == {"tasks_created": 0}

    tasks = await _all_tasks(api)
    assert len(tasks) == 2
    occurrence = await _get(api, next(t["id"] for t in tasks if t["id"] != head["id"]))

    # What describes the work carries over; the due date is the scheduled date.
    assert occurrence["recurrence_parent_id"] == head["id"]
    assert occurrence["recurrence_parent_code"] == head["code"]
    for same in ("title", "description", "priority", "category", "task_kind", "sla_level"):
        assert occurrence[same] == head[same], same
    assert occurrence["severity"] == head["severity"] == "high"
    assert occurrence["impact"] == "high"
    assert occurrence["due_at"] == _at(_today())
    assert occurrence["owner"]["membership_id"] == str(workspace.membership_id)
    assert [m["membership_id"] for m in occurrence["assignees"]] == [str(workspace.membership_id)]
    assert occurrence["sla_due_at"] is not None
    assert occurrence["source"] == "manual"

    # What happened to the head does not: it starts open with a history of its own, and
    # only the head carries the rule.
    assert occurrence["status"] == "open"
    assert occurrence["recurrence_rule"] is None
    assert occurrence["repeat"] is None
    assert occurrence["next_occurrence_at"] is None
    assert [t["field_changed"] for t in occurrence["transitions"]] == ["created"]
    assert (await _get(api, head["id"]))["next_occurrence_at"] == _at(_today() + timedelta(days=1))


async def test_the_spawn_job_audits_as_the_system_and_notifies_the_owner(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    head = await _daily_head(api, workspace)
    await _spawn_recurring_tasks()
    occurrence = next(t for t in await _all_tasks(api) if t["id"] != head["id"])

    stream = await full_stream(workspace.tenant_id)
    created = [
        e
        for e in stream
        if e.object_type == "task" and str(e.object_id) == occurrence["id"] and e.action == "create"
    ]
    assert len(created) == 1
    assert created[0].actor_type == "system"
    assert created[0].actor_id is None
    assert created[0].after is not None
    assert created[0].after["repeats"] == head["code"]
    moved = [
        e for e in stream if str(e.object_id) == head["id"] and e.after and "occurrence" in e.after
    ]
    assert len(moved) == 1
    assert moved[0].actor_type == "system"
    assert moved[0].after is not None
    assert moved[0].after["occurrence"] == occurrence["code"]

    inbox = (await api.get("/notifications")).json()["items"]
    notices = [n for n in inbox if n["kind"] == "recurrence"]
    assert [n["object_id"] for n in notices] == [occurrence["id"]]
    assert head["code"] in notices[0]["title"]


async def test_the_spawn_job_carries_the_heads_links_but_not_its_evidence(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    head = await _daily_head(api, workspace)
    control = (await api.get("/controls")).json()[0]
    evidence = await _evidence(api, "Last quarter's export")
    async with session_scope(workspace.tenant_id) as session:
        await link_service.create(
            session,
            tenant_id=workspace.tenant_id,
            from_type="task",
            from_id=uuid.UUID(head["id"]),
            to_type="control",
            to_id=uuid.UUID(control["id"]),
        )
    attached = await api.post(
        f"/tasks/{head['id']}/attachments", data={"evidence_ids": [evidence["id"]]}
    )
    assert attached.status_code == 200, attached.text

    await _spawn_recurring_tasks()
    occurrence = next(t for t in await _all_tasks(api) if t["id"] != head["id"])
    async with session_scope(workspace.tenant_id) as session:
        edges = await link_service.for_object(
            session,
            tenant_id=workspace.tenant_id,
            obj_type="task",
            obj_id=uuid.UUID(occurrence["id"]),
        )
    assert [(e.other_type, str(e.other_id)) for e in edges] == [("control", control["id"])]
    assert (await _get(api, occurrence["id"]))["attachments"] == []


async def test_a_head_that_was_not_moved_on_moves_on_without_raising_the_task_again(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    """A run that stopped between making the task and moving the head leaves the head
    pointing at a date that already has its task. The next run moves on and adds nothing."""
    head = await _daily_head(api, workspace)
    assert await _spawn_recurring_tasks() == {"tasks_created": 1}
    async with session_scope(workspace.tenant_id) as session:
        await session.execute(
            text("UPDATE tasks SET next_occurrence_at = :at WHERE id = :id"),
            {"at": datetime.combine(_today(), time.min, tzinfo=UTC), "id": uuid.UUID(head["id"])},
        )
    assert await _spawn_recurring_tasks() == {"tasks_created": 0}
    assert len(await _all_tasks(api)) == 2
    assert (await _get(api, head["id"]))["next_occurrence_at"] == _at(_today() + timedelta(days=1))


async def test_a_run_that_is_behind_catches_up_a_dozen_at_a_time(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    head = await _daily_head(api, workspace)
    far = datetime.now(UTC) + timedelta(days=30)
    async with session_scope(workspace.tenant_id) as session:
        first = await task_service.spawn_due_occurrences(
            session, tenant_id=workspace.tenant_id, now=far
        )
    assert first == 12
    after_first = await _get(api, head["id"])
    assert after_first["next_occurrence_at"] == _at(_today() + timedelta(days=12))

    async with session_scope(workspace.tenant_id) as session:
        second = await task_service.spawn_due_occurrences(
            session, tenant_id=workspace.tenant_id, now=far
        )
    async with session_scope(workspace.tenant_id) as session:
        third = await task_service.spawn_due_occurrences(
            session, tenant_id=workspace.tenant_id, now=far
        )
    # Today through thirty days on is 31 dates: twelve, twelve, then the seven left.
    assert (second, third) == (12, 7)
    dues = sorted(t["due_at"] for t in await _all_tasks(api) if t["id"] != head["id"])
    assert dues == [_at(_today() + timedelta(days=n)) for n in range(31)]


async def test_a_series_ends_when_its_rule_does(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    counted = await _create(
        api,
        title="Three in all",
        due_at=_at(_today() - timedelta(days=2)),
        repeat={"frequency": "daily", "count": 3},
    )
    ending = await _create(
        api,
        title="Until the day after tomorrow",
        due_at=_at(_today() - timedelta(days=2)),
        repeat={"frequency": "daily", "until": (_today() + timedelta(days=2)).isoformat()},
    )
    far = datetime.now(UTC) + timedelta(days=60)
    async with session_scope(workspace.tenant_id) as session:
        made = await task_service.spawn_due_occurrences(
            session, tenant_id=workspace.tenant_id, now=far
        )
    # The count counts the head, and the two days the rule skipped when it was set count
    # too: one more for the first series (today), and today through the end date for the
    # second (three).
    assert made == 4
    assert (await _get(api, counted["id"]))["next_occurrence_at"] is None
    assert (await _get(api, ending["id"]))["next_occurrence_at"] is None
    assert await _spawn_recurring_tasks() == {"tasks_created": 0}


async def test_cancelling_the_head_ends_the_series_and_reinstating_it_resumes_it(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    head = await _daily_head(api, workspace)
    cancelled = await _move(api, head["id"], "cancelled", "No longer needed")
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["next_occurrence_at"] is None
    assert cancelled.json()["recurrence_rule"] is not None
    assert await _spawn_recurring_tasks() == {"tasks_created": 0}

    reinstated = await _move(api, head["id"], "open")
    assert reinstated.status_code == 200, reinstated.text
    assert reinstated.json()["next_occurrence_at"] == _at(_today())
    assert await _spawn_recurring_tasks() == {"tasks_created": 1}


async def test_closing_the_head_does_not_end_the_series(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    head = await _daily_head(api, workspace)
    for to, note in (("in_progress", None), ("under_review", None), ("closed", "Done this time")):
        assert (await _move(api, head["id"], to, note)).status_code == 200
    assert await _spawn_recurring_tasks() == {"tasks_created": 1}


async def test_clearing_the_repeat_stops_the_next_task(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    head = await _daily_head(api, workspace)
    cleared = await api.patch(f"/tasks/{head['id']}", json={"clear_repeat": True})
    assert cleared.status_code == 200, cleared.text
    assert await _spawn_recurring_tasks() == {"tasks_created": 0}
    assert len(await _all_tasks(api)) == 1


# ---------------------------------------------------------------------------
# The approval gate
# ---------------------------------------------------------------------------


async def _decide(
    api: httpx.AsyncClient, task_id: str, decision: str, note: str | None = None
) -> httpx.Response:
    return await api.post(f"/tasks/{task_id}/approve", json={"decision": decision, "note": note})


async def test_closing_waits_for_the_approval_of_a_spawned_occurrence(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    head = await _daily_head(api, workspace, requires_approval=True)
    await _spawn_recurring_tasks()
    occurrence = next(t for t in await _all_tasks(api) if t["id"] != head["id"])
    task_id = occurrence["id"]

    # The occurrence starts with a fresh approval state of its own.
    fresh = await _get(api, task_id)
    assert fresh["approval_required"] is True
    assert fresh["approval_status"] == "pending"

    # An approval is a decision about work sent for review, not before.
    early = await _decide(api, task_id, "approved")
    assert early.status_code == 409
    assert "sent for review" in early.json()["error"]["message"]

    assert (await _move(api, task_id, "in_progress")).status_code == 200
    review = await _move(api, task_id, "under_review")
    assert review.status_code == 200, review.text
    assert review.json()["approval_status"] == "pending"
    # The close button is not offered, and pressing it anyway is refused with copy.
    assert "closed" not in review.json()["allowed_transitions"]
    blocked = await _move(api, task_id, "closed", "All done")
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "conflict"
    assert "needs approval" in blocked.json()["error"]["message"]

    rejected = await _decide(api, task_id, "rejected", "The export is missing")
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["approval_status"] == "rejected"
    assert "closed" not in rejected.json()["allowed_transitions"]
    assert (await _move(api, task_id, "closed", "Trying again")).status_code == 409

    # Sent back and sent for review again, it needs a fresh decision.
    assert (await _move(api, task_id, "in_progress")).status_code == 200
    again = await _move(api, task_id, "under_review")
    assert again.json()["approval_status"] == "pending"
    approved = await _decide(api, task_id, "approved", "Looks complete")
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["approval_status"] == "approved"
    assert body["approver"]["membership_id"] == str(workspace.membership_id)
    assert "closed" in body["allowed_transitions"]

    closed = await _move(api, task_id, "closed", "Signed off")
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "closed"
    # The decisions are in the history, with who and why.
    approvals = [t for t in closed.json()["transitions"] if t["field_changed"] == "approval"]
    assert [(t["new_value"], t["note"]) for t in approvals] == [
        ("approved", "Looks complete"),
        ("rejected", "The export is missing"),
    ]


async def test_a_task_that_needs_no_approval_closes_without_one(api: httpx.AsyncClient) -> None:
    task = await _create(api)
    assert task["approval_required"] is False
    assert task["approval_status"] == "not_required"
    for to, note in (("in_progress", None), ("under_review", None), ("closed", "Done")):
        assert (await _move(api, task["id"], to, note)).status_code == 200
    nothing = await _decide(api, task["id"], "approved")
    assert nothing.status_code == 409


async def test_approval_can_be_required_and_dropped_on_edit(api: httpx.AsyncClient) -> None:
    task = await _create(api)
    on = await api.patch(f"/tasks/{task['id']}", json={"requires_approval": True})
    assert on.status_code == 200, on.text
    assert on.json()["approval_required"] is True
    assert on.json()["approval_status"] == "pending"
    for to in ("in_progress", "under_review"):
        assert (await _move(api, task["id"], to)).status_code == 200
    assert (await _move(api, task["id"], "closed", "Done")).status_code == 409

    off = await api.patch(f"/tasks/{task['id']}", json={"requires_approval": False})
    assert off.json()["approval_status"] == "not_required"
    assert "closed" in off.json()["allowed_transitions"]
    assert (await _move(api, task["id"], "closed", "Done")).status_code == 200


# ---------------------------------------------------------------------------
# Evidence on a task
# ---------------------------------------------------------------------------

CSV = b"user,role\nada,admin\ngrace,auditor\n"


async def _evidence(
    api: httpx.AsyncClient, title: str, *, controls: list[str] | None = None, **fields: object
) -> dict[str, Any]:
    today = _today()
    body = {
        "title": title,
        "link_url": "https://example.test/export",
        "evidence_type": "log_export",
        "collected_at": (today - timedelta(days=5)).isoformat(),
        "control_ids": controls or [],
        **fields,
    }
    response = await api.post("/evidence/link", json=body)
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


async def test_a_transition_carries_an_existing_item_and_an_uploaded_file(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    control = (await api.get("/controls")).json()[0]
    existing = await _evidence(api, "Access review export")
    task = await _create(api, title="Review access")
    async with session_scope(workspace.tenant_id) as session:
        await link_service.create(
            session,
            tenant_id=workspace.tenant_id,
            from_type="task",
            from_id=uuid.UUID(task["id"]),
            to_type="control",
            to_id=uuid.UUID(control["id"]),
        )

    moved = await api.post(
        f"/tasks/{task['id']}/transition/files",
        data={"to_status": "in_progress", "note": "Started", "evidence_ids": [existing["id"]]},
        files=[("files", ("access-review_q3.csv", CSV, "text/csv"))],
    )
    assert moved.status_code == 200, moved.text
    body = moved.json()
    assert body["status"] == "in_progress"
    assert body["attachment_count"] == 2
    by_title = {a["title"]: a for a in body["attachments"]}
    assert set(by_title) == {"Access review export", "access review q3"}

    # The file became an evidence item: stored, hashed, and mapped to the task's controls.
    uploaded = by_title["access review q3"]
    assert uploaded["kind"] == "file"
    assert uploaded["filename"] == "access-review_q3.csv"
    assert uploaded["content_type"] == "text/plain"
    assert uploaded["size_bytes"] == len(CSV)
    assert uploaded["sha256"] == hashlib.sha256(CSV).hexdigest()
    assert uploaded["evidence_type"] == "other"
    evidence = (await api.get(f"/evidence/{uploaded['id']}")).json()
    assert evidence["control_ids"] == [control["id"]]
    assert evidence["owner_membership_id"] == str(workspace.membership_id)

    # Both say who attached them and name the status change they came with.
    status_row = next(t for t in body["transitions"] if t["field_changed"] == "status")
    for attachment in body["attachments"]:
        assert attachment["attached_by"] == "Founding Admin"
        assert attachment["transition_id"] == status_row["id"]
    attach_events = [t for t in body["transitions"] if t["field_changed"] == "attachment"]
    assert {t["new_value"] for t in attach_events} == {a["id"] for a in body["attachments"]}
    assert {t["old_value"] for t in attach_events} == {status_row["id"]}

    # The edge reads from the evidence side too, so the library shows the task.
    links = (await api.get(f"/evidence/{existing['id']}/links")).json()
    assert [(link["target_type"], link["code"]) for link in links] == [("task", task["code"])]


async def test_an_attached_file_downloads_with_its_bytes_and_only_from_its_task(
    api: httpx.AsyncClient,
) -> None:
    task = await _create(api)
    other = await _create(api, title="Another task")
    link = await _evidence(api, "A link, not a file")
    attached = await api.post(
        f"/tasks/{task['id']}/attachments",
        data={"evidence_ids": [link["id"]]},
        files=[("files", ("people.csv", CSV, "text/csv"))],
    )
    assert attached.status_code == 200, attached.text
    file_item = next(a for a in attached.json()["attachments"] if a["kind"] == "file")
    link_item = next(a for a in attached.json()["attachments"] if a["kind"] == "link")
    # Attached on its own, not with a status change.
    assert file_item["transition_id"] is None

    download = await api.get(f"/tasks/{task['id']}/attachments/{file_item['id']}/download")
    assert download.status_code == 200
    assert download.content == CSV
    assert download.headers["content-disposition"] == 'attachment; filename="people.csv"'

    # A link has no bytes; a task that does not carry the item does not serve it.
    assert (
        await api.get(f"/tasks/{task['id']}/attachments/{link_item['id']}/download")
    ).status_code == 422
    assert (
        await api.get(f"/tasks/{other['id']}/attachments/{file_item['id']}/download")
    ).status_code == 404


async def test_attaching_again_changes_nothing_and_adds_no_history(
    api: httpx.AsyncClient,
) -> None:
    task = await _create(api)
    item = await _evidence(api, "Once is enough")
    first = await api.post(f"/tasks/{task['id']}/attachments", data={"evidence_ids": [item["id"]]})
    again = await api.post(f"/tasks/{task['id']}/attachments", data={"evidence_ids": [item["id"]]})
    assert again.status_code == 200, again.text
    assert len(again.json()["attachments"]) == 1
    assert len(again.json()["transitions"]) == len(first.json()["transitions"])


async def test_a_refused_file_stops_the_transition_and_attaches_nothing(
    api: httpx.AsyncClient,
) -> None:
    task = await _create(api)
    item = await _evidence(api, "Fine on its own")
    refused = await api.post(
        f"/tasks/{task['id']}/transition/files",
        data={"to_status": "in_progress", "evidence_ids": [item["id"]]},
        files=[("files", ("page.html", b"<html><script>alert(1)</script></html>", "text/html"))],
    )
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "unsupported_file_type"
    after = await _get(api, task["id"])
    assert after["status"] == "open"
    assert after["attachments"] == []
    assert [t["field_changed"] for t in after["transitions"]] == ["created"]


async def test_attaching_needs_something_to_attach_and_a_real_item(
    api: httpx.AsyncClient,
) -> None:
    task = await _create(api)
    nothing = await api.post(f"/tasks/{task['id']}/attachments")
    assert nothing.status_code == 422
    assert "Choose" in nothing.json()["error"]["message"]
    missing = await api.post(
        f"/tasks/{task['id']}/attachments", data={"evidence_ids": [str(uuid.uuid4())]}
    )
    assert missing.status_code == 404
    too_many = await api.post(
        f"/tasks/{task['id']}/attachments",
        files=[("files", (f"f{n}.csv", CSV, "text/csv")) for n in range(6)],
    )
    assert too_many.status_code == 422
    assert "up to 5 files" in too_many.json()["error"]["message"]


async def test_evidence_on_a_task_needs_the_evidence_keys(
    api: httpx.AsyncClient, workspace: Workspace, app: FastAPI
) -> None:
    task = await _create(api)
    item = await _evidence(api, "Visible to the library only")
    await api.post(f"/tasks/{task['id']}/attachments", data={"evidence_ids": [item["id"]]})

    # A member who works tasks but has no access to the evidence library.
    invited = await invite_directly(
        workspace,
        email="worker@tasks.example",
        full_name="Task Worker",
        role_name="Chief Executive Officer",
    )
    await iam_auth_service.accept_invitation(
        token=invited.invite_token, full_name="Task Worker", password=INVITEE_PASSWORD
    )
    role = await api.post(
        "/roles",
        json={
            "name": "Task worker",
            "permission_keys": ["tenant:read", "tasks:read", "tasks:manage"],
        },
    )
    assert role.status_code == 201, role.text
    assignment = await api.post(
        f"/roles/{role.json()['id']}/assignments",
        json={"assignee_type": "membership", "assignee_id": str(invited.member.membership_id)},
    )
    assert assignment.status_code == 201, assignment.text

    async with _client(app, tenant_session_headers(invited.member.membership_id)) as worker:
        detail = await worker.get(f"/tasks/{task['id']}")
        assert detail.status_code == 200
        # The task and the number, but not what the evidence library holds.
        assert detail.json()["attachments"] == []
        assert detail.json()["attachment_count"] == 1
        download = await worker.get(f"/tasks/{task['id']}/attachments/{item['id']}/download")
        assert download.status_code == 403
        picked = await worker.post(
            f"/tasks/{task['id']}/attachments", data={"evidence_ids": [item["id"]]}
        )
        assert picked.status_code == 403
        picked_on_move = await worker.post(
            f"/tasks/{task['id']}/transition",
            json={"to_status": "in_progress", "evidence_ids": [item["id"]]},
        )
        assert picked_on_move.status_code == 403
        uploaded = await worker.post(
            f"/tasks/{task['id']}/attachments", files=[("files", ("a.csv", CSV, "text/csv"))]
        )
        assert uploaded.status_code == 403
        # Everything that is the task's own still works.
        plain = await worker.post(
            f"/tasks/{task['id']}/transition", json={"to_status": "in_progress"}
        )
        assert plain.status_code == 200


# ---------------------------------------------------------------------------
# The renewal task
# ---------------------------------------------------------------------------


async def _stale(
    api: httpx.AsyncClient,
    title: str,
    *,
    controls: list[str] | None = None,
    lapsed_days_ago: int = 10,
    **fields: object,
) -> dict[str, Any]:
    """Evidence collected long ago whose validity ran out ``lapsed_days_ago`` days ago."""
    today = _today()
    return await _evidence(
        api,
        title,
        controls=controls,
        collected_at=(today - timedelta(days=120)).isoformat(),
        renewal_date=(today - timedelta(days=lapsed_days_ago)).isoformat(),
        **fields,
    )


async def _renewal_tasks(api: httpx.AsyncClient) -> list[dict[str, Any]]:
    response = await api.get("/tasks", params={"source_type": "evidence", "page_size": 200})
    assert response.status_code == 200, response.text
    items: list[dict[str, Any]] = response.json()["items"]
    return items


async def test_stale_evidence_gets_one_renewal_task_and_a_second_run_adds_none(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    controls = (await api.get("/controls")).json()[:2]
    owned = await api.patch(
        f"/controls/{controls[0]['id']}", json={"owner_membership_id": str(workspace.membership_id)}
    )
    assert owned.status_code == 200, owned.text
    stale = await _stale(api, "Access review export", controls=[c["id"] for c in controls])
    await _evidence(api, "Still current", controls=[controls[0]["id"]])

    assert await _raise_evidence_renewals() == {"tasks_created": 1}
    assert await _raise_evidence_renewals() == {"tasks_created": 0}

    (task,) = await _renewal_tasks(api)
    detail = await _get(api, task["id"])
    assert detail["title"] == "Renew evidence: Access review export"
    assert detail["task_kind"] == "task"
    assert detail["priority"] == "medium"
    assert detail["category"] == "regulatory"
    assert detail["source"] == "evidence"
    assert detail["due_at"] == _at(_today() + timedelta(days=7))
    assert detail["status"] == "open"
    # The evidence has no owner of its own, so the first of its controls that has one.
    assert detail["owner"]["membership_id"] == str(workspace.membership_id)
    assert [m["membership_id"] for m in detail["assignees"]] == [str(workspace.membership_id)]
    assert all(c["code"] in detail["description"] for c in controls)

    # The stale item is on the task, attached by the system.
    (attachment,) = detail["attachments"]
    assert attachment["id"] == stale["id"]
    assert attachment["freshness"] == "stale"
    assert attachment["attached_by"] == "System"
    # The evidence library shows the task, and the task is linked to the controls.
    links = (await api.get(f"/evidence/{stale['id']}/links")).json()
    assert [link["code"] for link in links] == [detail["code"]]
    async with session_scope(workspace.tenant_id) as session:
        edges = await link_service.for_object(
            session,
            tenant_id=workspace.tenant_id,
            obj_type="task",
            obj_id=uuid.UUID(detail["id"]),
        )
    assert {str(e.other_id) for e in edges if e.other_type == "control"} == {
        c["id"] for c in controls
    }

    # The owner is told, and the audit row names the system, not a person.
    inbox = (await api.get("/notifications")).json()["items"]
    assert [n["object_id"] for n in inbox if n["kind"] == "assigned"] == [detail["id"]]
    stream = await full_stream(workspace.tenant_id)
    created = [
        e
        for e in stream
        if e.object_type == "task" and str(e.object_id) == detail["id"] and e.action == "create"
    ]
    assert [(e.actor_type, e.actor_id) for e in created] == [("system", None)]
    assert created[0].after is not None
    assert created[0].after["evidence_id"] == stale["id"]


async def test_the_evidence_owner_is_the_renewal_owner_before_any_control_owner(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    owner = str(workspace.membership_id)
    await _stale(api, "Owned directly", owner_membership_id=owner)
    await _stale(api, "Nobody owns this")
    assert await _raise_evidence_renewals() == {"tasks_created": 2}
    by_title = {t["title"]: t for t in await _renewal_tasks(api)}
    assert by_title["Renew evidence: Owned directly"]["owner"]["membership_id"] == owner
    assert by_title["Renew evidence: Nobody owns this"]["owner"] is None


async def test_a_closed_renewal_is_not_reopened_but_a_later_lapse_raises_a_new_one(
    api: httpx.AsyncClient,
) -> None:
    item = await _stale(api, "Quarterly scan")
    assert await _raise_evidence_renewals() == {"tasks_created": 1}
    (first,) = await _renewal_tasks(api)

    # Closing the task without renewing the evidence leaves the same lapse: no second task.
    for to, note in (("in_progress", None), ("under_review", None), ("closed", "Will renew later")):
        assert (await _move(api, first["id"], to, note)).status_code == 200
    assert await _raise_evidence_renewals() == {"tasks_created": 0}

    # Renewing the evidence ends the lapse. Letting it run out again starts another.
    today = _today()
    renewed = await api.patch(
        f"/evidence/{item['id']}", json={"renewal_date": (today + timedelta(days=90)).isoformat()}
    )
    assert renewed.status_code == 200, renewed.text
    assert await _raise_evidence_renewals() == {"tasks_created": 0}
    lapsed = await api.patch(
        f"/evidence/{item['id']}", json={"renewal_date": (today - timedelta(days=1)).isoformat()}
    )
    assert lapsed.status_code == 200, lapsed.text
    assert await _raise_evidence_renewals() == {"tasks_created": 1}

    tasks = await _renewal_tasks(api)
    assert {t["id"] for t in tasks} > {first["id"]}
    assert sorted(t["status"] for t in tasks) == ["closed", "open"]


async def test_an_item_with_an_open_renewal_task_is_left_alone_whatever_its_date(
    api: httpx.AsyncClient,
) -> None:
    item = await _stale(api, "Shifting date")
    assert await _raise_evidence_renewals() == {"tasks_created": 1}
    moved = await api.patch(
        f"/evidence/{item['id']}",
        json={"renewal_date": (_today() - timedelta(days=3)).isoformat()},
    )
    assert moved.status_code == 200, moved.text
    assert await _raise_evidence_renewals() == {"tasks_created": 0}
    assert len(await _renewal_tasks(api)) == 1


async def test_the_renewal_task_follows_the_automation(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    await _stale(api, "Switchable")

    off = await api.patch("/tasks/automations/evidence_stale", json={"enabled": False})
    assert off.status_code == 200, off.text
    assert await _raise_evidence_renewals() == {"tasks_created": 0}
    assert await _renewal_tasks(api) == []

    tuned = await api.patch(
        "/tasks/automations/evidence_stale",
        json={
            "enabled": True,
            "owner_rule": "unassigned",
            "priority": "high",
            "due_in_days": 3,
            "creates": "issue",
        },
    )
    assert tuned.status_code == 200, tuned.text
    assert await _raise_evidence_renewals() == {"tasks_created": 1}
    (task,) = await _renewal_tasks(api)
    detail = await _get(api, task["id"])
    assert detail["task_kind"] == "issue"
    assert detail["priority"] == "high"
    assert detail["due_at"] == _at(_today() + timedelta(days=3))
    assert detail["owner"] is None
    assert detail["assignees"] == []
    # An issue raised from an event gets its corrective action, as every other source does.
    assert len(detail["capa_actions"]) == 1
    inbox = (await api.get("/notifications")).json()["items"]
    assert [n for n in inbox if n["kind"] == "assigned"] == []


async def test_nothing_is_raised_when_no_evidence_has_lapsed(api: httpx.AsyncClient) -> None:
    await _evidence(api, "Fresh")
    assert await _raise_evidence_renewals() == {"tasks_created": 0}
    assert await _renewal_tasks(api) == []


async def test_task_codes_keep_counting_past_four_digits(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    """The code is the highest number plus one, compared as a number: as text,
    TSK-9999 sorts after TSK-10000 and the next code handed out would already be taken."""
    first = await _create(api, title="one")
    second = await _create(api, title="two")
    async with session_scope(workspace.tenant_id) as session:
        for task, code in ((first, "TSK-9999"), (second, "TSK-10000")):
            await session.execute(
                text("UPDATE tasks SET code = :code WHERE id = :id"),
                {"code": code, "id": uuid.UUID(task["id"])},
            )
    third = await _create(api, title="three")
    assert third["code"] == "TSK-10001"
