"""Type and Sub-type on the control library (spec 1.1), through the real app.

Type is the category and Sub-type the area inside it. The library ships with both on
every control, adoption copies them, the register filters and exports by them and the
form suggests from them. The backfill that gives an earlier workspace its Sub-types
runs here on a transaction that is rolled back, so the shared database is left as found.
"""

from __future__ import annotations

import csv
import importlib.util
import io
from collections import defaultdict
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from openpyxl import load_workbook
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

import verity
from tests.support.iam import Workspace, signup_workspace
from verity.core.config import Settings
from verity.main import create_app

pytestmark = [pytest.mark.integration]

_MIGRATIONS = Path(verity.__file__).parent / "db" / "migrations" / "versions"


@pytest.fixture
async def workspaces(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> tuple[Workspace, Workspace]:
    home = await signup_workspace(company="Subtype Ltd", email="subtype@example.test")
    other = await signup_workspace(company="Elsewhere Ltd", email="elsewhere@example.test")
    return home, other


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


def _client(app: FastAPI, workspace: Workspace) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test/api/v1",
        headers={"Authorization": f"Bearer {workspace.session_token}"},
    )


async def _templates(api: httpx.AsyncClient) -> dict[str, dict[str, Any]]:
    page = (await api.get("/control-templates", params={"limit": 200})).json()
    return {template["id"]: template for template in page["items"]}


