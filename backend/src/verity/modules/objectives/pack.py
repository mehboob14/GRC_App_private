"""The objectives pack: sealed content, read into memory once, never written to the database.

``artifacts.json`` is the artifact catalogue (what an auditor looks at, and where it can come
from); ``objectives.json`` lists each control's objectives. The pack is refused when an
objective names an artifact the catalogue does not hold (AO-1), when a control has no design
objective (AO-2), or when its letters are not in order.
"""

from __future__ import annotations

import json
import string
from functools import cache
from typing import Any, Final

from verity.modules.onboarding.owner_functions import FUNCTION_KEYS
from verity.seed.seal import CONTENT_ROOT, ContentError, verify_pack

PACK: Final = CONTENT_ROOT / "objectives"
METHODS: Final = frozenset({"examine", "interview", "observe", "test"})
ASSURANCE: Final = frozenset({"design", "operating"})


def validate(artifacts: list[dict[str, Any]], objectives: list[dict[str, Any]]) -> None:
    """Raise ContentError on the first rule the pack breaks."""
    keys = {a["key"] for a in artifacts}
    if len(keys) != len(artifacts):
        raise ContentError("objectives pack: duplicate artifact keys")
    seen: set[str] = set()
    for entry in objectives:
        code = entry["control"]
        if code in seen:
            raise ContentError(f"objectives pack: {code} listed twice")
        seen.add(code)
        items = entry["objectives"]
        if not any(o["assurance"] == "design" for o in items):
            raise ContentError(f"objectives pack: {code} has no design objective")
        for letter, objective in zip(string.ascii_uppercase, items, strict=False):
            if objective["code"] != f"{code}.{letter}":
                raise ContentError(f"objectives pack: {objective['code']} is out of order")
            if objective["assurance"] not in ASSURANCE:
                raise ContentError(f"objectives pack: {objective['code']} assurance")
            backed = False
            for method in objective["methods"]:
                if method["method"] not in METHODS:
                    raise ContentError(f"objectives pack: {objective['code']} method")
                unknown = set(method["artifacts"]) - keys
                if unknown:
                    raise ContentError(
                        f"objectives pack: {objective['code']} names unknown artifacts {unknown}"
                    )
                if method["method"] == "interview" and method.get("who") not in FUNCTION_KEYS:
                    raise ContentError(
                        f"objectives pack: {objective['code']} interview names nobody"
                    )
                backed = backed or (method["method"] != "interview" and bool(method["artifacts"]))
            if not backed:
                raise ContentError(f"objectives pack: {objective['code']} rests on interview alone")


@cache
def load() -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """``(artifacts by key, objectives by control code)``, after the seal check."""
    verify_pack(PACK)
    artifacts = json.loads((PACK / "artifacts.json").read_text(encoding="utf-8"))
    objectives = json.loads((PACK / "objectives.json").read_text(encoding="utf-8"))
    validate(artifacts, objectives)
    return (
        {a["key"]: a for a in artifacts},
        {e["control"]: e["objectives"] for e in objectives},
    )


@cache
def manifest() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((PACK / "MANIFEST.json").read_text(encoding="utf-8"))
    return data
