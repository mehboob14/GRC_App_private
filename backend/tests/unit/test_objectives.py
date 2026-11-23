"""Assessment objectives: the outcome rules and the content rules (AO-1, AO-2, AO-6)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from verity.modules.objectives import pack
from verity.modules.objectives.outcomes import (
    Facts,
    artifact_state,
    control_readiness,
    objective_outcome,
)
from verity.seed.seal import ContentError

CONTENT = Path(__file__).resolve().parents[2] / "src" / "verity" / "seed" / "content"

DOC = {"key": "doc-x", "sources": [{"kind": "document", "template": "x"}]}
REC = {"key": "rec", "sources": [{"kind": "check", "checks": ["c.one"]}, {"kind": "person"}]}


def _facts(checks: dict[str, str] | None = None, tagged: dict[str, list[str]] | None = None,
           templates: set[str] | None = None) -> Facts:  # fmt: skip
    return Facts(checks or {}, tagged or {}, frozenset(templates or set()))


def test_artifact_rules_fail_wins_and_rule_a_never_grants_from_a_check() -> None:
    assert artifact_state(DOC, _facts(templates={"x"})).state == "satisfied"
    assert artifact_state(DOC, _facts()).reason == "missing"
    assert artifact_state(REC, _facts({"c.one": "pass"})).state == "satisfied"
    assert artifact_state(REC, _facts({"c.one": "pass"}), rule="A").reason == "missing"
    failing = _facts({"c.one": "fail"}, {"rec": ["current"]})
    assert artifact_state(REC, failing).reason == "deviation", "a failing check beats an upload"
    assert artifact_state(REC, _facts({"c.one": "error"}, {"rec": ["current"]})).reason == (
        "insufficient_information"
    )
    assert artifact_state(REC, _facts(tagged={"rec": ["lapsed"]})).reason == "stale"
    assert artifact_state(REC, _facts(tagged={"rec": ["pending"]})).reason == "awaiting_review"
    assert artifact_state(REC, _facts(tagged={"rec": ["current"]}), rule="A").state == "satisfied"


def test_objective_and_control_rules() -> None:
    objective = {
        "methods": [
            {"method": "examine", "artifacts": ["doc-x"]},
            {"method": "interview", "artifacts": []},
        ]
    }
    yes = {"doc-x": artifact_state(DOC, _facts(templates={"x"}))}
    no = {"doc-x": artifact_state(DOC, _facts())}
    assert objective_outcome(objective, yes) == ("satisfied", None)
    assert objective_outcome(objective, no) == ("not_tested", None)
    assert objective_outcome(objective, no, not_applicable=True) == ("not_applicable", None)
    assert control_readiness("implemented", [("design", "satisfied"), ("operating", "satisfied")])[
        2
    ]
    assert not control_readiness("in_progress", [("design", "satisfied")])[2]
    assert control_readiness("implemented", [("design", "not_applicable")])[0]
    assert not control_readiness("implemented", [("operating", "satisfied")])[0]


def test_the_pack_refuses_unknown_artifacts_and_interview_alone() -> None:
    artifacts = [{"key": "a"}]
    good = {
        "code": "X-01.A",
        "assurance": "design",
        "methods": [{"method": "examine", "artifacts": ["a"]}],
    }
    pack.validate(artifacts, [{"control": "X-01", "objectives": [good]}])
    unknown = {**good, "methods": [{"method": "examine", "artifacts": ["zz"]}]}
    with pytest.raises(ContentError, match="unknown artifacts"):
        pack.validate(artifacts, [{"control": "X-01", "objectives": [unknown]}])
    nobody = {**good, "methods": [*good["methods"], {"method": "interview", "artifacts": []}]}
    with pytest.raises(ContentError, match="names nobody"):
        pack.validate(artifacts, [{"control": "X-01", "objectives": [nobody]}])
    talk = {**good, "methods": [{"method": "interview", "artifacts": ["a"], "who": "hr_lead"}]}
    with pytest.raises(ContentError, match="interview alone"):
        pack.validate(artifacts, [{"control": "X-01", "objectives": [talk]}])
    operating_only = {**good, "assurance": "operating"}
    with pytest.raises(ContentError, match="no design objective"):
        pack.validate(artifacts, [{"control": "X-01", "objectives": [operating_only]}])


def test_shipped_pack_covers_every_control() -> None:
    artifacts, by_control = pack.load()
    assert len(by_control) == 133
    manifest = pack.manifest()
    codes = {
        t["code"]
        for name in ("soc2", "iso27001")
        for t in json.loads((CONTENT / name / "control_templates.json").read_text("utf-8"))
    }
    # AO-6: a control added to the library ships with objectives, or the build fails.
    assert codes <= set(by_control) | set(manifest["controls_pending"]), codes - set(by_control)
    for items in by_control.values():
        for o in items:
            assert len(o["statement"]) <= 300, o["code"]
            assert not re.search("[\u2012\u2013\u2014\u2015]", o["statement"]), o["code"]
    templates = {
        t["key"]
        for t in json.loads((CONTENT / "policies" / "document_templates.json").read_text("utf-8"))
    }
    checks = {
        c["key"] for c in json.loads((CONTENT / "automation" / "checks.json").read_text("utf-8"))
    }
    for a in artifacts.values():
        for s in a["sources"]:
            if s["kind"] == "document":
                assert s["template"] in templates, a["key"]
            if s["kind"] == "check":
                assert set(s["checks"]) <= checks, a["key"]
