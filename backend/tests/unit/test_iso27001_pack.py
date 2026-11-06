"""The shipped ISO/IEC 27001:2022 pack: every requirement is answered, every claim is explained.

The same rules the SOC 2 pack lives by (a mapping nobody can explain is a claim nobody can
check), plus what is particular to this pack: it has the standard's structure, its new
controls follow the library's rules, and it never ships the standard's own text.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

import verity
from verity.modules.compliance.models import CONTROL_CATEGORIES, SCOPE_MODELS
from verity.seed.loader import verify_pack

_CONTENT = Path(verity.__file__).parent / "seed" / "content"
_ISO = _CONTENT / "iso27001"
_SOC2 = _CONTENT / "soc2"

_COVERAGE = {"full", "partial"}
_ASSURANCE = {"design", "operating"}
_CADENCE = {"annual", "quarterly", "monthly", "on_change", "per_event", "once", "ongoing"}
_MODULES = {"documents", "risks", "vendors", "assets", "vulnerabilities", "tasks", "controls"}
_DASHES = (chr(0x2014), chr(0x2013))


def _load(path: Path) -> Any:  # noqa: ANN401 — a JSON document is Any by nature
    return json.loads(path.read_text(encoding="utf-8"))


FRAMEWORK = _load(_ISO / "framework.json")
REQUIREMENTS: list[dict[str, Any]] = _load(_ISO / "requirements.json")
MAPPINGS: list[dict[str, Any]] = _load(_ISO / "template_requirements.json")
NEW_TEMPLATES: list[dict[str, Any]] = _load(_ISO / "control_templates.json")
SOC2_TEMPLATES: list[dict[str, Any]] = _load(_SOC2 / "control_templates.json")
CHECK_CONTROLS: dict[str, set[str]] = {
    check["key"]: {m["code"] for m in check["controls"]}
    for check in _load(_ISO.parent / "automation" / "checks.json")
}
SOC2_CODES = {t["code"] for t in SOC2_TEMPLATES}
NEW_CODES = {t["code"] for t in NEW_TEMPLATES}
ALL_CODES = SOC2_CODES | NEW_CODES


def test_the_pack_is_sealed() -> None:
    verify_pack(_ISO)


def test_the_framework_says_how_its_scope_is_chosen() -> None:
    assert FRAMEWORK["code"] == "ISO27001"
    assert FRAMEWORK["scope_model"] == "applicability"
    assert FRAMEWORK["scope_model"] in SCOPE_MODELS
    # SOC 2 keeps the default position, so it stays the first framework listed.
    assert FRAMEWORK["position"] > 100


def test_the_pack_has_the_structure_of_the_standard() -> None:
    codes = [r["code"] for r in REQUIREMENTS]
    assert len(codes) == len(set(codes)) == 123
    annex = [c for c in codes if c.startswith("A.")]
    assert len(annex) == 93
    assert len(codes) - len(annex) == 30
    by_section = Counter(c.split(".")[1] for c in annex)
    assert by_section == {"5": 37, "6": 8, "7": 14, "8": 34}
    for requirement in REQUIREMENTS:
        assert requirement["requirement_key"] == f"ISO27001:{requirement['code']}"


def test_clauses_cannot_be_excluded_and_annex_a_can() -> None:
    for requirement in REQUIREMENTS:
        is_annex = requirement["code"].startswith("A.")
        assert requirement["is_always_in_scope"] is (not is_annex), requirement["code"]
        expected = "Annex A controls" if is_annex else "Management system"
        assert requirement["trust_services_category"] == expected


def test_every_requirement_is_answered_and_every_new_control_is_used() -> None:
    assert {r["requirement_key"] for r in REQUIREMENTS} == {m["requirement_key"] for m in MAPPINGS}
    used = {m["template_code"] for m in MAPPINGS}
    assert NEW_CODES <= used, f"new controls that answer nothing: {sorted(NEW_CODES - used)}"
    assert used <= ALL_CODES, f"mappings to controls that do not exist: {sorted(used - ALL_CODES)}"


def test_every_mapping_says_how_much_it_covers_and_why() -> None:
    for row in MAPPINGS:
        label = f"{row['requirement_key']} <- {row['template_code']}"
        assert row["coverage"] in _COVERAGE, label
        assert len(row["rationale"].strip()) > 20, label


def test_the_mapping_has_no_duplicates_and_stays_tight() -> None:
    pairs = [(m["requirement_key"], m["template_code"]) for m in MAPPINGS]
    assert len(pairs) == len(set(pairs))
    # A requirement is met only when every control mapped to it is ready, so a long list
    # makes it unreachable. Review any requirement above this before raising the limit.
    per_requirement = Counter(m["requirement_key"] for m in MAPPINGS)
    # Reviewed and kept wide: privacy is met by seven distinct DM and GOV controls
    # (consent, correction, processors, access requests, purpose, notice, obligations).
    reviewed = {"ISO27001:A.5.34": 7}
    over = {key: n for key, n in per_requirement.items() if n > reviewed.get(key, 6)}
    assert not over, over


def test_the_new_controls_follow_the_library_rules() -> None:
    assert len(NEW_TEMPLATES) == 17
    codes = [t["code"] for t in NEW_TEMPLATES]
    keys = [t["canonical_key"] for t in NEW_TEMPLATES]
    assert len(codes) == len(set(codes))
    assert not set(codes) & SOC2_CODES
    soc2_keys = {t["canonical_key"] for t in SOC2_TEMPLATES}
    assert len(keys) == len(set(keys))
    assert not set(keys) & soc2_keys
    for template in NEW_TEMPLATES:
        code = template["code"]
        assert template["category"] in CONTROL_CATEGORIES, code
        assert 0 < len(template["sub_category"]) <= 40, code
        words = [w for w in template["sub_category"].replace("/", " ").split() if w[:1].isalpha()]
        assert all(w[0].isupper() for w in words), code
        assert template["importance"] in {"mandatory", "preferred"}, code
        assert template["control_sub_type"] in {"Manual", "Automated", "Hybrid"}, code
        assert template["description"].strip()
        assert template["implementation_guidance"].strip()
        items = template["evidence"]
        assert items, f"{code} lists no expected evidence"
        assert len({i["key"] for i in items}) == len(items), code
        for item in items:
            assert item["assurance"] in _ASSURANCE, code
            assert item["cadence"] in _CADENCE, code
            assert item["source"] in {"upload", "platform"}, code
            if item["source"] == "platform":
                assert item["module"] in _MODULES, code
            # Automation is promised only by a shipped check that serves this control.
            for check_key in item.get("automated_by", []):
                assert code in CHECK_CONTROLS.get(check_key, set()), (code, check_key)


def test_control_text_is_framework_neutral() -> None:
    """The library is one list. A control that names a standard cannot serve the next one."""
    for template in NEW_TEMPLATES:
        text = " ".join(
            [template["name"], template["description"], template["implementation_guidance"]]
            + [i["name"] for i in template["evidence"]]
        )
        for word in (
            "SOC 2",
            "ISO 27001",
            "ISO/IEC",
            "Annex A",
            "clause ",
            "criterion",
            "criteria",
        ):
            assert word.lower() not in text.lower(), (template["code"], word)


def test_requirement_names_are_short_and_descriptions_are_summaries() -> None:
    for requirement in REQUIREMENTS:
        code = requirement["code"]
        assert 2 <= len(requirement["name"]) <= 70, code
        words = len(requirement["description"].split())
        assert 6 <= words <= 55, (code, words)


def test_nothing_shown_in_the_product_uses_a_dash_as_punctuation() -> None:
    texts: list[str] = [FRAMEWORK["name"], FRAMEWORK["description"]]
    for requirement in REQUIREMENTS:
        texts += [requirement["name"], requirement["description"]]
    texts += [m["rationale"] for m in MAPPINGS]
    for template in NEW_TEMPLATES:
        texts += [template["name"], template["description"], template["implementation_guidance"]]
        texts += [template["sub_category"]]
        texts += [i["name"] for i in template["evidence"]]
    offenders = [t for t in texts if any(d in t for d in _DASHES) or " - " in t]
    assert not offenders, offenders[:3]


@pytest.mark.parametrize("code", sorted(NEW_CODES))
def test_each_new_control_has_four_guidance_steps(code: str) -> None:
    template = next(t for t in NEW_TEMPLATES if t["code"] == code)
    steps = [line for line in template["implementation_guidance"].split("\n") if line.strip()]
    assert len(steps) == 4, code
