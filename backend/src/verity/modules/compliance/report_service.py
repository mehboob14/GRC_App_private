"""The control gap-assessment report, rendered to JSON, CSV, or XLSX.

One dataset, three renderers — so the spreadsheet, the download, and the PDF a
person prints all agree to the row. The dataset is control-centric: every
control (disabled ones included, because "who removed it and why" is exactly
what a gap assessment is for) with its framework, owner, criteria, evidence
count, and status, plus a KPI summary over the live library.

Reads go through the sibling and cross-module *services* (rule 4): control rows
and owner names from ``control_service``, evidence counts from
``evidence_service``. Nothing here touches another module's tables.
"""

from __future__ import annotations

import csv
import io
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy.ext.asyncio import AsyncSession

_FRAMEWORK_LABEL = {"SOC2": "SOC 2"}

_STATUS_LABEL = {
    "not_started": "Not started",
    "in_progress": "In progress",
    "implemented": "Implemented",
    "not_applicable": "Not applicable",
    "disabled": "Disabled",
}


@dataclass(frozen=True, slots=True)
class ReportRow:
    code: str
    name: str
    category: str
    control_type: str | None
    status: str
    status_label: str
    owner_name: str | None
    frameworks: list[str]
    criteria: list[str]
    evidence_count: int
    disabled_reason: str | None


@dataclass(frozen=True, slots=True)
class ReportKpis:
    controls_total: int
    controls_disabled: int
    controls_evidenced: int
    controls_owned: int
    controls_ready: int
    criteria_mapped: int
    by_status: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ControlGapReport:
    generated_at: datetime
    framework_label: str
    kpis: ReportKpis
    rows: list[ReportRow]


def _framework_label(code: str) -> str:
    return _FRAMEWORK_LABEL.get(code, code)


def _split_keys(requirement_keys: list[str]) -> tuple[list[str], list[str]]:
    """Return (framework labels, criterion codes) from ``FRAMEWORK:CRITERION`` keys."""
    frameworks: set[str] = set()
    criteria: list[str] = []
    for key in requirement_keys:
        framework, _, criterion = key.partition(":")
        if criterion:
            frameworks.add(_framework_label(framework))
            criteria.append(criterion)
        else:
            criteria.append(key)
    return sorted(frameworks), criteria