def _migration() -> ModuleType:
    path = next(_MIGRATIONS.glob("*_control_sub_category_backfill.py"))
    spec = importlib.util.spec_from_file_location("control_sub_category_backfill", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def test_adoption_copies_the_type_and_sub_type_of_every_template(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, _ = workspaces
    async with _client(app, home) as api:
        templates = await _templates(api)
        controls = (await api.get("/controls")).json()

    assert len(controls) == len(templates) > 100
    for control in controls:
        shipped = templates[control["template_id"]]
        assert control["category"] == shipped["category"], control["code"]
        assert control["sub_category"], f"{control['code']} was adopted with no Sub-type"
        assert control["sub_category"] == shipped["sub_category"], control["code"]


async def test_the_vocabulary_offers_the_shipped_sub_types_of_each_type(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, _ = workspaces
    async with _client(app, home) as api:
        shipped: dict[str, set[str]] = defaultdict(set)
        for template in (await _templates(api)).values():
            shipped[template["category"]].add(template["sub_category"])
        vocabulary = (await api.get("/controls/vocabulary")).json()

    offered = vocabulary["sub_categories"]
    assert set(offered) <= set(vocabulary["categories"])
    assert {category: set(names) for category, names in offered.items()} == shipped
    assert all(names == sorted(names) for names in offered.values())


async def test_the_library_filters_by_type_and_sub_type(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, _ = workspaces
    async with _client(app, home) as api:
        everything = (await api.get("/controls")).json()
        by_area: dict[tuple[str, str], set[str]] = defaultdict(set)
        for control in everything:
            by_area[(control["category"], control["sub_category"])].add(control["code"])
        category, sub_type = next(area for area, members in by_area.items() if len(members) > 1)
        expected = {c["code"] for c in everything if c["sub_category"] == sub_type}

        async def codes(**filters: str) -> set[str]:
            response = await api.get("/controls", params=filters)
            assert response.status_code == 200
            return {control["code"] for control in response.json()}

        assert await codes(sub_category=sub_type) == expected
        assert (
            await codes(category=category, sub_category=sub_type) == by_area[(category, sub_type)]
        )
        # Exact, never a substring; and a Sub-type under another Type matches nothing.
        assert await codes(sub_category=sub_type[:3]) == set()
        elsewhere = next(name for name, _ in by_area if name != category)
        assert await codes(category=elsewhere, sub_category=sub_type) == by_area.get(
            (elsewhere, sub_type), set()
        )
        assert await codes(sub_category="No such area") == set()


async def test_a_custom_control_takes_a_free_text_sub_type_up_to_one_hundred_characters(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, other = workspaces
    body = {
        "name": "Badge audit",
        "description": "Badge access is audited each quarter.",
        "category": "Physical & Environmental Security",
        "sub_category": "Badge Audits",
    }
    async with _client(app, home) as api, _client(app, other) as outsider:
        # Stray spaces would split one area into two entries in the register's facet.
        created = await api.post("/controls", json={**body, "sub_category": "  Badge Audits "})
        assert created.status_code == 201
        assert created.json()["sub_category"] == "Badge Audits"

        longest = await api.post("/controls", json={**body, "sub_category": "x" * 100})
        assert longest.status_code == 201
        too_long = await api.post("/controls", json={**body, "sub_category": "x" * 101})
        assert too_long.status_code == 422

        # Free text is this workspace's own: another one never sees it.
        mine = await api.get("/controls", params={"sub_category": "Badge Audits"})
        assert [c["code"] for c in mine.json()] == [created.json()["code"]]
        theirs = await outsider.get("/controls", params={"sub_category": "Badge Audits"})
        assert theirs.json() == []

        # An empty value clears it, and the register then files the control as having none.
        cleared = await api.patch(f"/controls/{created.json()['id']}", json={"sub_category": "  "})
        assert cleared.status_code == 200
        assert not cleared.json()["sub_category"]


async def test_changing_the_sub_type_is_audited_with_before_and_after(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, _ = workspaces
    async with _client(app, home) as api:
        controls = (await api.get("/controls")).json()
        control = next(c for c in controls if c["code"] == "IAM-04")

        changed = await api.patch(f"/controls/{control['id']}", json={"sub_category": "My Area"})
        assert changed.status_code == 200
        assert changed.json()["sub_category"] == "My Area"

        trail = await api.get(
            "/audit-log", params={"object_type": "control", "object_id": control["id"]}
        )
        newest = trail.json()["items"][0]
        assert newest["before"]["sub_category"] == control["sub_category"]
        assert newest["after"]["sub_category"] == "My Area"


async def test_the_exports_carry_type_sub_type_and_design(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, _ = workspaces
    async with _client(app, home) as api:
        controls = {c["code"]: c for c in (await api.get("/controls")).json()}
        report = (await api.get("/controls/report")).json()
        as_csv = await api.get("/controls/report/export", params={"format": "csv"})
        as_xlsx = await api.get("/controls/report/export", params={"format": "xlsx"})

    expected = ["Code", "Control", "Type", "Sub-type", "Design"]
    assert {r["code"]: r["sub_category"] for r in report["rows"]} == {
        code: control["sub_category"] for code, control in controls.items()
    }

    rows = list(csv.reader(io.StringIO(as_csv.content.decode("utf-8-sig"))))
    start = next(i for i, row in enumerate(rows) if row[:5] == expected)
    csv_rows = {row[0]: row for row in rows[start + 1 :] if row}
    assert csv_rows["IAM-04"][2] == controls["IAM-04"]["category"]
    assert csv_rows["IAM-04"][3] == controls["IAM-04"]["sub_category"]

    sheet = load_workbook(io.BytesIO(as_xlsx.content))["Controls"]
    assert [cell.value for cell in sheet[1]][:5] == expected
    first = [cell.value for cell in sheet[2]]
    assert first[2] == controls[first[0]]["category"]
    assert first[3] == controls[first[0]]["sub_category"]


async def test_the_backfill_fills_only_what_is_empty_and_is_idempotent(
    settings: Settings, workspaces: tuple[Workspace, Workspace]
) -> None:
    """What an earlier workspace's controls look like when this revision reaches it."""
    home, _ = workspaces
    migration = _migration()
    engine = create_async_engine(settings.database.effective_migration_url)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                # FORCE row level security filters the owner too, so the arrangement
                # and the reads below run as the home workspace.
                await connection.execute(
                    text("SELECT set_config('app.tenant_id', :tenant, true)"),
                    {"tenant": str(home.tenant_id)},
                )
                for code, value in (
                    ("IAM-04", None),  # never given one
                    ("GOV-04", ""),  # cleared
                    ("SD-02", "   "),  # blank
                    ("NS-04", None),  # its template is still empty too
                    ("NS-05", None),  # its template was refreshed by the loader since
                    ("EP-01", "Mine"),  # a person's own choice
                ):
                    await connection.execute(
                        text("UPDATE controls SET sub_category = :v WHERE code = :c"),
                        {"v": value, "c": code},
                    )
                # A control moved to another Type, with its Sub-type cleared on the way.
                await connection.execute(
                    text(
                        "UPDATE controls SET category = 'Endpoint Security', sub_category = NULL "
                        "WHERE code = 'HR-01'"
                    )
                )
                await connection.execute(
                    text("UPDATE control_templates SET sub_category = NULL WHERE code = 'NS-04'")
                )
                await connection.execute(
                    text(
                        "UPDATE control_templates SET sub_category = 'Refreshed by the loader' "
                        "WHERE code = 'NS-05'"
                    )
                )

                filled = await connection.run_sync(migration.backfill)

                result = await connection.execute(text("SELECT code, sub_category FROM controls"))
                controls = {row[0]: row[1] for row in result}
                snapshot = migration.SUB_TYPES
                assert filled == 5
                assert controls["IAM-04"] == snapshot["IAM-04"]
                assert controls["GOV-04"] == snapshot["GOV-04"]
                assert controls["SD-02"] == snapshot["SD-02"]
                assert controls["NS-04"] == snapshot["NS-04"]
                assert controls["NS-05"] == "Refreshed by the loader"
                assert controls["EP-01"] == "Mine"
                assert controls["HR-01"] is None
                assert all(value for code, value in controls.items() if code != "HR-01")

                result = await connection.execute(
                    text("SELECT code, sub_category FROM control_templates WHERE code LIKE 'NS-0_'")
                )
                templates = {row[0]: row[1] for row in result}
                assert templates["NS-04"] == snapshot["NS-04"]
                assert templates["NS-05"] == "Refreshed by the loader"

                assert await connection.run_sync(migration.backfill) == 0

                forced = await connection.scalar(
                    text("SELECT relforcerowsecurity FROM pg_class WHERE relname = 'controls'")
                )
                assert forced is True
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
