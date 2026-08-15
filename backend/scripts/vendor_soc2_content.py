"""Vendor the SOC 2 content pack from the grc-s prototype into verity/seed/content/soc2.

Reads the two prototype JSON files, normalises them into the four content files
Verity seeds from, and writes a MANIFEST with sha256 of every input and output.

Idempotent: same inputs + same date argument => byte-identical output.

    python backend/scripts/vendor_soc2_content.py 2026-08-15
"""

import hashlib
import json
import sys
from pathlib import Path

SRC_LIBRARY = Path("C:/Users/HP/OneDrive/Desktop/Platform/grc-s/backend/app/control_library.json")
SRC_CRITERIA = Path("C:/Users/HP/OneDrive/Desktop/Platform/grc-s/backend/data/soc2_controls.json")
OUT = Path(__file__).resolve().parents[1] / "src/verity/seed/content/soc2"

# The source framework description reads "(2017, rev. 2022)" - asserted below,
# so this string cannot silently drift away from what the source supports.
FRAMEWORK_VERSION = "2017 TSC (2022 revision)"

# Longest prefix first: PI before P, CC before C.
TSC_BY_PREFIX = [
    ("CC", "Security"),
    ("PI", "Processing Integrity"),
    ("A", "Availability"),
    ("C", "Confidentiality"),
    ("P", "Privacy"),
]


def trust_services_category(code: str) -> str:
    for prefix, category in TSC_BY_PREFIX:
        if code.startswith(prefix):
            return category
    raise AssertionError(f"no trust services category for {code!r}")


def split_description(text: str) -> tuple[str, str]:
    """'## Why? <why> ## How? <how>' -> (why, how), headings stripped."""
    why, sep, how = text.partition("## How?")
    assert sep, "missing '## How?' heading"
    why = why.replace("## Why?", "", 1).strip()
    assert "## " not in why, "unexpected extra heading in the Why prose"
    assert "## " not in how, "unexpected extra heading in the How prose"
    return why, how.strip()


def write_json(path: Path, payload: object) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(vendored_on: str) -> None:
    library = json.loads(SRC_LIBRARY.read_text(encoding="utf-8"))
    source = json.loads(SRC_CRITERIA.read_text(encoding="utf-8"))
    assert "2017" in source["description"], "criteria source is not the 2017 TSC"
    assert "2022" in source["description"], "criteria source is not the 2022 revision"

    framework = {
        "code": source["id"],
        "name": source["name"],
        "description": source["description"],
        "version": FRAMEWORK_VERSION,
    }

    # Field names match the columns in modules/compliance/models.py, so the loader
    # is a straight copy rather than a translation layer that can drift.
    requirements = [
        {
            "requirement_key": f"SOC2:{c['code']}",
            "code": c["code"],
            "category": c["category"],
            "name": c["name"],
            "trust_services_category": trust_services_category(c["code"]),
            # Security (the common criteria) is in scope for every SOC 2 report;
            # the other four categories are opted into per engagement.
            "is_always_in_scope": trust_services_category(c["code"]) == "Security",
        }
        for c in source["controls"]
    ]

    templates = []
    for item in library:
        why, how = split_description(item["description"])
        templates.append(
            {
                "code": item["key"],
                # The concept identity a second framework reuses instead of minting a
                # duplicate control (D7a). The grc-s slug already names the concept
                # ("mfa-enforced"), so it seeds canonical_key directly; a later pack
                # that ships the same concept under a different code points here.
                "canonical_key": item["key"],
                "name": item["name"],
                "category": item["category"],
                # The source ships MANDATORY/PREFERRED; every enum in this schema
                # is lower-case (active, pending, done), so normalise at the edge
                # rather than teaching the constraint a second convention.
                "importance": item["importance"].lower(),
                "description": why,
                "implementation_guidance": how,
                "control_type": item["category"],
            }
        )

    crosswalk = [
        {"template_code": item["key"], "requirement_key": f"SOC2:{m['code']}"}
        for item in library
        for m in item["mappings"]
        if m["framework"] == "SOC2"
    ]

    # --- checks: fail loudly rather than seed a broken pack -------------------
    requirement_keys = {r["requirement_key"] for r in requirements}
    template_codes = {t["code"] for t in templates}
    assert len(requirement_keys) == len(requirements) == 61
    assert len(template_codes) == len(templates) == 114
    assert all(
        not t[f].startswith("#")
        for t in templates
        for f in ("description", "implementation_guidance")
    )
    assert all(t["description"] and t["implementation_guidance"] for t in templates)
    for pair in crosswalk:
        assert pair["requirement_key"] in requirement_keys, pair
        assert pair["template_code"] in template_codes, pair
    assert len({(p["template_code"], p["requirement_key"]) for p in crosswalk}) == len(crosswalk)
    assert {p["requirement_key"] for p in crosswalk} == requirement_keys, "gap in coverage"

    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        "framework.json": framework,
        "requirements.json": requirements,
        "control_templates.json": templates,
        "template_requirements.json": crosswalk,
    }
    for name, payload in files.items():
        write_json(OUT / name, payload)

    write_json(
        OUT / "MANIFEST.json",
        {
            "note": (
                f"Vendored from the grc-s prototype on {vendored_on} by "
                "backend/scripts/vendor_soc2_content.py; re-run it to regenerate."
            ),
            "vendored_on": vendored_on,
            "sources": [{"path": str(p), "sha256": sha256(p)} for p in (SRC_LIBRARY, SRC_CRITERIA)],
            "generated": [{"path": name, "sha256": sha256(OUT / name)} for name in files],
            "counts": {
                "frameworks": 1,
                "requirements": len(requirements),
                "control_templates": len(templates),
                "template_requirements": len(crosswalk),
            },
        },
    )
    print(f"wrote {len(files) + 1} files to {OUT}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: vendor_soc2_content.py <YYYY-MM-DD>")
    main(sys.argv[1])
