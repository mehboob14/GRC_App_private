"""The trace through the real app: the signed exit criterion, walked both ways.

"Tracing a vulnerability to its asset, the asset to a risk, the risk to a control, and
the control to a policy" is built here from real routes and then read back with one
call each way. The chain has no shortcuts (nothing links the finding, the asset or the
risk straight to the control), so the depths are the hops. Around it sit what the
signed spec adds ("from a control to the risks it mitigates, the policies that document
it, the evidence that proves it, and the assets and vulnerabilities in its scope"):
evidence, a second asset and a second finding tied straight to the control.

Then the walls: what a caller who cannot read a type sees, the caps, and a second
workspace that sees none of it.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, cast

import httpx
import pytest
from fastapi import FastAPI

from tests.support.audit import full_stream
from tests.support.iam import (
    INVITEE_PASSWORD,
    Workspace,
    invite_directly,
    signup_workspace,
    tenant_session_headers,
)
from verity.core.config import Settings
from verity.core.db import dispose_engine
from verity.main import create_app
from verity.modules.iam.service import iam_auth_service
from verity.modules.linkage import trace as trace_module

pytestmark = [pytest.mark.integration]

SCAN = b"title,severity,asset\nOpen admin panel,critical,Payments API\nWeak TLS,high,Ledger DB\n"


@dataclass(frozen=True, slots=True)
class World:
    workspace: Workspace
    api: httpx.AsyncClient
    asset: str
    finding: str
    risk: str
    control: str
    document: str
    evidence: tuple[str, str]
    other_asset: str
    other_finding: str


@pytest.fixture(autouse=True)
async def _fresh(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> AsyncIterator[None]:
    await dispose_engine()
    yield
    await dispose_engine()


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


def _client(app: FastAPI, headers: dict[str, str]) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test/api/v1", headers=headers
    )


def _admin(workspace: Workspace) -> dict[str, str]:
    return {"Authorization": f"Bearer {workspace.session_token}"}


def _json(response: httpx.Response, status: int = 200) -> dict[str, Any]:
    assert response.status_code == status, response.text
    return cast(dict[str, Any], response.json())


async def _build(api: httpx.AsyncClient, workspace: Workspace) -> World:
    """The exit criterion chain, plus what the spec says surrounds a control."""
    asset = _json(await api.post("/assets", json={"name": "Payments API"}), 201)["id"]
    other_asset = _json(await api.post("/assets", json={"name": "Ledger DB"}), 201)["id"]
    imported = await api.post(
        "/vulnerabilities/import",
        files={"file": ("scan.csv", SCAN)},
        data={"report_name": "Nightly scan"},
    )
    assert imported.status_code == 201, imported.text
    findings = {f["title"]: f["id"] for f in (await api.get("/vulnerabilities")).json()}

    register = (await api.get("/risks/registers")).json()[0]
    risk = _json(
        await api.post(
            "/risks",
            json={
                "register_id": register["id"],
                "title": "Payments outage",
                "category_id": register["categories"][0]["id"],
                "inherent_likelihood": 3,
                "inherent_impact": 4,
                # The risk to asset step of the chain, drawn the way the risk form does.
                "asset_ids": [asset],
            },
        ),
        201,
    )["id"]
    control = (await api.get("/controls")).json()[0]["id"]
    _json(await api.post(f"/risks/{risk}/controls", json={"control_ids": [control]}))
    document = _json(
        await api.post(
            "/documents",
            json={"title": "Access control policy", "doc_type": "policy", "control_ids": [control]},
        ),
        201,
    )["id"]
    evidence: list[str] = []
    for title in ("Access review export", "Quarterly attestation"):
        item = await api.post(
            "/evidence/link",
            json={
                "title": title,
                "link_url": "https://example.test/proof",
                "evidence_type": "other",
                "collected_at": "2026-10-01",
                "control_ids": [control],
            },
        )
        evidence.append(_json(item, 201)["id"])
    # The scope of the control: an asset and a finding drawn straight to it.
    _json(
        await api.post(
            f"/assets/{other_asset}/links", json={"target_type": "control", "target_id": control}
        ),
        201,
    )
    _json(
        await api.post(
            f"/vulnerabilities/{findings['Weak TLS']}/links",
            json={"target_type": "control", "target_id": control},
        ),
        201,
    )
    return World(
        workspace=workspace,
        api=api,
        asset=asset,
        finding=findings["Open admin panel"],
        risk=risk,
        control=control,
        document=document,
        evidence=(evidence[0], evidence[1]),
        other_asset=other_asset,
        other_finding=findings["Weak TLS"],
    )


@pytest.fixture
async def world(app: FastAPI) -> AsyncIterator[World]:
    workspace = await signup_workspace(company="Trace Ltd", email="founder@trace.example")
    async with _client(app, _admin(workspace)) as api:
        yield await _build(api, workspace)


async def _trace(
    api: httpx.AsyncClient, kind: str, record_id: str, depth: int | None = None
) -> dict[str, Any]:
    params: dict[str, Any] = {"type": kind, "id": record_id}
    if depth is not None:
        params["depth"] = depth
    return _json(await api.get("/linkage/trace", params=params))


def _by_key(body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {n["key"]: n for n in body["nodes"]}


async def test_the_exit_criterion_traces_both_ways_and_stops_at_the_depth_asked_for(
    world: World,
) -> None:
    """One workspace, built once, asked the questions below in turn."""
    await _finding_to_policy(world)
    await _policy_back_to_finding(world)
    await _depth_limits(world)
    await _refusals(world)


async def test_a_control_shows_its_whole_scope_and_its_linked_records_say_so(
    world: World,
) -> None:
    """The spec's own sentence about a control, then the pages that show the same pairs."""
    await _control_one_hop_out(world)
    await _control_linked_records(world)
    await _document_linked_records(world)
    await _no_audit_row(world)


