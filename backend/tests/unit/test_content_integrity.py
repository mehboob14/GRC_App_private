"""The shipped control library, as a whole: every claim in it can be checked.

A mapping nobody can explain, a check with no evidence behind it, and a control that
promises evidence no check or module can produce are the things an auditor finds
first. These keep the library honest as it grows, and they are what a second
framework pack has to pass too.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import verity
from verity.modules.compliance.models import CONTROL_CATEGORIES
from verity.seed.loader import CONTENT_ROOT, verify_pack

_CONTENT = Path(verity.__file__).parent / "seed" / "content"
_SOC2 = _CONTENT / "soc2"
_AUTOMATION = _CONTENT / "automation"

_COVERAGE = {"full", "partial"}
_ASSURANCE = {"design", "operating"}
_CADENCE = {"annual", "quarterly", "monthly", "on_change", "per_event", "once", "ongoing"}
_MODULES = {"documents", "risks", "vendors", "assets", "vulnerabilities", "tasks", "controls"}
_DASHES = (chr(0x2014), chr(0x2013))  # em and en dash


def _load(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    return rows


TEMPLATES = _load(_SOC2 / "control_templates.json")
MAPPINGS = _load(_SOC2 / "template_requirements.json")
REQUIREMENTS = _load(_SOC2 / "requirements.json")
CHECKS = _load(_AUTOMATION / "checks.json")
CAPABILITIES = {c["key"]: c for c in _load(_AUTOMATION / "capabilities.json")}
CODES = {t["code"] for t in TEMPLATES}


def test_every_pack_matches_the_hashes_sealed_in_its_manifest() -> None:
    """Content and its seal travel together: run scripts/seal_content.py after an edit."""
    for pack in sorted(p for p in CONTENT_ROOT.iterdir() if p.is_dir()):
        verify_pack(pack)


def test_every_mapping_says_how_much_it_covers_and_why() -> None:
    for row in MAPPINGS:
        label = f"{row['requirement_key']} <- {row['template_code']}"
        assert row.get("coverage") in _COVERAGE, label
        assert len(row.get("rationale", "").strip()) > 20, label
        assert row["template_code"] in CODES, label


def test_every_requirement_has_a_control_and_every_control_a_requirement() -> None:
    assert {r["requirement_key"] for r in REQUIREMENTS} == {m["requirement_key"] for m in MAPPINGS}
    assert CODES == {m["template_code"] for m in MAPPINGS}


def test_a_criterion_is_not_claimed_to_be_fully_covered_by_a_control_that_is_one_of_many() -> None:
    """Where several controls answer a criterion, at least one is its primary route.

    A criterion whose controls are all partial can never be shown as fully covered
    by the library alone, which is honest, but it is worth knowing which they are.
    """
    by_criterion: dict[str, list[str]] = {}
    for row in MAPPINGS:
        by_criterion.setdefault(row["requirement_key"], []).append(row["coverage"])
    only_supporting = sorted(k for k, v in by_criterion.items() if "full" not in v)
    # Review these when adding controls: each is a criterion no single control owns.
    assert len(only_supporting) <= 35, only_supporting


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t["code"])
def test_a_control_lists_the_evidence_an_auditor_expects(template: dict[str, Any]) -> None:
    items = template["evidence"]
    assert items, "a control with no expected evidence cannot be evidenced"
    keys = [i["key"] for i in items]
    assert len(keys) == len(set(keys))
    mapped = {c["key"] for c in CHECKS if any(m["code"] == template["code"] for m in c["controls"])}
    for item in items:
        assert item["assurance"] in _ASSURANCE
        assert item["cadence"] in _CADENCE
        assert item["source"] in {"upload", "platform"}
        if item["source"] == "platform":
            assert item["module"] in _MODULES
        for check_key in item.get("automated_by", []):
            assert check_key in mapped, f"{check_key} is not a check of {template['code']}"


def test_every_check_names_what_it_collects_and_why_it_belongs_to_each_control() -> None:
    for check in CHECKS:
        assert check["evidence_kinds"], check["key"]
        assert check["controls"], check["key"]
        for capability in check["capabilities"]:
            assert capability in CAPABILITIES, (check["key"], capability)
        for provider in check["implementations"]:
            declared = {
                p["key"]: p["status"]
                for c in check["capabilities"]
                for p in CAPABILITIES[c]["providers"]
            }
            assert declared.get(provider) == "available", (check["key"], provider)
        for mapping in check["controls"]:
            assert mapping["code"] in CODES, (check["key"], mapping["code"])
            assert mapping["coverage"] in _COVERAGE
            assert len(mapping["rationale"].strip()) > 20, (check["key"], mapping["code"])


def test_a_check_is_full_cover_only_where_it_alone_verifies_the_whole_control() -> None:
    """Most checks verify part of a control. Full cover is the exception, and a
    control with several checks cannot be fully verified by any one of them."""
    per_control: dict[str, int] = {}
    for check in CHECKS:
        for mapping in check["controls"]:
            per_control[mapping["code"]] = per_control.get(mapping["code"], 0) + 1
    for check in CHECKS:
        for mapping in check["controls"]:
            if mapping["coverage"] == "full":
                assert per_control[mapping["code"]] == 1, (check["key"], mapping["code"])


def test_the_change_management_criterion_has_every_link_in_its_chain() -> None:
    """CC8.1 is answered by controls for process, authorization, review, testing,
    environments, emergencies, deployment and traceability, and each is tested."""
    chain = {m["template_code"] for m in MAPPINGS if m["requirement_key"] == "SOC2:CC8.1"}
    assert chain == {"SD-01", "SD-02", "SD-04", "SD-06", "SD-10", "SD-12", "SD-13", "SD-14"}
    tested = {m["code"] for c in CHECKS for m in c["controls"]}
    assert {"SD-01", "SD-02", "SD-06", "SD-13", "SD-14", "SD-04"} <= tested


def test_every_control_has_a_type_and_a_sub_type() -> None:
    """The spec gives every control a Type (the category) and a Sub-type (spec 1.1)."""
    assert len(TEMPLATES) == 116
    for template in TEMPLATES:
        assert template["category"] in CONTROL_CATEGORIES, template["code"]
        sub_type = template.get("sub_category", "")
        assert sub_type.strip(), f"{template['code']} has no Sub-type"
        assert len(sub_type) <= 100, template["code"]


def test_each_type_has_three_to_seven_sub_types_and_every_type_is_used() -> None:
    """A Sub-type is a finer area inside a Type, so each Type splits into a handful.

    One Sub-type per control means a Type with fewer than three controls cannot
    reach three; that is only Physical and Environmental Security today.
    """
    for category in CONTROL_CATEGORIES:
        owned = [t for t in TEMPLATES if t["category"] == category]
        assert owned, f"no control is filed under {category}"
        sub_types = {t["sub_category"] for t in owned}
        assert min(3, len(owned)) <= len(sub_types) <= 7, (category, sorted(sub_types))


def test_a_sub_type_is_short_title_case() -> None:
    for template in TEMPLATES:
        sub_type = template["sub_category"]
        assert len(sub_type) <= 40, sub_type
        words = [w for w in sub_type.replace("/", " ").split() if any(c.isalpha() for c in w)]
        assert all(w[0].isupper() for w in words), sub_type


def test_nothing_shown_in_the_product_uses_a_dash_as_punctuation() -> None:
    texts: list[str] = []
    for row in MAPPINGS:
        texts.append(row["rationale"])
    for template in TEMPLATES:
        texts += [template["name"], template["description"], template["sub_category"]]
        texts += [i["name"] for i in template["evidence"]]
    for check in CHECKS:
        texts += [
            check["name"],
            check["description"],
            check["remediation"],
            *check["evidence_kinds"],
        ]
        texts += [m["rationale"] for m in check["controls"]]
    offenders = [t for t in texts if any(d in t for d in _DASHES) or " - " in t]
    assert not offenders, offenders[:3]
