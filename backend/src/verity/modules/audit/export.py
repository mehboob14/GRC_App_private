"""The audit trail as a file: the cell rules, the CSV stream and the Excel workbook.

Formatting only, with no database and no HTTP. ``AuditService.export_batches`` supplies
the rows, ``events`` turns them into the events the list shows, and the router wraps what
comes out. Both formats take their cells from ``row_cells``, so a CSV and a workbook of
the same range agree to the character.
"""

from __future__ import annotations

import asyncio
import codecs
import csv
import io
from collections.abc import AsyncIterator, Iterable, Sequence
from typing import Any, Final

import orjson
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from verity.modules.audit.schemas import AuditLogEntry, iso_utc_z
from verity.modules.audit.service import ExportBatch, ExportRun

HEADERS: Final[tuple[str, ...]] = (
    "occurred_at",
    "actor",
    "actor_type",
    "actor_id",
    "action",
    "object_type",
    "object",
    "object_id",
    "before",
    "after",
)

# A spreadsheet runs a cell that starts with one of these as a formula.
_FORMULA_PREFIXES: Final = ("=", "+", "-", "@", "\t", "\r")


def neutralise_cell(value: str) -> str:
    """Make a text cell inert. A leading apostrophe turns it back into plain text in
    Excel and Sheets. Names in the trail are typed by users and end up in a file that
    an auditor opens in a spreadsheet, so every text cell passes through here."""
    return f"'{value}" if value.startswith(_FORMULA_PREFIXES) else value


def _json_text(snapshot: dict[str, Any] | None) -> str:
    # Sorted keys: the same snapshot reads the same in every export.
    return "" if snapshot is None else orjson.dumps(snapshot, option=orjson.OPT_SORT_KEYS).decode()


def row_cells(entry: AuditLogEntry) -> list[str]:
    return [
        neutralise_cell(value)
        for value in (
            iso_utc_z(entry.occurred_at),
            entry.actor_label,
            entry.actor_type,
            "" if entry.actor_id is None else str(entry.actor_id),
            entry.action,
            entry.object_type,
            entry.object_label,
            str(entry.object_id),
            _json_text(entry.before),
            _json_text(entry.after),
        )
    ]


async def events(batches: AsyncIterator[ExportBatch]) -> AsyncIterator[list[AuditLogEntry]]:
    """The batches as the events the list shows, with their names."""
    async for rows, names in batches:
        yield [AuditLogEntry.labelled(row, names) for row in rows]


def _csv_bytes(rows: Iterable[Sequence[str]]) -> bytes:
    buffer = io.StringIO()
    csv.writer(buffer).writerows(rows)
    return buffer.getvalue().encode()


async def csv_stream(batches: AsyncIterator[list[AuditLogEntry]]) -> AsyncIterator[bytes]:
    """The header and then one chunk per batch, so the file is never held whole."""
    # The byte order mark is what tells Excel the file is UTF-8, so an accented name is
    # not mangled. The risk register's CSV carries it for the same reason.
    yield codecs.BOM_UTF8 + _csv_bytes([HEADERS])
    async for batch in batches:
        yield _csv_bytes(row_cells(entry) for entry in batch)


_HEADER_FILL: Final = "1F2A44"
_COLUMN_WIDTHS: Final = (27, 24, 16, 38, 12, 18, 28, 38, 50, 50)
_XLSX_CELL_LIMIT: Final = 32_767
_CUT_NOTE: Final = " [cut: export CSV for the full text]"


def _xlsx_text(value: str) -> str:
    """What a worksheet cell will accept. openpyxl refuses control characters outright,
    which would fail the whole file over one stray character in a name, and it cuts a
    cell at Excel's limit without saying so, which would change what was recorded
    without telling the reader. So the characters go, and a cut says that it is one."""
    value = ILLEGAL_CHARACTERS_RE.sub("", value)
    if len(value) > _XLSX_CELL_LIMIT:
        value = value[: _XLSX_CELL_LIMIT - len(_CUT_NOTE)] + _CUT_NOTE
    return value


def _append_rows(sheet: Any, entries: Sequence[AuditLogEntry]) -> None:  # noqa: ANN401 — openpyxl is untyped
    for entry in entries:
        sheet.append([_xlsx_text(cell) for cell in row_cells(entry)])


def _export_details(run: ExportRun, rows: int) -> list[tuple[str, str | int]]:
    request = run.request
    stamp = iso_utc_z(run.cut_off)
    first = "Not set" if request.date_from is None else request.date_from.isoformat()
    last = "Not set" if request.date_to is None else request.date_to.isoformat()
    return [
        ("Export id", str(run.export_id)),
        ("Exported by", run.actor_label),
        ("Exported at (UTC)", stamp),
        ("Cut-off (UTC)", stamp),
        ("From (UTC day)", first),
        ("To (UTC day)", last),
        ("Include system activity", "Yes" if request.include_system else "No"),
        ("Object type", request.object_type or "All"),
        ("Rows", rows),
    ]


def _finish(workbook: Any, sheet: Any, run: ExportRun, rows: int) -> bytes:  # noqa: ANN401
    # Set last: only now is the row count known, and a write-only sheet writes its
    # filter after its rows.
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(HEADERS))}{rows + 1}"
    details = workbook.create_sheet("Export")
    details.column_dimensions["A"].width = 30
    details.column_dimensions["B"].width = 64
    for label, value in _export_details(run, rows):
        key = WriteOnlyCell(details, value=label)
        key.font = Font(bold=True)
        text = _xlsx_text(neutralise_cell(value)) if isinstance(value, str) else value
        details.append([key, text])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


async def build_xlsx(batches: AsyncIterator[list[AuditLogEntry]], run: ExportRun) -> bytes:
    """The trail as a workbook: the events on one sheet, the export's own details on a
    second.

    The workbook is write-only, so memory stays flat however many rows arrive, and every
    openpyxl call after the first header runs in a worker thread: at the row ceiling
    that is tens of seconds of CPU, which would otherwise stall every other request.
    A build that fails part way leaves openpyxl's temp file behind until the process exits.
    """
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("Audit log")
    # Panes, widths and the header style must be set before the first row is written.
    sheet.freeze_panes = "A2"
    for index, width in enumerate(_COLUMN_WIDTHS, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    header = []
    for label in HEADERS:
        cell = WriteOnlyCell(sheet, value=label)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=_HEADER_FILL)
        header.append(cell)
    sheet.append(header)
    rows = 0
    async for batch in batches:
        await asyncio.to_thread(_append_rows, sheet, batch)
        rows += len(batch)
    return await asyncio.to_thread(_finish, workbook, sheet, run, rows)
