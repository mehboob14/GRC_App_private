"""Reading evidence files for the AI, and the maturity judgement it returns (drafts, rule 11)."""

from __future__ import annotations

import asyncio
import io
import zipfile
from types import SimpleNamespace
from typing import Any

import pytest

from verity.modules.ai import mapping
from verity.modules.evidence.text import extract_text

CONTROL = mapping.ControlCandidate("c1", "SD-11", "Secret scanning", "Scan for secrets.", ["CC6.1"])
EVIDENCE = mapping.EvidenceContext("Scan report", "weekly", "log_export", text="0 secrets found")


def test_text_json_and_word_files_are_read_and_a_scan_is_not() -> None:
    assert extract_text(b"hello", "text/plain", "a.txt") == "hello"
    docx = io.BytesIO()
    with zipfile.ZipFile(docx, "w") as z:
        z.writestr("word/document.xml", "<w:p><w:t>Access review</w:t></w:p>")
    assert "Access review" in extract_text(docx.getvalue(), "application/octet-stream", "r.docx")
    assert extract_text(b"%PDF-1.4", "application/pdf", "scan.pdf") == ""
    assert extract_text(b"x" * 6_000_000, "text/plain", "big.txt") == ""


def test_no_model_key_means_no_invented_score(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mapping, "get_settings", lambda: SimpleNamespace(ai=SimpleNamespace(api_key=None))
    )
    assert asyncio.run(mapping.assess_maturity(EVIDENCE, CONTROL)) is None


def test_a_model_answer_is_clamped_and_unknown_verdicts_read_as_partly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Model:
        async def ainvoke(self, _messages: Any) -> Any:  # noqa: ANN401
            reply = '{"maturity": 140, "verdict": "great", "summary": "ok", "gaps": ["undated"],'
            reply += ' "requirements": [{"code": "CC6.1", "verdict": "partly", "note": "n"}]}'
            return SimpleNamespace(content="```json\n" + reply + "\n```")

    monkeypatch.setattr(
        mapping, "get_settings", lambda: SimpleNamespace(ai=SimpleNamespace(api_key="k"))
    )
    monkeypatch.setattr("verity.modules.ai.llm.get_chat_model", Model)
    result = asyncio.run(mapping.assess_maturity(EVIDENCE, CONTROL))
    assert result is not None
    assert (result.maturity, result.verdict, result.gaps) == (100, "partly", ["undated"])
    assert result.requirements[0]["code"] == "CC6.1"
