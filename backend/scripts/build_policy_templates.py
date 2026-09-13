"""Turn the Openlane policy-hub markdown into a shipped content pack.

Run once, by hand, when the upstream templates change:

    uv run --with markdown python scripts/build_policy_templates.py \
        --source C:/Users/HP/Documents/policies_templates/policy-hub

``markdown`` is a BUILD-TIME tool only — it is deliberately not a project
dependency. The HTML it produces is committed under ``seed/content/``, reviewed
in the diff like any other shipped content, and loaded by the ordinary seed
loader. Nothing converts markdown at runtime.

Provenance matters here. These policies are third-party content under Apache 2.0,
which permits commercial use and redistribution but requires the licence, the
attribution, and a statement of changes. Every row carries its source repository,
commit and licence so the platform can show a customer where its policy text came
from, and NOTICE records the modification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from verity.modules.documents import placeholders as placeholder_lib

SOURCE_REPO = "https://github.com/theopenlane/policy-hub"
LICENSE = "Apache-2.0"

#: `{{company_name}}` is the tenant's own name and is filled in automatically on
#: instantiation. The rest are genuine decisions the customer has to make, so
#: they are left in place and surfaced for editing.
AUTO_FILLED = {"company_name"}

#: Editorial markers in the upstream text — "[Optional]" and friends. Not fields
#: to fill, but a decision to keep or cut, so they are counted separately.
_OPTIONAL = re.compile(r"\[Optional[^\]]*\]")

_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

#: The picker card and the register show a short description of what each policy
#: covers. The upstream files open with the policy's own first paragraph, which is
#: long, full of {{placeholders}} and reads as policy text rather than a summary,
#: so the descriptions are written here and win over the extracted sentence.
SUMMARIES: dict[str, str] = {
    "access-control-policy": (
        "Who can access which systems and data, and how access is granted, reviewed and removed."
    ),
    "asset-management-policy": (
        "Keeps an inventory of company assets and gives each one an owner responsible for "
        "protecting it."
    ),
    "business-continuity-and-disaster-recovery-plan": (
        "How the business keeps running and restores systems and data after an outage or disaster."
    ),
    "code-of-conduct": (
        "The standards of behaviour expected from everyone who works for or with the company."
    ),
    "cryptography-policy": (
        "When encryption must be used to protect data, and how encryption keys are managed."
    ),
    "data-management-policy": (
        "How data is classified, handled, kept and securely disposed of based on how sensitive "
        "it is."
    ),
    "human-resource-security-policy": (
        "Security steps before, during and after employment, from background checks and "
        "training to offboarding."
    ),
    "incident-response-plan": (
        "How security incidents are reported, investigated, contained and closed, and who is "
        "responsible for each step."
    ),
    "information-security-policy": (
        "The company's overall approach to protecting information and the security rules every "
        "employee follows."
    ),
    "information-security-roles-and-responsibilities": (
        "Who is responsible for information security and what each role is accountable for."
    ),
    "operations-security-policy": (
        "Keeps production systems running securely through change control, monitoring, backups "
        "and patching."
    ),
    "physical-security-policy": (
        "Protects offices, equipment and facilities from unauthorised access, damage and theft."
    ),
    "risk-management-policy": (
        "How security risks are identified, assessed, treated and reviewed on a regular schedule."
    ),
    "secure-development-policy": (
        "Builds security into software development, from design and code review to testing and "
        "release."
    ),
    "third-party-management-policy": (
        "How vendors that handle company data or systems are assessed, contracted and monitored."
    ),
}


def _frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse the small, regular YAML subset these files use, without pulling in
    a YAML dependency for four keys."""
    match = _FRONTMATTER.match(text)
    if not match:
        return {}, text
    body = text[match.end() :]
    meta: dict[str, Any] = {}
    section: str | None = None
    framework: str | None = None
    for raw in match.group(1).splitlines():
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if line.startswith("- "):
            value = line[2:].strip()
            if section == "satisfies" and framework:
                meta.setdefault("satisfies", {}).setdefault(framework, []).append(value)
            elif section:
                meta.setdefault(section, []).append(value)
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if indent == 0:
            section = key
            framework = None
            if value:
                meta[key] = value
        elif section == "satisfies":
            framework = key
            meta.setdefault("satisfies", {}).setdefault(framework, [])
    return meta, body


