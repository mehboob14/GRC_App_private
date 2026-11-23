"""The content seal: a pack's files must match the hashes its MANIFEST.json vouches for.

Kept apart from the loader so code that only reads a sealed pack into memory (the country
reference panel) checks the seal without importing every module's models.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

CONTENT_ROOT = Path(__file__).parent / "content"


class ContentError(ValueError):
    """A content pack that must not be loaded: it does not match what was reviewed."""


def content_digest(path: Path) -> str:
    """SHA256 of a content file with line endings normalised to LF."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def sealed_hashes(pack: Path) -> dict[str, str]:
    """The file hashes a pack's manifest vouches for: ``{file name: sha256}``."""
    manifest_path = pack / "MANIFEST.json"
    if not manifest_path.exists():
        return {}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sealed = {item["path"]: item["sha256"] for item in manifest.get("generated", [])}
    sealed.update(manifest.get("sha256", {}))
    return sealed


def verify_pack(pack: Path) -> None:
    """Refuse a pack whose files differ from the bytes its manifest sealed."""
    for name, expected in sealed_hashes(pack).items():
        if not (pack / name).exists() or content_digest(pack / name) != expected:
            raise ContentError(
                f"{pack.name}/{name} does not match its MANIFEST.json hash. "
                "Content changes are sealed in the same reviewed change "
                "(python scripts/seal_content.py)."
            )
