"""The trace walk's rules, on a graph held in a dict: no database, no services.

Each test builds the few records it needs and asks the walk one question. The caps are
lowered by patching the module constants, which is what the integration suite does too.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from itertools import pairwise

import pytest

from verity.modules.linkage import trace
from verity.modules.linkage.trace import Candidate, Label, Ref, Trace, phrase, relation_key, walk

ALL_TYPES = frozenset(trace.TYPE_ORDER)


def _ref(name: str, kind: str = "asset") -> Ref:
    return Ref(kind, uuid.uuid5(uuid.NAMESPACE_URL, name))


def _edge(ref: Ref, relation: str = "relates_to") -> Candidate:
    return Candidate(ref, relation, "outgoing")


class Graph:
    """Edges by record, and a count of how often each record was opened."""

    def __init__(self, edges: dict[Ref, list[Candidate]], gone: set[Ref] | None = None) -> None:
        self.edges = edges
        self.gone = gone or set()
        self.opened: list[Ref] = []

    async def edges_of(self, ref: Ref) -> list[Candidate]:
        self.opened.append(ref)
        return self.edges.get(ref, [])

    async def label_of(self, ref: Ref) -> Label | None:
        if ref in self.gone:
            return None
        return Label(code=ref.type[:3].upper(), title=str(ref.id)[:8], status="active", detail=None)


async def _walk(
    graph: Graph,
    start: Ref,
    *,
    depth: int = 4,
    readable: frozenset[str] = ALL_TYPES,
) -> Trace:
    return await walk(
        start,
        Label(code="", title="start", status="active", detail=None),
        edges=graph.edges_of,
        label=graph.label_of,
        readable=readable,
        depth=depth,
    )


def _keys(result: Trace) -> list[str]:
    return [node.key for node in result.nodes]


async def test_a_record_reached_two_ways_is_listed_once_under_its_shortest_path() -> None:
    start, b, c, d = (_ref(n) for n in ["start", "b", "c", "d"])
    graph = Graph(
        {
            start: [_edge(b), _edge(c)],
            b: [_edge(d), _edge(start)],
            c: [_edge(d), _edge(start)],
            d: [_edge(b)],
        }
    )
    result = await _walk(graph, start)
    assert _keys(result) == [b.key, c.key, d.key]
    by_key = {n.key: n for n in result.nodes}
    assert [by_key[k].depth for k in (b.key, c.key, d.key)] == [1, 1, 2]
    assert by_key[d.key].parent_key == b.key, "the first parent to reach it keeps it"
    assert start.key not in by_key, "the start is the header, never a node"
    assert result.start.depth == 0
    assert not result.truncated


async def test_a_record_that_is_a_hop_nearer_by_another_route_stays_at_the_nearer_depth() -> None:
    start, near, far, target = (_ref(n) for n in ["start", "near", "far", "target"])
    # target is 3 hops away through near and far, and 1 hop away directly.
    graph = Graph({start: [_edge(near), _edge(target)], near: [_edge(far)], far: [_edge(target)]})
    result = await _walk(graph, start)
    placed = {n.key: n for n in result.nodes}
    assert placed[target.key].depth == 1
    assert placed[target.key].parent_key == start.key


async def test_depth_stops_the_walk_and_each_record_is_opened_once() -> None:
    chain = [_ref(f"r{i}") for i in range(6)]
    graph = Graph({a: [_edge(b)] for a, b in pairwise(chain)})
    result = await _walk(graph, chain[0], depth=2)
    assert _keys(result) == [chain[1].key, chain[2].key]
    assert graph.opened == [chain[0], chain[1]], "records at the last hop are not opened"
    assert result.depth == 2
    assert not result.truncated, "stopping at the depth asked for is not a cap biting"


async def test_a_type_the_caller_cannot_read_is_named_and_never_walked_through() -> None:
    start = _ref("start", "vulnerability")
    risk = _ref("risk", "risk")
    asset = _ref("asset")
    control = _ref("control", "control")
    graph = Graph({start: [_edge(asset), _edge(risk)], risk: [_edge(control)], asset: []})
    result = await _walk(graph, start, readable=ALL_TYPES - {"risk"})
    assert _keys(result) == [asset.key]
    assert result.hidden_types == ["risk"]
    assert risk not in graph.opened, "a hidden record is never opened, so nothing behind it leaks"


async def test_nothing_hidden_when_the_caller_can_read_everything() -> None:
    start, other = _ref("start"), _ref("other", "risk")
    result = await _walk(Graph({start: [_edge(other)]}), start)
    assert result.hidden_types == []


async def test_too_many_of_one_type_under_a_record_flags_truncation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(trace, "NEIGHBOURS_PER_TYPE", 2)
    start = _ref("start")
    findings = [_ref(f"v{i}", "vulnerability") for i in range(3)]
    result = await _walk(Graph({start: [_edge(v) for v in findings]}), start)
    assert _keys(result) == [findings[0].key, findings[1].key], "the first ones are kept"
    assert result.truncated
    assert result.neighbour_limit == 2


async def test_exactly_the_cap_is_not_truncation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(trace, "NEIGHBOURS_PER_TYPE", 2)
    monkeypatch.setattr(trace, "MAX_NODES", 2)
    start = _ref("start")
    findings = [_ref(f"v{i}", "vulnerability") for i in range(2)]
    result = await _walk(Graph({start: [_edge(v) for v in findings]}), start)
    assert len(result.nodes) == 2
    assert not result.truncated


async def test_the_cap_applies_per_type_so_another_type_still_gets_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(trace, "NEIGHBOURS_PER_TYPE", 1)
    start = _ref("start")
    v1, v2 = _ref("v1", "vulnerability"), _ref("v2", "vulnerability")
    risk = _ref("risk", "risk")
    result = await _walk(Graph({start: [_edge(v1), _edge(v2), _edge(risk)]}), start)
    assert sorted(_keys(result)) == sorted([v1.key, risk.key])
    assert result.truncated


async def test_too_many_records_in_all_stops_the_walk_nearest_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(trace, "MAX_NODES", 3)
    start = _ref("start")
    first = [_ref(f"a{i}", "risk") for i in range(2)]
    deeper = [_ref(f"b{i}", "control") for i in range(2)]
    graph = Graph({start: [_edge(r) for r in first], first[0]: [_edge(c) for c in deeper]})
    result = await _walk(graph, start)
    assert _keys(result) == [first[0].key, first[1].key, deeper[0].key]
    assert result.truncated
    assert result.node_limit == 3


async def test_children_group_by_type_in_the_fixed_order_and_keep_their_own_order() -> None:
    start = _ref("start", "control")
    v1, v2 = _ref("v1", "vulnerability"), _ref("v2", "vulnerability")
    asset, risk, doc = _ref("asset"), _ref("risk", "risk"), _ref("doc", "document")
    graph = Graph({start: [_edge(v2), _edge(asset), _edge(risk), _edge(v1), _edge(doc)]})
    result = await _walk(graph, start)
    assert _keys(result) == [risk.key, doc.key, asset.key, v2.key, v1.key]


async def test_a_record_that_is_gone_is_skipped_and_costs_no_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(trace, "NEIGHBOURS_PER_TYPE", 1)
    start = _ref("start")
    gone, here = _ref("gone"), _ref("here")
    result = await _walk(Graph({start: [_edge(gone), _edge(here)]}, gone={gone}), start)
    assert _keys(result) == [here.key]
    assert not result.truncated


async def test_the_edge_a_node_was_reached_by_travels_with_it() -> None:
    start, other = _ref("start", "risk"), _ref("other", "control")
    when = datetime(2026, 10, 1, 9, 30, tzinfo=UTC)
    member = uuid.uuid4()
    edge = Candidate(other, "mitigated_by", "outgoing", linked_at=when, linked_by_id=member)
    result = await _walk(Graph({start: [edge]}), start)
    (node,) = result.nodes
    assert (node.relation, node.direction) == ("mitigated_by", "outgoing")
    assert (node.linked_at, node.linked_by_id) == (when, member)
    assert node.parent_key == start.key


async def test_a_cycle_back_to_the_start_adds_nothing() -> None:
    start, other = _ref("start"), _ref("other")
    result = await _walk(Graph({start: [_edge(other)], other: [_edge(start)]}), start)
    assert _keys(result) == [other.key]


def test_a_link_reads_the_other_way_round_from_its_other_end() -> None:
    assert relation_key("remediates", "outgoing") == "remediates"
    assert relation_key("remediates", "incoming") == "remediated_by"
    assert relation_key("caused_by", "incoming") == "cause_of"
    assert relation_key("relates_to", "incoming") == "relates_to"
    assert relation_key("something_new", "incoming") == "something_new", "unknown stays as is"


def test_relation_keys_read_as_words() -> None:
    assert phrase("mitigated_by") == "Mitigated by"
    assert phrase("found_on") == "Found on"
    assert phrase("relates_to") == "Related to"
    assert "-" not in phrase("depended_on_by")
