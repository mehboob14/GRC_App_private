"""Profile fields in documents: filled when known, a visible marker when not (PR-8)."""

from __future__ import annotations

from verity.modules.documents.placeholders import fill_profile, markers


def test_missing_profile_fields_become_markers_and_others_stay() -> None:
    html = "<p>{{legal_name}} at {{registered_address}} reviews {{frequency}}.</p>"
    out = fill_profile(html, {"legal_name": "Acme Ltd", "registered_address": None})
    assert out == "<p>Acme Ltd at [Add your registered address] reviews {{frequency}}.</p>"
    assert markers(out) == ["[Add your registered address]"]
    assert markers("<p>Done.</p>") == []
