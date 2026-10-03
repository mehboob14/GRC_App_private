"""Seal the content packs: write each pack's file hashes (and counts) into its MANIFEST.json.

The loader refuses a pack whose files no longer match the hashes in its manifest, so a
content change and its new hashes travel in the same reviewed change. Run this after
editing anything under ``src/verity/seed/content`` and commit the manifests with it::

    cd backend
    python scripts/seal_content.py          # rewrite the manifests
    python scripts/seal_content.py --check  # fail if any manifest is out of date

Hashes are taken with line endings normalised, so they are the same on a Windows
checkout as on the server.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from verity.seed.loader import CONTENT_ROOT, content_digest, sealed_hashes


def _json(pack: Path, name: str) -> list[dict]:
    return json.loads((pack / name).read_text(encoding="utf-8"))


def _counts(pack: Path) -> dict[str, int]:
    """The numbers a manifest states about its pack, where it states any."""
    out: dict[str, int] = {}
    if pack.name == "soc2":
        out = {
            "requirements": len(_json(pack, "requirements.json")),
            "control_templates": len(_json(pack, "control_templates.json")),
            "template_requirements": len(_json(pack, "template_requirements.json")),
        }
    elif pack.name == "automation":
        checks = _json(pack, "checks.json")
        out = {
            "capabilities": len(_json(pack, "capabilities.json")),
            "checks": len(checks),
            "controls_mapped": len({m["code"] for c in checks for m in c["controls"]}),
        }
    return out


def seal(pack: Path) -> bool:
    """Rewrite one manifest; return whether it changed."""
    path = pack / "MANIFEST.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    before = json.dumps(manifest, sort_keys=True)
    for item in manifest.get("generated", []):
        item["sha256"] = content_digest(pack / item["path"])
    if "sha256" in manifest:
        manifest["sha256"] = {name: content_digest(pack / name) for name in manifest["sha256"]}
    counts = _counts(pack)
    if pack.name == "soc2":
        manifest["counts"] = {**manifest.get("counts", {}), **counts}
    else:
        manifest.update({k: v for k, v in counts.items() if k in manifest})
    if json.dumps(manifest, sort_keys=True) == before:
        return False
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def main() -> int:
    check = "--check" in sys.argv
    stale = []
    for pack in sorted(p for p in CONTENT_ROOT.iterdir() if p.is_dir()):
        if not (pack / "MANIFEST.json").exists():
            continue
        if check:
            if any(content_digest(pack / n) != h for n, h in sealed_hashes(pack).items()):
                stale.append(pack.name)
        elif seal(pack):
            print(f"sealed {pack.name}")
    if stale:
        print("out of date: " + ", ".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
