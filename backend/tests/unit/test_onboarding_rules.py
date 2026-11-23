"""The suggestion rules: the evaluator's three answers, and every rule names real things."""

from __future__ import annotations

import json
from pathlib import Path

from verity.modules.onboarding.rules import RULES, firing, holds
from verity.modules.tenancy.profile_questions import QUESTIONS

CONTENT = Path(__file__).resolve().parents[2] / "src" / "verity" / "seed" / "content"


def test_unknown_answers_never_fire() -> None:
    leaf = {"fact": "offices", "op": "eq", "value": "none"}
    assert holds(leaf, {"offices": "none"}) is True
    assert holds(leaf, {"offices": "own_premises"}) is False
    assert holds(leaf, {}) is None
    assert (
        holds(
            {"fact": "builds_software", "op": "eq", "value": "no"}, {"builds_software": "not_sure"}
        )
        is None
    )
    both = {"all": [leaf, {"fact": "public_app", "op": "eq", "value": "no"}]}
    assert holds(both, {"offices": "none"}) is None
    assert holds(both, {"offices": "own_premises"}) is False
    either = {"any": [leaf, {"fact": "public_app", "op": "eq", "value": "no"}]}
    assert holds(either, {"public_app": "no"}) is True
    assert (
        holds(
            {"fact": "operating_countries", "op": "contains", "value": "SA"},
            {"operating_countries": ["SA"]},
        )
        is True
    )


def test_iso_rules_need_iso_active() -> None:
    answers = {"offices": "none"}
    assert {r.key for r in firing(answers, {"SOC2"})} == {"no_offices.controls"}
    assert {r.key for r in firing(answers, {"SOC2", "ISO27001"})} == {
        "no_offices.controls",
        "no_offices.iso",
    }


def test_rules_name_real_facts_controls_and_requirements() -> None:
    options = {q.key: {o[0] for o in q.options} for q in QUESTIONS}
    controls = {
        t["code"]
        for pack in ("soc2", "iso27001")
        for t in json.loads((CONTENT / pack / "control_templates.json").read_text("utf-8"))
    }
    iso = {
        r["code"]
        for r in json.loads((CONTENT / "iso27001" / "requirements.json").read_text("utf-8"))
    }
    for rule in RULES:
        leaf = rule.when
        assert leaf["fact"] in options, rule.key
        assert leaf["value"] in options[leaf["fact"]], rule.key
        known = controls if rule.kind == "control_status" else iso
        assert set(rule.subjects) <= known, (rule.key, set(rule.subjects) - known)
        assert "{company}" in rule.reason or "{supplier}" in rule.reason, rule.key