def _summary(html: str) -> str:
    """The first real sentence, for the picker card."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    # Skip the "Purpose" heading itself.
    text = re.sub(r"^Purpose\s*", "", text, flags=re.IGNORECASE)
    return (text[:240].rstrip() + "…") if len(text) > 240 else text


def _slug(path: Path) -> str:
    return path.stem.lower()


def build(source: Path, out: Path) -> int:
    # Build-time only, never imported at runtime.
    import markdown

    templates_dir = source / "templates"
    if not templates_dir.is_dir():
        print(f"no templates/ under {source}", file=sys.stderr)
        return 1

    try:
        commit = subprocess.run(  # noqa: S603 — fixed args, local repo
            ["git", "-C", str(source), "rev-parse", "HEAD"],  # noqa: S607 — git off PATH
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:  # pragma: no cover - provenance is best effort
        commit = "unknown"

    rows: list[dict[str, Any]] = []
    for path in sorted(templates_dir.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = _frontmatter(raw)
        title = str(meta.get("title") or path.stem.replace("-", " ").title())

        html = markdown.markdown(
            body,
            extensions=["tables", "sane_lists", "attr_list", "md_in_html"],
            output_format="html",
        )

        # The same detection the documents use, so the picker's count and the
        # editor's checklist agree about what is left to fill in.
        placeholders = [
            {
                "key": p.key,
                "label": p.label,
                "kind": p.kind,
                "count": p.count,
                "auto_filled": p.key in AUTO_FILLED,
            }
            for p in placeholder_lib.find(html)
        ]

        satisfies = meta.get("satisfies") or {}
        rows.append(
            {
                "key": _slug(path),
                "title": title,
                # Every file in this pack is a policy or a plan; both are
                # governed documents that a person approves, which is what
                # "policy" means in DOC_TYPES.
                "doc_type": "policy",
                "classification": "internal",
                "tags": meta.get("tags") or [],
                "satisfies": satisfies,
                "summary": SUMMARIES.get(_slug(path)) or _summary(html),
                "content_html": html,
                "placeholders": placeholders,
                "optional_markers": len(_OPTIONAL.findall(body)),
                "word_count": len(body.split()),
                "source": "openlane-policy-hub",
                "source_url": f"{SOURCE_REPO}/blob/{commit}/templates/{path.name}",
                "source_commit": commit,
                "license": LICENSE,
            }
        )

    out.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
    (out / "document_templates.json").write_text(payload, encoding="utf-8")

    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    manifest = {
        "counts": {"document_templates": len(rows)},
        "source": {
            "repository": SOURCE_REPO,
            "commit": commit,
            "license": LICENSE,
            "retrieved_for": "policy template library",
            "modifications": (
                "Markdown converted to HTML; YAML frontmatter lifted into columns; "
                "{{placeholder}} tokens and written <prompts> catalogued; each template's "
                "summary written for the platform as a short description. The policy text "
                "itself is unaltered."
            ),
        },
        "generated": [{"path": "document_templates.json", "sha256": digest}],
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    total_ph = sum(p["count"] for r in rows for p in r["placeholders"])
    print(f"{len(rows)} templates -> {out}")
    print(f"  {total_ph} placeholder occurrences, {sum(r['word_count'] for r in rows)} words")
    print(f"  source {commit[:12]} ({LICENSE})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="the policy-hub clone")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "src/verity/seed/content/policies",
    )
    args = parser.parse_args()
    return build(args.source.resolve(), args.out.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