# ---------------------------------------------------------------------------
# The exit criterion
# ---------------------------------------------------------------------------


async def _finding_to_policy(world: World) -> None:
    w = world
    body = await _trace(w.api, "vulnerability", w.finding)

    assert body["start"]["key"] == f"vulnerability:{w.finding}"
    assert body["start"]["title"] == "Open admin panel"
    assert (body["start"]["depth"], body["start"]["parent_key"]) == (0, None)
    nodes = _by_key(body)
    chain = [
        (f"asset:{w.asset}", 1, f"vulnerability:{w.finding}", "Found on"),
        (f"risk:{w.risk}", 2, f"asset:{w.asset}", "Related to"),
        (f"control:{w.control}", 3, f"risk:{w.risk}", "Mitigated by"),
        (f"document:{w.document}", 4, f"control:{w.control}", "Documented by"),
    ]
    for key, depth, parent, relation in chain:
        assert (nodes[key]["depth"], nodes[key]["parent_key"], nodes[key]["relation"]) == (
            depth,
            parent,
            relation,
        ), key
    assert nodes[f"document:{w.document}"]["title"] == "Access control policy"
    assert nodes[f"control:{w.control}"]["code"], "a control carries its code"
    # The rest of the control's scope sits at the same fourth hop.
    assert {k for k, n in nodes.items() if n["depth"] == 4} == {
        f"document:{w.document}",
        f"evidence:{w.evidence[0]}",
        f"evidence:{w.evidence[1]}",
        f"asset:{w.other_asset}",
        f"vulnerability:{w.other_finding}",
    }
    assert body["truncated"] is False
    assert body["hidden_types"] == []
    assert body["depth"] == 4


async def _policy_back_to_finding(world: World) -> None:
    w = world
    body = await _trace(w.api, "document", w.document)
    nodes = _by_key(body)
    back = [
        (f"control:{w.control}", 1, "Documents"),
        (f"risk:{w.risk}", 2, "Mitigates"),
        (f"asset:{w.asset}", 3, "Related to"),
        (f"vulnerability:{w.finding}", 4, "Affected by"),
    ]
    parent = f"document:{w.document}"
    for key, depth, relation in back:
        assert (nodes[key]["depth"], nodes[key]["parent_key"], nodes[key]["relation"]) == (
            depth,
            parent,
            relation,
        ), key
        parent = key
    # The finding drawn straight to the control is nearer than the one behind the risk.
    assert nodes[f"vulnerability:{w.other_finding}"]["depth"] == 2


async def _depth_limits(world: World) -> None:
    w = world
    one = await _trace(w.api, "vulnerability", w.finding, depth=1)
    assert [n["key"] for n in one["nodes"]] == [f"asset:{w.asset}"]
    assert one["depth"] == 1
    assert one["truncated"] is False, "stopping at the depth asked for is not a cap"

    two = await _trace(w.api, "vulnerability", w.finding, depth=2)
    assert [n["key"] for n in two["nodes"]] == [f"asset:{w.asset}", f"risk:{w.risk}"]

    for bad in (0, 5):
        refused = await w.api.get(
            "/linkage/trace", params={"type": "vulnerability", "id": w.finding, "depth": bad}
        )
        assert refused.status_code == 422, refused.text


