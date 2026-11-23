"""Every shipped control has an owner function (guided onboarding CL-8)."""

from __future__ import annotations

import json
from pathlib import Path

from verity.modules.documents.required_documents import REQUIRED, controls_for_template
from verity.modules.onboarding.owner_functions import FUNCTION_KEYS, function_for

CONTENT = Path(__file__).resolve().parents[2] / "src" / "verity" / "seed" / "content"


def _codes() -> list[str]:
    codes: list[str] = []
    for pack in ("soc2", "iso27001"):
        rows = json.loads((CONTENT / pack / "control_templates.json").read_text(encoding="utf-8"))
        codes.extend(row["code"] for row in rows)
    return codes


def test_every_shipped_control_resolves_to_a_function() -> None:
    missing = [code for code in _codes() if function_for(code) not in FUNCTION_KEYS]
    assert missing == []


def test_the_internal_audit_is_not_owned_by_the_security_lead() -> None:
    assert function_for("GOV-13") == "executive_sponsor"


def test_required_documents_name_only_shipped_controls_and_templates() -> None:
    codes = set(_codes())
    keys = {
        row["key"]
        for row in json.loads(
            (CONTENT / "policies" / "document_templates.json").read_text(encoding="utf-8")
        )
    }
    for item in REQUIRED:
        assert set(item.controls) <= codes, item.title
        if item.kind == "template":
            assert item.template in keys, f"{item.title}: {item.template} is not shipped"
    assert "IAM-01" in controls_for_template("access-control-policy")
