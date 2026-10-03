"""The shipped SOC 2 crosswalk: complete, and in step with the migration that corrects it.

The control library arrived from the prototype with its criterion mappings
unvalidated. Reading them against the AICPA points of focus corrected fourteen
(``20261003_1100_soc2_mapping_corrections``). These tests keep that work from
quietly regressing: every criterion has a control, every control answers a
criterion, and the migration's idea of "what we ship now" is what the content
pack actually ships.
"""

from __future__ import annotations

import importlib.util
import json
from collections import defaultdict
from pathlib import Path
from types import ModuleType

import pytest

import verity

_CONTENT = Path(verity.__file__).parent / "seed" / "content" / "soc2"
_MIGRATIONS = Path(verity.__file__).parent / "db" / "migrations" / "versions"


def _load(name: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = json.loads((_CONTENT / name).read_text(encoding="utf-8"))
    return rows


def _shipped() -> dict[str, set[str]]:
    by_template: dict[str, set[str]] = defaultdict(set)
    for row in _load("template_requirements.json"):
        by_template[row["template_code"]].add(row["requirement_key"].split(":")[1])
    return by_template


def _migration() -> ModuleType:
    path = next(_MIGRATIONS.glob("*_soc2_mapping_corrections.py"))
    spec = importlib.util.spec_from_file_location("soc2_mapping_corrections", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_criterion_has_at_least_one_control() -> None:
    criteria = {row["requirement_key"] for row in _load("requirements.json")}
    mapped = {row["requirement_key"] for row in _load("template_requirements.json")}
    assert criteria == mapped, f"criteria with no control: {sorted(criteria - mapped)}"


def test_every_control_answers_at_least_one_criterion() -> None:
    templates = {row["code"] for row in _load("control_templates.json")}
    assert templates == set(_shipped()), (
        f"controls mapped to nothing: {sorted(templates - set(_shipped()))}"
    )


def test_the_mapping_has_no_duplicates() -> None:
    rows = [(r["requirement_key"], r["template_code"]) for r in _load("template_requirements.json")]
    assert len(rows) == len(set(rows))


def test_the_migration_carries_exactly_what_the_pack_ships() -> None:
    shipped = _shipped()
    for code, (_before, after) in _migration().CHANGES.items():
        assert shipped[code] == set(after), code


@pytest.mark.parametrize(
    ("control", "criterion", "reason"),
    [
        ("SD-11", "CC6.1", "a committed credential is a failure to protect credentials"),
        ("SD-11", "CC7.1", "a secret in a change is a vulnerability that change introduced"),
        ("LM-01", "CC6.1", "CC6.1 starts with the inventory of information assets"),
        ("HR-01", "CC1.4", "CC1.4 lists considering the background of individuals"),
        ("SD-06", "CC8.1", "peer review of changes is the change criterion"),
    ],
)
def test_the_mappings_an_auditor_would_check_first_are_present(
    control: str, criterion: str, reason: str
) -> None:
    assert criterion in _shipped()[control], reason


def test_secret_scanning_is_not_filed_under_malicious_software() -> None:
    """CC6.8 is about unauthorized or malicious *software*. A secret is not one."""
    assert "CC6.8" not in _shipped()["SD-11"]
