"""The Statement of Applicability as a workbook an auditor can open without Verity.

Pure: it takes plain values and returns bytes, so it needs no session and a unit test can
read the workbook back. The service decides what is in each row; this decides how it looks.
"""

from __future__ import annotations

import io
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Final

SOA_COLUMNS: Final[tuple[tuple[str, str, int], ...]] = (
    ("reference", "Reference", 11),
    ("title", "Requirement", 38),
    ("section", "Section", 22),
    ("applicable", "Applicable", 11),
    ("justification", "Justification", 46),
    ("provided_by", "Operated by", 14),
    ("implementation", "Implementation", 16),
    ("controls", "Controls", 26),
    ("owner", "Owner", 20),
    ("reviewed", "Last reviewed", 14),
)

_HEADER_FILL: Final = "1F2A44"
_EXCLUDED_FILL: Final = "F3F4F6"


def build_soa_workbook(
    *,
    framework_name: str,
    version: str,
    scope_statement: str | None,
    generated_on: date,
    rows: Sequence[Mapping[str, str]],
) -> bytes:
    """One sheet: a short header, the scope statement, then one row per requirement."""
    from openpyxl import Workbook  # noqa: PLC0415 — only an export needs it
    from openpyxl.styles import Alignment, Font, PatternFill  # noqa: PLC0415
    from openpyxl.utils import get_column_letter  # noqa: PLC0415

    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None  # noqa: S101 — a new workbook always has one sheet
    sheet.title = "Statement of Applicability"

    sheet.cell(row=1, column=1, value="Statement of Applicability").font = Font(bold=True, size=14)
    sheet.cell(
        row=2, column=1, value=f"{framework_name} {version}, generated {generated_on.isoformat()}"
    ).font = Font(color="6B7280")
    sheet.cell(row=3, column=1, value="Scope").font = Font(bold=True)
    scope = sheet.cell(row=3, column=2, value=scope_statement or "Not written yet")
    scope.alignment = Alignment(wrap_text=True, vertical="top")
    sheet.merge_cells(start_row=3, start_column=2, end_row=3, end_column=len(SOA_COLUMNS))
    sheet.row_dimensions[3].height = max(30, 15 * (1 + len(scope_statement or "") // 110))

    header_row = 5
    for index, (_key, label, width) in enumerate(SOA_COLUMNS, start=1):
        cell = sheet.cell(row=header_row, column=index, value=label)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=_HEADER_FILL)
        cell.alignment = Alignment(vertical="center")
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.row_dimensions[header_row].height = 22

    for offset, row in enumerate(rows, start=1):
        excluded = row.get("applicable") == "No"
        for index, (key, _label, _width) in enumerate(SOA_COLUMNS, start=1):
            cell = sheet.cell(row=header_row + offset, column=index, value=row.get(key, ""))
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if excluded:
                cell.fill = PatternFill("solid", fgColor=_EXCLUDED_FILL)

    sheet.freeze_panes = sheet.cell(row=header_row + 1, column=2)
    last = header_row + max(1, len(rows))
    sheet.auto_filter.ref = f"A{header_row}:{get_column_letter(len(SOA_COLUMNS))}{last}"

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