async def _control_one_hop_out(world: World) -> None:
    w = world
    body = await _trace(w.api, "control", w.control, depth=1)
    start = f"control:{w.control}"
    assert [(n["type"], n["id"]) for n in body["nodes"]] == [
        ("risk", w.risk),
        ("document", w.document),
        ("evidence", w.evidence[0]),
        ("evidence", w.evidence[1]),
        ("asset", w.other_asset),
        ("vulnerability", w.other_finding),
    ], "grouped by type in the spec's order, oldest first within a type"
    assert {n["depth"] for n in body["nodes"]} == {1}
    assert {n["parent_key"] for n in body["nodes"]} == {start}

    nodes = _by_key(body)
    assert nodes[f"risk:{w.risk}"]["relation"] == "Mitigates"
    assert nodes[f"document:{w.document}"]["relation"] == "Documented by"
    assert nodes[f"evidence:{w.evidence[0]}"]["relation"] == "Proven by"

    # Each row says what its own module calls the record.
    said = {key: (n["code"], n["title"], n["status"], n["detail"]) for key, n in nodes.items()}
    assert said[f"document:{w.document}"] == ("POL-01", "Access control policy", "draft", "policy")
    assert said[f"evidence:{w.evidence[0]}"] == ("", "Access review export", "current", "other")
    assert said[f"asset:{w.other_asset}"] == ("", "Ledger DB", "planned", "application")
    assert said[f"vulnerability:{w.other_finding}"] == ("", "Weak TLS", "new", "high")
    assert said[f"risk:{w.risk}"][:3] == ("RSK-0001", "Payments outage", "open")

    # Only a link drawn on the links table knows when and by whom it was drawn.
    drawn = nodes[f"asset:{w.other_asset}"]
    assert drawn["linked_at"] is not None
    assert drawn["linked_by"] == "Founding Admin"
    assert drawn["relation"] == "Related to"
    for key in (f"risk:{w.risk}", f"document:{w.document}", f"evidence:{w.evidence[0]}"):
        assert (nodes[key]["linked_at"], nodes[key]["linked_by"]) == (None, None), key


async def _no_audit_row(world: World) -> None:
    before = len(await full_stream(world.workspace.tenant_id))
    await _trace(world.api, "control", world.control)
    await world.api.get(f"/controls/{world.control}/links")
    assert len(await full_stream(world.workspace.tenant_id)) == before


# ---------------------------------------------------------------------------
# Linked records, now with the pairs that have a table of their own
# ---------------------------------------------------------------------------


async def _control_linked_records(world: World) -> None:
    w = world
    body = _json(await w.api.get(f"/controls/{w.control}/links"))
    assert body["offered"] == ["risk", "document", "asset", "vulnerability"]
    assert body["can_link"] == ["asset", "vulnerability"], "the new groups are not linkable here"
    assert set(body["managed_elsewhere"]) == {"risk", "document"}

    records = {(r["target_type"], r["target_id"]): r for r in body["records"]}
    risk = records[("risk", w.risk)]
    assert (risk["relation"], risk["link_id"], risk["can_unlink"]) == ("mitigates", None, False)
    assert risk["title"] == "Payments outage"
    policy = records[("document", w.document)]
    assert (policy["relation"], policy["link_id"], policy["can_unlink"]) == (
        "documented_by",
        None,
        False,
    )
    # What was there before is untouched: the asset and finding drawn to the control.
    assert records[("asset", w.other_asset)]["can_unlink"] is True
    assert records[("vulnerability", w.other_finding)]["link_id"] is not None

    # And there is still no drawing a risk from the control's side.
    refused = await w.api.post(
        f"/controls/{w.control}/links", json={"target_type": "risk", "target_id": w.risk}
    )
    assert refused.status_code == 422, refused.text


async def _document_linked_records(world: World) -> None:
    w = world
    body = _json(await w.api.get(f"/documents/{w.document}/links"))
    assert body["offered"] == ["control", "asset", "vulnerability", "risk"]
    assert body["can_link"] == ["asset", "vulnerability", "risk"]
    assert set(body["managed_elsewhere"]) == {"control"}
    (control,) = [r for r in body["records"] if r["target_type"] == "control"]
    assert control["target_id"] == w.control
    assert (control["relation"], control["link_id"], control["can_unlink"]) == (
        "documents",
        None,
        False,
    )


# ---------------------------------------------------------------------------
# What the caller may read
# ---------------------------------------------------------------------------


async def _reader(app: FastAPI, w: World, *keys: str) -> httpx.AsyncClient:
    """A member whose role holds exactly these keys."""
    role = _json(
        await w.api.post("/roles", json={"name": "Trace reader", "permission_keys": list(keys)}),
        201,
    )
    invited = await invite_directly(
        w.workspace, email="reader@trace.example", full_name="Casey Reader", role_name=role["name"]
    )
    await iam_auth_service.accept_invitation(
        token=invited.invite_token, full_name="Casey Reader", password=INVITEE_PASSWORD
    )
    return _client(app, tenant_session_headers(invited.member.membership_id))