class ReportService:
    async def control_gap_report(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> ControlGapReport:
        from verity.modules.compliance.control_service import control_service  # noqa: PLC0415
        from verity.modules.evidence.service import evidence_service  # noqa: PLC0415

        controls = await control_service.list_controls(
            session, tenant_id=tenant_id, include_disabled=True
        )
        counts = await evidence_service.evidence_counts_by_control(session, tenant_id)

        rows: list[ReportRow] = []
        for control in controls:
            frameworks, criteria = _split_keys(control.requirement_keys)
            status = "disabled" if control.disabled_at is not None else control.status
            rows.append(
                ReportRow(
                    code=control.code,
                    name=control.name,
                    category=control.category,
                    control_type=control.control_type,
                    status=status,
                    status_label=_STATUS_LABEL.get(status, status),
                    owner_name=control.owner_name,
                    frameworks=frameworks,
                    criteria=criteria,
                    evidence_count=counts.get(control.id, 0),
                    disabled_reason=control.disabled_reason,
                )
            )
        rows.sort(key=lambda r: r.code)

        live = [c for c in controls if c.disabled_at is None]
        by_status: dict[str, int] = {}
        for control in live:
            by_status[control.status] = by_status.get(control.status, 0) + 1
        evidenced = sum(1 for c in live if counts.get(c.id, 0) > 0)
        ready = sum(1 for c in live if c.status == "implemented" and counts.get(c.id, 0) > 0)
        criteria_mapped = len(
            {key for c in controls if c.disabled_at is None for key in c.requirement_keys}
        )

        framework_labels = sorted({fw for row in rows for fw in row.frameworks})
        return ControlGapReport(
            generated_at=datetime.now(UTC),
            framework_label=", ".join(framework_labels) if framework_labels else "No frameworks",
            kpis=ReportKpis(
                controls_total=len(live),
                controls_disabled=len(controls) - len(live),
                controls_evidenced=evidenced,
                controls_owned=sum(1 for c in live if c.owner_membership_id is not None),
                controls_ready=ready,
                criteria_mapped=criteria_mapped,
                by_status=by_status,
            ),
            rows=rows,
        )

    # -- renderers ---------------------------------------------------------------

    @staticmethod
    def _kpi_pairs(report: ControlGapReport) -> list[tuple[str, object]]:
        k = report.kpis
        pairs: list[tuple[str, object]] = [
            ("Frameworks", report.framework_label),
            ("Generated", report.generated_at.strftime("%Y-%m-%d %H:%M UTC")),
            ("Controls (in scope)", k.controls_total),
            ("Controls with evidence", k.controls_evidenced),
            ("Controls with an owner", k.controls_owned),
            ("Ready for audit", k.controls_ready),
            ("Criteria mapped", k.criteria_mapped),
            ("Disabled controls", k.controls_disabled),
        ]
        for status, label in _STATUS_LABEL.items():
            if status == "disabled":
                continue
            pairs.append((f"  {label}", k.by_status.get(status, 0)))
        return pairs

    _HEADERS = (
        "Code",
        "Control",
        "Category",
        "Type",
        "Status",
        "Owner",
        "Framework",
        "Criteria",
        "Evidence",
        "Disabled reason",
    )

    @classmethod
    def _row_cells(cls, row: ReportRow) -> list[object]:
        return [
            row.code,
            row.name,
            row.category,
            row.control_type or "",
            row.status_label,
            row.owner_name or "Unassigned",
            ", ".join(row.frameworks),
            ", ".join(row.criteria),
            row.evidence_count,
            row.disabled_reason or "",
        ]

    @staticmethod
    def _csv_safe(value: object) -> object:
        # Formula-injection guard: a cell a spreadsheet would evaluate is prefixed
        # so Excel/Sheets treat it as text, not a formula.
        if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
            return "'" + value
        return value

    def render_csv(self, report: ControlGapReport) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["Control gap assessment"])
        for label, value in self._kpi_pairs(report):
            writer.writerow([label.strip(), self._csv_safe(value)])
        writer.writerow([])
        writer.writerow(self._HEADERS)
        for row in report.rows:
            writer.writerow([self._csv_safe(cell) for cell in self._row_cells(row)])
        return buffer.getvalue()

    def render_xlsx(self, report: ControlGapReport) -> bytes:
        workbook = Workbook()
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill("solid", fgColor="0369A1")
        title_font = Font(bold=True, size=14)

        summary = workbook.active
        summary.title = "Summary"
        summary["A1"] = "Control gap assessment"
        summary["A1"].font = title_font
        for offset, (label, value) in enumerate(self._kpi_pairs(report), start=3):
            summary.cell(row=offset, column=1, value=label.strip()).font = Font(
                bold=not label.startswith("  ")
            )
            summary.cell(row=offset, column=2, value=value)
        summary.column_dimensions["A"].width = 26
        summary.column_dimensions["B"].width = 40

        sheet = workbook.create_sheet("Controls")
        sheet.append(list(self._HEADERS))
        for cell in sheet[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(vertical="center")
        for row in report.rows:
            sheet.append(self._row_cells(row))
        widths = (12, 40, 26, 14, 14, 22, 12, 24, 10, 32)
        for index, width in enumerate(widths, start=1):
            sheet.column_dimensions[get_column_letter(index)].width = width
        sheet.freeze_panes = "A2"

        stream = io.BytesIO()
        workbook.save(stream)
        return stream.getvalue()


report_service = ReportService()
