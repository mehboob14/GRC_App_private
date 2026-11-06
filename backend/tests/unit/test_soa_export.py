"""The Statement of Applicability workbook, read back the way an auditor would open it."""

from __future__ import annotations

import io
from datetime import date

from openpyxl import load_workbook

from verity.modules.compliance.models import (
    AUDIT_TYPES,
    AUDIT_TYPES_BY_SCOPE_MODEL,
    SCOPE_MODELS,
    natural_key,
)
from verity.modules.compliance.soa_export import SOA_COLUMNS, build_soa_workbook


def _row(code: str, applicable: str, **extra: str) -> dict[str, str]:
    base = {
        "reference": code,
        "title": f"Requirement {code}",
        "section": "Annex A Physical",
        "applicable": applicable,
        "justification": "",
        "provided_by": "Organization",
        "implementation": "Implemented",
        "controls": "PE-02",
        "owner": "",
        "reviewed": "",
    }
    return {**base, **extra}


def test_the_workbook_carries_the_scope_every_decision_and_its_reason() -> None:
    data = build_soa_workbook(
        framework_name="ISO 27001",
        version="2022",
        scope_statement="The hosted product and the team that runs it.",
        generated_on=date(2026, 10, 10),
        rows=[
            _row("A.7.1", "Yes", provided_by="Supplier"),
            _row(
                "A.7.6",
                "No",
                justification="Fully remote team, no secure areas.",
                implementation="Not needed",
            ),
        ],
    )
    sheet = load_workbook(io.BytesIO(data)).active
    assert sheet is not None
    assert sheet["A1"].value == "Statement of Applicability"
    subtitle = str(sheet["A2"].value)
    assert "ISO 27001 2022" in subtitle
    assert "2026-10-10" in subtitle
    assert sheet["B3"].value == "The hosted product and the team that runs it."
    header = [sheet.cell(row=5, column=i + 1).value for i in range(len(SOA_COLUMNS))]
    assert header == [label for _key, label, _width in SOA_COLUMNS]
    assert [sheet.cell(row=6, column=i).value for i in (1, 4, 6)] == ["A.7.1", "Yes", "Supplier"]
    assert [sheet.cell(row=7, column=i).value for i in (1, 4, 5)] == [
        "A.7.6",
        "No",
        "Fully remote team, no secure areas.",
    ]
    # An excluded row is shaded so it reads at a glance; an applicable one is not.
    assert sheet.cell(row=7, column=1).fill.fgColor.rgb.endswith("F3F4F6")
    assert sheet.cell(row=6, column=1).fill.fgColor.rgb in (None, "00000000")
    assert sheet.auto_filter.ref == "A5:J7"


def test_an_empty_scope_says_so_rather_than_leaving_a_blank() -> None:
    data = build_soa_workbook(
        framework_name="ISO 27001",
        version="2022",
        scope_statement=None,
        generated_on=date(2026, 10, 10),
        rows=[],
    )
    sheet = load_workbook(io.BytesIO(data)).active
    assert sheet is not None
    assert sheet["B3"].value == "Not written yet"


def test_requirement_codes_sort_the_way_a_person_reads_them() -> None:
    codes = ["A.5.10", "A.5.2", "10.1", "4.1", "A.8.9", "A.8.10"]
    assert sorted(codes, key=natural_key) == ["4.1", "10.1", "A.5.2", "A.5.10", "A.8.9", "A.8.10"]


def test_each_scope_model_has_its_own_audits_and_none_overlap() -> None:
    assert set(AUDIT_TYPES_BY_SCOPE_MODEL) == set(SCOPE_MODELS)
    assert AUDIT_TYPES_BY_SCOPE_MODEL["categories"] == ("type_1", "type_2")
    assert "surveillance" in AUDIT_TYPES_BY_SCOPE_MODEL["applicability"]
    assert len(AUDIT_TYPES) == len(set(AUDIT_TYPES)) == 5
