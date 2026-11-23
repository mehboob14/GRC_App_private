"""The country reference pack: sealed, well formed, and matched the way part 4 says."""

from __future__ import annotations

import json
import re
from pathlib import Path

from verity.modules.regulations.pack import entries, match, uncovered
from verity.modules.tenancy.profile_questions import QUESTIONS

CONTENT = Path(__file__).resolve().parents[2] / "src" / "verity" / "seed" / "content"
DASHES = re.compile("[\u2012\u2013\u2014\u2015]")


def _leaves(cond: dict) -> list[dict]:
    if "all" in cond:
        return [leaf for c in cond["all"] for leaf in _leaves(c)]
    if "any" in cond:
        return [leaf for c in cond["any"] for leaf in _leaves(c)]
    return [cond]


def test_pack_is_sealed_unique_and_names_real_things() -> None:
    pack = entries()
    assert len(pack) == 83
    keys = [e["key"] for e in pack]
    assert len(keys) == len(set(keys))
    facts = {q.key for q in QUESTIONS}
    controls = {
        t["code"]
        for name in ("soc2", "iso27001")
        for t in json.loads((CONTENT / name / "control_templates.json").read_text("utf-8"))
    }
    for e in pack:
        for t in e["triggers"]:
            for leaf in _leaves({k: t[k] for k in ("all", "any") if k in t}):
                assert leaf["fact"] in facts, (e["key"], leaf["fact"])
                assert leaf["op"] in {"eq", "in", "any_in", "exists"}, e["key"]
        for code in e["helps"]:
            if code.endswith("*"):
                assert any(c.startswith(code[:-1]) for c in controls), (e["key"], code)
            else:
                assert code in controls, (e["key"], code)
        assert not DASHES.search(json.dumps(e, ensure_ascii=False)), e["key"]


def test_matching_follows_the_three_wordings() -> None:
    saudi = next(e for e in entries() if e["key"] == "SA-01")
    assert match(saudi, {"hq_country": "SA"}).confidence == "applies"  # type: ignore[union-attr]
    assert (
        match(
            saudi,
            {
                "hq_country": "GB",
                "operating_countries": ["GB"],
                "customer_regions": ["GB"],
                "personal_data_role": "staff_only",
            },
        )
        is None
    )
    # A first tier entry with the deciding answers missing reads "check", never silence.
    unknown = match(saudi, {})
    assert unknown is not None
    assert unknown.confidence == "check"


def test_countries_outside_the_pack_are_named() -> None:
    assert uncovered({"hq_country": "IN", "operating_countries": ["DE", "SG"]}) == ["IN", "SG"]
