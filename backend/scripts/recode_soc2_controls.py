"""Re-code the 114 shipped SOC 2 control templates to category-based codes.

Rewrites `control_templates.json` (`code`) and `template_requirements.json`
(`template_code`) in place, leaving `canonical_key` — the stable identity the
pack was authored against — untouched. Codes are `<CATEGORY_ABBR>-<NN>`,
numbered within each category by canonical_key so the result is deterministic:
re-running produces the same codes.

    # from backend/, venv active
    python -m scripts.recode_soc2_controls          # writes the mapping + files
    python -m scripts.recode_soc2_controls --dry-run

The tenant-side rename (already-adopted `controls.code`) is a migration, not
this script — see the Alembic revision that carries the same mapping.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

PACK = Path(__file__).resolve().parents[1] / "src" / "verity" / "seed" / "content" / "soc2"

# One short, stable abbreviation per control category. Chosen to not collide
# with the SOC 2 *criteria* prefixes (CC / A / C / PI / P), which appear beside
# these codes in the UI — a control code must never read as a criterion.
CATEGORY_ABBR: dict[str, str] = {
    "Business Continuity & Third-Party Management": "BC",
    "Communications & Collaboration Security": "CS",
    "Data Management & Privacy": "DM",
    "Endpoint Security": "EP",
    "Governance, Risk & Compliance": "GRC",
    "Human Resources & Personnel Security": "HR",
    "Identity & Access Management": "IAM",
    "Infrastructure & Network Security": "NS",
    "Logging, Monitoring & Incident Management": "LM",
    "Physical & Environmental Security": "PE",
    "Secure Development & Code Management": "SD",
}


def _read(name: str) -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = json.loads((PACK / name).read_text(encoding="utf-8"))
    return data


def _write(name: str, doc: object) -> None:
    (PACK / name).write_text(
        json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_mapping(templates: list[dict[str, Any]]) -> dict[str, str]:
    """canonical_key -> new code. Deterministic: sorted within each category."""
    unknown = sorted({t["category"] for t in templates} - CATEGORY_ABBR.keys())
    if unknown:
        raise SystemExit(f"no abbreviation for categories: {unknown}")

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for template in templates:
        groups[template["category"]].append(template)

    mapping: dict[str, str] = {}
    for category, items in groups.items():
        for index, template in enumerate(sorted(items, key=lambda t: t["canonical_key"]), start=1):
            mapping[template["canonical_key"]] = f"{CATEGORY_ABBR[category]}-{index:02d}"

    if len(set(mapping.values())) != len(mapping):
        raise SystemExit("generated codes are not unique")
    return mapping


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    templates = _read("control_templates.json")
    crosswalk = _read("template_requirements.json")

    mapping = build_mapping(templates)
    # old code -> new code, for the crosswalk and the tenant migration
    by_old = {t["code"]: mapping[t["canonical_key"]] for t in templates}

    for template in templates:
        template["code"] = mapping[template["canonical_key"]]
    for row in crosswalk:
        row["template_code"] = by_old[row["template_code"]]

    print(f"{len(mapping)} templates re-coded, {len(crosswalk)} crosswalk rows rewritten")
    for old, new in sorted(by_old.items(), key=lambda kv: kv[1])[:8]:
        print(f"  {old:28s} -> {new}")
    print("  …")

    if dry_run:
        print("dry run — nothing written")
        return

    _write("control_templates.json", templates)
    _write("template_requirements.json", crosswalk)
    # Emitted for the Alembic revision, so the tenant rename uses the same map.
    _write("_recode_map.json", by_old)
    print("wrote control_templates.json, template_requirements.json, _recode_map.json")


if __name__ == "__main__":
    main()
