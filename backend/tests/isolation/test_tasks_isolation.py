"""Tenant isolation for tasks: their attachments and the renewal tasks raised for evidence.

Tasks reach across modules now, to carry evidence and to be raised for it, so the wall has
more ways to be missing than a table without a policy:

1. An unfiltered read from tenant A's session returns only A's tasks and A's edges: the
   policy bounds the row set, not the query.
2. A B task is *absent* by id for every path that takes one: read, move, attach to,
   download from. 404-not-403 at the API is this database fact.
3. Evidence is checked by the module that owns it: a task cannot attach B's evidence, and a
   link that points at it anyway shows nothing, because evidence is read under the caller's
   own tenant.
4. The scheduled jobs bind one tenant per unit of work, so a renewal task is raised in the
   workspace that owns the stale evidence and only there.
5. A write carrying B's ``tenant_id`` from an A-bound session is refused by the policy's
   ``WITH CHECK``.

Everything is seeded through the real services, never by writing a table.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.iam import Workspace, signup_workspace
from verity.core.db import dispose_engine, session_scope
from verity.core.errors import NotFound
from verity.db.base import Base
from verity.modules.audit.service import Membership
from verity.modules.evidence.service import evidence_service
from verity.modules.links.models import Link
from verity.modules.links.service import link_service
from verity.modules.tasks.models import Task, TaskTransition
from verity.modules.tasks.service import TaskFilters, Upload, task_service
from verity.shared.ids import uuid7
from verity.workers.tasks import _raise_evidence_renewals

pytestmark = [pytest.mark.isolation, pytest.mark.integration]

CSV = b"user,role\nada,admin\n"


@pytest.fixture(autouse=True)
async def _fresh_state(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> AsyncIterator[None]:
    """``session_scope`` runs on the cached process engine; keep it per-test."""
    await dispose_engine()
    yield
    await dispose_engine()


@dataclass(frozen=True, slots=True)
class Seeded:
    workspace: Workspace
    task_id: uuid.UUID
    file_evidence_id: uuid.UUID
    stale_evidence_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class TwoTenants:
    a: Seeded
    b: Seeded


async def _populate(workspace: Workspace, label: str) -> Seeded:
    """A task carrying an uploaded file, and a stale evidence item awaiting its renewal
    task. Both tenants use the same titles and file name, so a name can never be what
    keeps them apart."""
    actor = Membership(workspace.membership_id)
    today = datetime.now(UTC).date()
    async with session_scope(workspace.tenant_id) as session:
        task = await task_service.create_task(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            task_kind="task",
            title="Quarterly access review",
        )
        attached = await task_service.attach(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            task_id=task.id,
            uploads=[Upload(filename="proof.csv", data=CSV)],
        )
        stale = await evidence_service.add_link(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            title="Access review export",
            link_url=f"https://example.test/{label}",
            evidence_type="log_export",
            collected_at=today - timedelta(days=120),
            renewal_date=today - timedelta(days=10),
        )
    return Seeded(
        workspace=workspace,
        task_id=task.id,
        file_evidence_id=attached.attachments[0].id,
        stale_evidence_id=stale.id,
    )


@pytest.fixture
async def tenants() -> TwoTenants:
    a = await signup_workspace(company="Alpha Compliance", email="founder@alpha.example")
    b = await signup_workspace(company="Bravo Assurance", email="founder@bravo.example")
    return TwoTenants(a=await _populate(a, "a"), b=await _populate(b, "b"))


async def test_an_a_session_lists_only_a_tasks_and_a_edges(tenants: TwoTenants) -> None:
    """No WHERE clause anywhere: the policy, not the query, bounds every row set."""
    async with session_scope(tenants.a.workspace.tenant_id) as session:
        for model in (Task, TaskTransition, Link):
            owners = list((await session.execute(select(model.tenant_id))).scalars())
            assert owners, f"{model.__name__}: the seed should have written rows"
            assert set(owners) == {tenants.a.workspace.tenant_id}, model.__name__
        items, total = await task_service.list_tasks(
            session, tenant_id=tenants.a.workspace.tenant_id, filters=TaskFilters()
        )
    assert total == 1
    assert [t.id for t in items] == [tenants.a.task_id]
    assert items[0].attachment_count == 1


async def test_a_b_task_reads_as_absent_by_id_on_every_path(tenants: TwoTenants) -> None:
    a, b = tenants.a, tenants.b
    actor = Membership(a.workspace.membership_id)
    paths: dict[str, Callable[[AsyncSession], Awaitable[object]]] = {
        "read": lambda s: task_service.get_task(
            s, tenant_id=a.workspace.tenant_id, task_id=b.task_id
        ),
        "move": lambda s: task_service.transition(
            s,
            tenant_id=a.workspace.tenant_id,
            actor=actor,
            task_id=b.task_id,
            to_status="in_progress",
        ),
        "attach": lambda s: task_service.attach(
            s,
            tenant_id=a.workspace.tenant_id,
            actor=actor,
            task_id=b.task_id,
            uploads=[Upload(filename="x.csv", data=CSV)],
        ),
        "download": lambda s: task_service.download_attachment(
            s,
            tenant_id=a.workspace.tenant_id,
            task_id=b.task_id,
            evidence_id=b.file_evidence_id,
        ),
    }
    for name, call in paths.items():
        async with session_scope(a.workspace.tenant_id) as session:
            with pytest.raises(NotFound):
                await call(session)
            assert await session.get(Task, b.task_id) is None, name


async def test_a_task_cannot_attach_another_workspaces_evidence(tenants: TwoTenants) -> None:
    a, b = tenants.a, tenants.b
    async with session_scope(a.workspace.tenant_id) as session:
        with pytest.raises(NotFound):
            await task_service.attach(
                session,
                tenant_id=a.workspace.tenant_id,
                actor=Membership(a.workspace.membership_id),
                task_id=a.task_id,
                evidence_ids=[b.file_evidence_id],
            )
    async with session_scope(a.workspace.tenant_id) as session:
        with pytest.raises(NotFound):
            await evidence_service.link_to_task(
                session,
                tenant_id=a.workspace.tenant_id,
                actor=Membership(a.workspace.membership_id),
                evidence_id=b.file_evidence_id,
                task_id=a.task_id,
            )


async def test_an_edge_that_points_at_b_evidence_shows_nothing_on_an_a_task(
    tenants: TwoTenants,
) -> None:
    """The links table has no foreign key to evidence, so an A edge can name a B id.
    Evidence is read under A's own tenant, so it resolves to nothing: no title, no hash,
    and no download."""
    a, b = tenants.a, tenants.b
    async with session_scope(a.workspace.tenant_id) as session:
        await link_service.create(
            session,
            tenant_id=a.workspace.tenant_id,
            from_type="evidence",
            from_id=b.file_evidence_id,
            to_type="task",
            to_id=a.task_id,
        )
    async with session_scope(a.workspace.tenant_id) as session:
        detail = await task_service.get_task(
            session, tenant_id=a.workspace.tenant_id, task_id=a.task_id
        )
        assert [x.id for x in detail.attachments] == [a.file_evidence_id]
        with pytest.raises(NotFound):
            await task_service.download_attachment(
                session,
                tenant_id=a.workspace.tenant_id,
                task_id=a.task_id,
                evidence_id=b.file_evidence_id,
            )


async def test_the_renewal_job_raises_each_workspaces_task_in_that_workspace(
    tenants: TwoTenants,
) -> None:
    assert await _raise_evidence_renewals() == {"tasks_created": 2}
    assert await _raise_evidence_renewals() == {"tasks_created": 0}

    for seeded, other in ((tenants.a, tenants.b), (tenants.b, tenants.a)):
        async with session_scope(seeded.workspace.tenant_id) as session:
            items, _total = await task_service.list_tasks(
                session,
                tenant_id=seeded.workspace.tenant_id,
                filters=TaskFilters(source_type="evidence"),
            )
            (renewal,) = items
            detail = await task_service.get_task(
                session, tenant_id=seeded.workspace.tenant_id, task_id=renewal.id
            )
        assert [a.id for a in detail.attachments] == [seeded.stale_evidence_id]
        assert other.stale_evidence_id not in {a.id for a in detail.attachments}

        # And the other workspace cannot read it by id.
        async with session_scope(other.workspace.tenant_id) as session:
            with pytest.raises(NotFound):
                await task_service.get_task(
                    session, tenant_id=other.workspace.tenant_id, task_id=renewal.id
                )


async def test_an_unbound_session_sees_no_tasks(tenants: TwoTenants) -> None:
    """Fail closed: no tenant bound, not provider plane: zero rows, no error."""
    async with session_scope(None) as session:
        for model in (Task, TaskTransition, Link):
            assert list((await session.execute(select(model.id))).scalars()) == [], model.__name__


async def test_a_write_carrying_tenant_b_is_refused_by_with_check(tenants: TwoTenants) -> None:
    forgeries: tuple[Base, ...] = (
        Task(
            id=uuid7(),
            tenant_id=tenants.b.workspace.tenant_id,
            code="TSK-0999",
            title="Forged",
        ),
        TaskTransition(
            id=uuid7(),
            tenant_id=tenants.b.workspace.tenant_id,
            task_id=tenants.a.task_id,
            field_changed="status",
            occurred_at=datetime.now(UTC),
        ),
        Link(
            id=uuid7(),
            tenant_id=tenants.b.workspace.tenant_id,
            from_type="evidence",
            from_id=tenants.a.file_evidence_id,
            to_type="task",
            to_id=tenants.a.task_id,
        ),
    )

    async def forge(instance: Base) -> None:
        async with session_scope(tenants.a.workspace.tenant_id) as session:
            session.add(instance)
            await session.flush()

    for forged in forgeries:
        with pytest.raises(DBAPIError, match="row-level security"):
            await forge(forged)
