"""Tenant isolation for the trace.

The trace reads the links table and four join tables, then labels whatever it finds
through the owning modules' services. Links hold bare ids, so the wall on that path is
the read side, and these are the properties it has to keep:

1. A record of the other workspace is absent by id: tracing it raises ``NotFound``.
2. A link in this workspace's own stream that points at a record of the other (nothing
   but the read side stops one existing) shows nothing: the other record is never
   labelled, so no title crosses the wall, and the trace is as empty as if the link
   were not there.
3. Both of the above hold from either side.

Every record is seeded through the real services, and the stray links through the links
service, as the application role with RLS on.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest

from tests.support.iam import Workspace, signup_workspace
from verity.core.db import dispose_engine, session_scope
from verity.core.errors import NotFound
from verity.modules.assets.service import AssetInput, asset_service
from verity.modules.audit.service import Membership
from verity.modules.compliance.control_service import control_service
from verity.modules.linkage.service import READ_PERMISSION, linkage_service
from verity.modules.links.service import link_service

pytestmark = [pytest.mark.isolation, pytest.mark.integration]

EVERYTHING = frozenset(READ_PERMISSION.values())


@pytest.fixture(autouse=True)
async def _fresh_state(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> AsyncIterator[None]:
    await dispose_engine()
    yield
    await dispose_engine()


@dataclass(frozen=True, slots=True)
class Seeded:
    workspace: Workspace
    asset_id: uuid.UUID
    control_id: uuid.UUID


async def _seed(workspace: Workspace, name: str) -> Seeded:
    async with session_scope(workspace.tenant_id) as session:
        asset = await asset_service.create_asset(
            session,
            tenant_id=workspace.tenant_id,
            actor=Membership(workspace.membership_id),
            data=AssetInput(name=name),
        )
        controls = await control_service.list_controls(session, tenant_id=workspace.tenant_id)
        assert controls, "signup should have adopted the control library"
    return Seeded(workspace, asset.id, controls[0].id)


@pytest.fixture
async def two() -> tuple[Seeded, Seeded]:
    a = await _seed(
        await signup_workspace(company="Alpha Ltd", email="a@alpha.example"), "Alpha API"
    )
    b = await _seed(await signup_workspace(company="Beta Ltd", email="b@beta.example"), "Beta API")
    return a, b


async def _trace(mine: Seeded, kind: str, record_id: uuid.UUID) -> list[str]:
    async with session_scope(mine.workspace.tenant_id) as session:
        result = await linkage_service.trace(
            session,
            tenant_id=mine.workspace.tenant_id,
            record_type=kind,
            record_id=record_id,
            depth=4,
            permissions=EVERYTHING,
        )
    return [node.key for node in result.nodes]


async def test_a_record_of_the_other_workspace_cannot_be_traced(
    two: tuple[Seeded, Seeded],
) -> None:
    a, b = two
    for mine, theirs in ((a, b), (b, a)):
        for kind, record_id in (("asset", theirs.asset_id), ("control", theirs.control_id)):
            with pytest.raises(NotFound):
                await _trace(mine, kind, record_id)
        # And each still traces its own records.
        assert await _trace(mine, "asset", mine.asset_id) == []


async def test_a_link_pointing_across_the_wall_shows_nothing(
    two: tuple[Seeded, Seeded],
) -> None:
    a, b = two
    # Each workspace's own stream gets links to the other's asset and control.
    for mine, theirs in ((a, b), (b, a)):
        async with session_scope(mine.workspace.tenant_id) as session:
            for to_type, to_id in (("asset", theirs.asset_id), ("control", theirs.control_id)):
                await link_service.create(
                    session,
                    tenant_id=mine.workspace.tenant_id,
                    from_type="asset",
                    from_id=mine.asset_id,
                    to_type=to_type,
                    to_id=to_id,
                )
    for mine, theirs in ((a, b), (b, a)):
        # The stray edges are really there, and only this workspace's own are visible ...
        async with session_scope(mine.workspace.tenant_id) as session:
            edges = await link_service.for_object(
                session,
                tenant_id=mine.workspace.tenant_id,
                obj_type="asset",
                obj_id=mine.asset_id,
            )
        assert {(e.other_type, e.other_id) for e in edges} == {
            ("asset", theirs.asset_id),
            ("control", theirs.control_id),
        }
        # ... and the trace labels neither: nothing of the other workspace comes back.
        assert await _trace(mine, "asset", mine.asset_id) == []