async def test_a_caller_who_cannot_read_risks_gets_no_risks_and_nothing_behind_them(
    app: FastAPI, world: World
) -> None:
    w = world
    reader = await _reader(
        app,
        w,
        "assets:read",
        "vulnerabilities:read",
        "frameworks:read",
        "documents:read",
        "evidence:read",
    )
    async with reader:
        from_finding = await _trace(reader, "vulnerability", w.finding)
        assert [n["key"] for n in from_finding["nodes"]] == [f"asset:{w.asset}"]
        assert from_finding["hidden_types"] == ["risk"]

        from_control = await _trace(reader, "control", w.control)
        types = {n["type"] for n in from_control["nodes"]}
        assert types == {"document", "evidence", "asset", "vulnerability"}
        assert from_control["hidden_types"] == ["risk"]
        keys = set(_by_key(from_control))
        assert f"risk:{w.risk}" not in keys
        assert f"vulnerability:{w.finding}" not in keys, "only reachable through the risk"
        assert f"asset:{w.asset}" not in keys, "only reachable through the risk"

        # The control's own page leaves the risk group out rather than showing it empty.
        links = _json(await reader.get(f"/controls/{w.control}/links"))
        assert "risk" not in links["offered"]
        assert all(r["target_type"] != "risk" for r in links["records"])

        # The start record needs its own module's key.
        for kind, record_id in (("risk", w.risk), ("vendor", str(uuid.uuid4()))):
            refused = await reader.get("/linkage/trace", params={"type": kind, "id": record_id})
            assert refused.status_code == 403, refused.text


async def _refusals(world: World) -> None:
    refused = await world.api.get(
        "/linkage/trace", params={"type": "incident", "id": str(uuid.uuid4())}
    )
    assert refused.status_code == 422, refused.text
    gone = await world.api.get("/linkage/trace", params={"type": "asset", "id": str(uuid.uuid4())})
    assert gone.status_code == 404, gone.text


# ---------------------------------------------------------------------------
# Caps
# ---------------------------------------------------------------------------


async def test_the_caps_are_flagged_not_silent(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    w = world
    whole = await _trace(w.api, "control", w.control, depth=1)
    assert whole["truncated"] is False
    assert len([n for n in whole["nodes"] if n["type"] == "evidence"]) == 2

    # Too many of one type under a record: the oldest is kept and the page says so.
    with monkeypatch.context() as patch:
        patch.setattr(trace_module, "NEIGHBOURS_PER_TYPE", 1)
        capped = await _trace(w.api, "control", w.control, depth=1)
    evidence = [n["id"] for n in capped["nodes"] if n["type"] == "evidence"]
    assert evidence == [w.evidence[0]]
    assert capped["truncated"] is True
    assert capped["neighbour_limit"] == 1
    assert {n["type"] for n in capped["nodes"]} == {n["type"] for n in whole["nodes"]}

    # Too many records in all: the nearest survive, one per hop here.
    with monkeypatch.context() as patch:
        patch.setattr(trace_module, "MAX_NODES", 4)
        short = await _trace(w.api, "vulnerability", w.finding)
    assert len(short["nodes"]) == 4
    assert short["truncated"] is True
    assert short["node_limit"] == 4
    assert [n["depth"] for n in short["nodes"]] == [1, 2, 3, 4]


# ---------------------------------------------------------------------------
# Tenant wall
# ---------------------------------------------------------------------------


async def test_another_workspace_gets_a_404_and_sees_none_of_the_edges(
    app: FastAPI, world: World
) -> None:
    w = world
    other = await signup_workspace(company="Elsewhere Ltd", email="founder@elsewhere.example")
    async with _client(app, _admin(other)) as outsider:
        for kind, record_id in (
            ("asset", w.asset),
            ("vulnerability", w.finding),
            ("risk", w.risk),
            ("control", w.control),
            ("document", w.document),
            ("evidence", w.evidence[0]),
        ):
            gone = await outsider.get("/linkage/trace", params={"type": kind, "id": record_id})
            assert gone.status_code == 404, (kind, gone.text)

        # Its own record traces to nothing: none of this workspace's links reach it.
        mine = _json(await outsider.post("/assets", json={"name": "Payments API"}), 201)["id"]
        alone = await _trace(outsider, "asset", mine)
        assert alone["nodes"] == []
        assert alone["truncated"] is False

    # And nothing of theirs turns up here.
    home = await _trace(w.api, "control", w.control)
    assert mine not in str(home)
