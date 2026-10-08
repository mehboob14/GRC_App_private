"""Spreadsheets in and out of a register: the import template, the validating
preview, the commit, and the CSV and Excel exports (R13, spec heatmap export).

The preview writes nothing. It returns normalised rows with their errors and
warnings; the client sends back the rows it wants and the service validates them
again on commit, so no upload is ever stored between the two calls.
"""

from __future__ import annotations

import csv
import io
import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Final

from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import InvalidInput, VerityError
from verity.modules.audit.service import Actor
from verity.modules.risk import scoring
from verity.modules.risk.service import RegisterView, RiskFilters, RiskInput, RiskView, risk_service

MAX_IMPORT_ROWS: Final = 2000
_TEMPLATE_ROWS: Final = 500

STATUS_LABELS: Final[dict[str, str]] = {
    "open": "Open",
    "in_treatment": "In treatment",
    "mitigated": "Mitigated",
    "accepted": "Accepted",
    "closed": "Closed",
}
TREATMENT_LABELS: Final[dict[str, str]] = {
    "mitigate": "Mitigate",
    "accept": "Accept",
    "avoid": "Avoid",
    "transfer": "Transfer",
}
REGISTER_TYPE_LABELS: Final[dict[str, str]] = {
    "enterprise": "Enterprise",
    "rcsa": "RCSA",
    "iso_27001": "ISO 27001",
    "soc_2": "SOC 2",
    "pci_dss": "PCI DSS",
    "sox": "SOX",
    "gdpr": "GDPR",
    "nist_csf": "NIST CSF",
    "sama_csf": "SAMA CSF",
    "internal": "Internal",
    "project": "Project",
    "third_party": "Third party",
    "other": "Other",
}
_IMPORTABLE_STATUSES: Final = ("open", "in_treatment", "mitigated")

# (key, header, required). The header is what the template writes and what the
# preview reads back; aliases below cover the spellings people actually use.
COLUMNS: Final[tuple[tuple[str, str, bool], ...]] = (
    ("title", "Title", True),
    ("description", "Description", False),
    ("category", "Category", True),
    ("sub_category", "Subcategory", False),
    ("status", "Status", False),
    ("owner", "Business owner", False),
    ("business_unit", "Business unit", False),
    ("inherent_likelihood", "Inherent likelihood", False),
    ("inherent_impact", "Inherent impact", False),
    ("residual_likelihood", "Residual likelihood", False),
    ("residual_impact", "Residual impact", False),
    ("root_cause", "Root cause", False),
    ("consequences", "Consequences", False),
    ("recommendations", "Recommendations", False),
    ("treatment", "Treatment", False),
    ("treatment_plan", "Treatment plan", False),
    ("treatment_due_on", "Treatment due", False),
    ("next_review_on", "Next review", False),
)

_ALIASES: Final[dict[str, str]] = {
    "risk": "title",
    "risk title": "title",
    "name": "title",
    "risk name": "title",
    "risk description": "description",
    "risk category": "category",
    "sub category": "sub_category",
    "subcategory": "sub_category",
    "risk sub category": "sub_category",
    "risk status": "status",
    "owner": "owner",
    "risk owner": "owner",
    "business owner": "owner",
    "owner email": "owner",
    "department": "business_unit",
    "team": "business_unit",
    "business unit": "business_unit",
    "likelihood": "inherent_likelihood",
    "impact": "inherent_impact",
    "treatment decision": "treatment",
    "risk treatment": "treatment",
    "due date": "treatment_due_on",
    "treatment due date": "treatment_due_on",
    "review date": "next_review_on",
    "next review date": "next_review_on",
}
for _key, _header, _required in COLUMNS:
    _ALIASES.setdefault(_header.lower(), _key)
    _ALIASES.setdefault(_key.replace("_", " "), _key)

_BAND_FILL: Final[dict[str, tuple[str, str]]] = {
    "low": ("DCFCE7", "166534"),
    "medium": ("FEF3C7", "92400E"),
    "high": ("FFEDD5", "9A3412"),
    "critical": ("FEE2E2", "991B1B"),
}
_HEADER_FILL: Final = "1F2A44"


def _normalise_header(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower().replace("*", "")).strip()
    return _ALIASES.get(text, text.replace(" ", "_"))


@dataclass
class ImportRow:
    row_number: int
    title: str = ""
    description: str = ""
    category_id: uuid.UUID | None = None
    category_name: str | None = None
    sub_category_id: uuid.UUID | None = None
    sub_category_name: str | None = None
    status: str = "open"
    owner_membership_id: uuid.UUID | None = None
    owner_name: str | None = None
    department_group_id: uuid.UUID | None = None
    department_name: str | None = None
    inherent_likelihood: int | None = None
    inherent_impact: int | None = None
    residual_likelihood: int | None = None
    residual_impact: int | None = None
    root_cause: str | None = None
    consequences: str | None = None
    recommendations: str | None = None
    treatment: str | None = None
    treatment_plan: str | None = None
    treatment_due_on: date | None = None
    next_review_on: date | None = None
    custom_fields: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# -- reading ---------------------------------------------------------------------


def read_rows(file_name: str, data: bytes) -> list[tuple[int, dict[str, Any]]]:
    """``(row_number, {key: value})`` for every non-blank row of a CSV or Excel file."""
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if ext in ("xlsx", "xlsm"):
        rows = _read_xlsx(data)
    elif ext in ("csv", "txt", ""):
        rows = _read_csv(data)
    else:
        raise InvalidInput(
            "Upload the Excel template or a CSV file.", detail=f"unsupported import type .{ext}"
        )
    out = [(n, r) for n, r in rows if any(str(v).strip() for v in r.values() if v is not None)]
    if len(out) > MAX_IMPORT_ROWS:
        raise InvalidInput(
            f"A file can hold up to {MAX_IMPORT_ROWS} risks. Split it and import each part.",
            detail=f"{len(out)} rows",
        )
    return out


def _read_csv(data: bytes) -> list[tuple[int, dict[str, Any]]]:
    reader = csv.reader(io.StringIO(data.decode("utf-8-sig", errors="replace")))
    try:
        header = [_normalise_header(h) for h in next(reader)]
    except StopIteration:
        return []
    return [
        (index + 2, {header[i]: v for i, v in enumerate(values) if i < len(header)})
        for index, values in enumerate(reader)
    ]


def _read_xlsx(data: bytes) -> list[tuple[int, dict[str, Any]]]:
    import openpyxl  # noqa: PLC0415 — heavy import, only on the Excel path

    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:  # a corrupt or password protected workbook
        raise InvalidInput(
            "This Excel file could not be opened. Save it again as .xlsx and retry.",
            detail="unreadable workbook",
        ) from exc
    ws = wb["Risks"] if "Risks" in wb.sheetnames else wb.active
    if ws is None:
        return []
    values = ws.iter_rows(values_only=True)
    try:
        header = [_normalise_header(h) for h in next(values)]
    except StopIteration:
        return []
    return [
        (index + 2, {header[i]: v for i, v in enumerate(row) if i < len(header)})
        for index, row in enumerate(values)
    ]


def _text(value: Any) -> str:  # noqa: ANN401 — a spreadsheet cell
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _int(value: Any, label: str, row: ImportRow) -> int | None:  # noqa: ANN401
    text = _text(value)
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        row.errors.append(f"{label} must be a number")
        return None
    if not number.is_integer():
        row.errors.append(f"{label} must be a whole number")
        return None
    return int(number)


def _date(value: Any, label: str, row: ImportRow) -> date | None:  # noqa: ANN401
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _text(value)
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        row.errors.append(f"{label} must be a date like 2026-12-31")
        return None


def _choice(value: Any, labels: dict[str, str]) -> str | None:  # noqa: ANN401
    text = _text(value).lower()
    if not text:
        return None
    for key, label in labels.items():
        if text in (key, label.lower(), key.replace("_", " ")):
            return key
    return "?"


# -- preview and commit ------------------------------------------------------------


async def preview(  # noqa: PLR0912, PLR0915 — one rule per column
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    register_id: uuid.UUID,
    file_name: str,
    data: bytes,
) -> list[ImportRow]:
    register, categories = await risk_service.register_context(
        session, tenant_id=tenant_id, register_id=register_id
    )
    raw = read_rows(file_name, data)
    if not raw:
        raise InvalidInput(
            "The file has no risks in it. Fill in the template from the second row.",
            detail="empty import",
        )
    if "title" not in raw[0][1] and not any("title" in r for _, r in raw):
        raise InvalidInput(
            "The file needs a Title column. Download the template to see the expected columns.",
            detail="no title column",
        )
    extras = await risk_service.custom_fields(session, tenant_id=tenant_id)
    members = await risk_service.members(session, tenant_id=tenant_id)
    groups = await risk_service.groups(session, tenant_id=tenant_id)
    by_email = {m.email.lower(): m for m in members}
    by_name = {m.full_name.lower(): m for m in members}
    group_by_name = {name.lower(): (gid, name) for gid, name in groups.items()}
    live = [c for c in categories if c.archived_at is None]
    parents = {c.name.lower(): c for c in live if c.parent_id is None}
    existing = await risk_service.titles(session, tenant_id=tenant_id, register_id=register.id)
    seen: set[str] = set()

    out: list[ImportRow] = []
    for number, values in raw:
        row = ImportRow(row_number=number)
        row.title = _text(values.get("title"))[:300]
        row.description = _text(values.get("description"))
        if not row.title:
            row.errors.append("Title is missing")
        elif row.title.lower() in existing:
            row.warnings.append("A risk with this title is already in the register")
        elif row.title.lower() in seen:
            row.warnings.append("This title appears twice in the file")
        seen.add(row.title.lower())

        category_text = _text(values.get("category"))
        parent = parents.get(category_text.lower()) if category_text else None
        if not category_text:
            row.errors.append("Category is missing")
        elif parent is None:
            row.errors.append(f"Category {category_text} is not in this register")
        else:
            row.category_id, row.category_name = parent.id, parent.name
            sub_text = _text(values.get("sub_category"))
            if sub_text:
                child = next(
                    (
                        c
                        for c in live
                        if c.parent_id == parent.id and c.name.lower() == sub_text.lower()
                    ),
                    None,
                )
                if child is None:
                    row.errors.append(f"Subcategory {sub_text} is not under {parent.name}")
                else:
                    row.sub_category_id, row.sub_category_name = child.id, child.name

        status = _choice(values.get("status"), STATUS_LABELS) or "open"
        if status not in _IMPORTABLE_STATUSES:
            row.errors.append("Status must be Open, In treatment or Mitigated")
        else:
            row.status = status

        owner_text = _text(values.get("owner"))
        if owner_text:
            member = by_email.get(owner_text.lower()) or by_name.get(owner_text.lower())
            if member is None:
                row.warnings.append(f"Owner {owner_text} is not a member, left unassigned")
            else:
                row.owner_membership_id, row.owner_name = member.membership_id, member.full_name

        unit_text = _text(values.get("business_unit"))
        if unit_text:
            match = group_by_name.get(unit_text.lower())
            if match is None:
                row.warnings.append(f"Business unit {unit_text} does not exist, left empty")
            else:
                row.department_group_id, row.department_name = match

        for prefix in ("inherent", "residual"):
            likelihood = _int(
                values.get(f"{prefix}_likelihood"), f"{prefix.capitalize()} likelihood", row
            )
            impact = _int(values.get(f"{prefix}_impact"), f"{prefix.capitalize()} impact", row)
            if (likelihood is None) != (impact is None):
                row.errors.append(f"Give both {prefix} likelihood and impact, or neither")
                continue
            if likelihood is not None and not 1 <= likelihood <= register.likelihood_levels:
                row.errors.append(
                    f"{prefix.capitalize()} likelihood must be 1 to {register.likelihood_levels}"
                )
                continue
            if impact is not None and not 1 <= impact <= register.impact_levels:
                row.errors.append(
                    f"{prefix.capitalize()} impact must be 1 to {register.impact_levels}"
                )
                continue
            setattr(row, f"{prefix}_likelihood", likelihood)
            setattr(row, f"{prefix}_impact", impact)

        treatment = _choice(values.get("treatment"), TREATMENT_LABELS)
        if treatment == "?":
            row.errors.append("Treatment must be Mitigate, Accept, Avoid or Transfer")
        else:
            row.treatment = treatment
        for key in ("root_cause", "consequences", "recommendations", "treatment_plan"):
            setattr(row, key, _text(values.get(key)) or None)
        row.treatment_due_on = _date(values.get("treatment_due_on"), "Treatment due", row)
        row.next_review_on = _date(values.get("next_review_on"), "Next review", row)
        for definition in extras:
            cell = _text(values.get(definition.key))
            if cell and definition.field_type == "checkbox":
                cell = "true" if cell.lower() in ("yes", "y", "true", "1", "x") else "false"
            if cell:
                row.custom_fields[definition.key] = cell
        if row.custom_fields or extras:
            try:
                row.custom_fields = await risk_service.clean_custom(
                    session, tenant_id=tenant_id, values=row.custom_fields
                )
            except VerityError as exc:
                row.errors.append(exc.message)
        out.append(row)
    return out


async def commit(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    actor: Actor,
    register_id: uuid.UUID,
    rows: Sequence[ImportRow],
) -> dict[str, Any]:
    """Create every row that validates; report the rest by row number."""
    if not rows:
        raise InvalidInput("There is nothing to import.", detail="empty commit")
    if len(rows) > MAX_IMPORT_ROWS:
        raise InvalidInput(
            f"Import up to {MAX_IMPORT_ROWS} risks at a time.", detail="too many rows"
        )
    number = await risk_service.next_code_number(session, tenant_id=tenant_id)
    created = 0
    failed: list[dict[str, Any]] = []
    for row in rows:
        if row.category_id is None:
            failed.append({"row_number": row.row_number, "error": "Category is missing"})
            continue
        try:
            async with session.begin_nested():
                await risk_service.create_risk(
                    session,
                    tenant_id=tenant_id,
                    actor=actor,
                    data=RiskInput(
                        register_id=register_id,
                        title=row.title,
                        description=row.description,
                        category_id=row.category_id,
                        sub_category_id=row.sub_category_id,
                        status=row.status,
                        treatment=row.treatment,
                        inherent_likelihood=row.inherent_likelihood,
                        inherent_impact=row.inherent_impact,
                        residual_likelihood=row.residual_likelihood,
                        residual_impact=row.residual_impact,
                        root_cause=row.root_cause,
                        consequences=row.consequences,
                        recommendations=row.recommendations,
                        treatment_plan=row.treatment_plan,
                        owner_membership_id=row.owner_membership_id,
                        department_group_id=row.department_group_id,
                        treatment_due_on=row.treatment_due_on,
                        next_review_on=row.next_review_on,
                        custom_fields=row.custom_fields,
                    ),
                    origin="import",
                    code_number=number,
                )
        except VerityError as exc:
            failed.append({"row_number": row.row_number, "error": exc.message})
            continue
        number += 1
        created += 1
    return {"created": created, "failed": failed}


# -- template ------------------------------------------------------------------------


def build_template(  # noqa: PLR0915 — three sheets, laid out in order
    register: RegisterView,
    owners: Sequence[str],
    units: Sequence[str],
    extras: Sequence[tuple[str, str]] = (),
) -> bytes:
    """The import workbook: a Risks sheet with dropdowns (subcategory follows
    category), a hidden Lists sheet feeding them, and a Guide."""
    from openpyxl import Workbook  # noqa: PLC0415
    from openpyxl.styles import Alignment, Font, PatternFill  # noqa: PLC0415
    from openpyxl.utils import get_column_letter, quote_sheetname  # noqa: PLC0415
    from openpyxl.workbook.defined_name import DefinedName  # noqa: PLC0415
    from openpyxl.worksheet.datavalidation import DataValidation  # noqa: PLC0415

    wb = Workbook()
    ws = wb.active
    assert ws is not None  # noqa: S101 — a new workbook always has one sheet
    ws.title = "Risks"
    lists = wb.create_sheet("Lists")
    guide = wb.create_sheet("Guide")

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor=_HEADER_FILL)
    for index, (key, header, required) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=index, value=f"{header} *" if required else header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center")
        width = (
            44
            if key
            in ("description", "root_cause", "consequences", "recommendations", "treatment_plan")
            else 20
        )
        ws.column_dimensions[get_column_letter(index)].width = width
    for offset, (_key, label) in enumerate(extras, start=len(COLUMNS) + 1):
        cell = ws.cell(row=1, column=offset, value=label)
        cell.font = header_font
        cell.fill = header_fill
        ws.column_dimensions[get_column_letter(offset)].width = 20
    ws.freeze_panes = "B2"
    ws.row_dimensions[1].height = 22

    live = [c for c in register.categories if not c.archived]
    sheet = quote_sheetname("Lists")

    def fill_column(column: int, title: str, values: Sequence[str]) -> str:
        lists.cell(row=1, column=column, value=title).font = Font(bold=True)
        for i, value in enumerate(values, start=2):
            lists.cell(row=i, column=column, value=value)
        letter = get_column_letter(column)
        return f"{sheet}!${letter}$2:${letter}${max(2, len(values) + 1)}"

    category_range = fill_column(1, "Categories", [c.name for c in live])
    status_range = fill_column(2, "Statuses", [STATUS_LABELS[s] for s in _IMPORTABLE_STATUSES])
    treatment_range = fill_column(3, "Treatments", list(TREATMENT_LABELS.values()))
    owner_range = fill_column(4, "Owners", list(owners))
    unit_range = fill_column(5, "Business units", list(units))
    for i, category in enumerate(live, start=1):
        target = fill_column(
            6 + i, category.name, [s.name for s in category.children if not s.archived]
        )
        wb.defined_names[f"sub_{i}"] = DefinedName(f"sub_{i}", attr_text=target)
    lists.sheet_state = "hidden"

    column_of = {key: get_column_letter(i) for i, (key, _h, _r) in enumerate(COLUMNS, start=1)}
    last = _TEMPLATE_ROWS + 1

    def validate(key: str, dv: Any) -> None:  # noqa: ANN401 — openpyxl is untyped
        dv.error = "Choose a value from the list."
        dv.errorStyle = "stop"
        ws.add_data_validation(dv)
        dv.add(f"{column_of[key]}2:{column_of[key]}{last}")

    validate(
        "category", DataValidation(type="list", formula1=f"={category_range}", allow_blank=True)
    )
    first_category = f"{column_of['category']}2"
    validate(
        "sub_category",
        DataValidation(
            type="list",
            formula1=(f'=INDIRECT("sub_"&MATCH({first_category},{category_range},0))'),
            allow_blank=True,
        ),
    )
    validate("status", DataValidation(type="list", formula1=f"={status_range}", allow_blank=True))
    validate(
        "treatment", DataValidation(type="list", formula1=f"={treatment_range}", allow_blank=True)
    )
    if owners:
        validate("owner", DataValidation(type="list", formula1=f"={owner_range}", allow_blank=True))
    if units:
        validate(
            "business_unit",
            DataValidation(type="list", formula1=f"={unit_range}", allow_blank=True),
        )
    for prefix in ("inherent", "residual"):
        for axis, levels in (
            ("likelihood", register.likelihood_levels),
            ("impact", register.impact_levels),
        ):
            dv = DataValidation(
                type="whole",
                operator="between",
                formula1="1",
                formula2=str(levels),
                allow_blank=True,
            )
            dv.error = f"Enter a whole number from 1 to {levels}."
            ws.add_data_validation(dv)
            letter = column_of[f"{prefix}_{axis}"]
            dv.add(f"{letter}2:{letter}{last}")
    for key in ("treatment_due_on", "next_review_on"):
        letter = column_of[key]
        for r in range(2, last + 1):
            ws[f"{letter}{r}"].number_format = "yyyy-mm-dd"

    guide.column_dimensions["A"].width = 26
    guide.column_dimensions["B"].width = 90
    lines: list[tuple[str, str]] = [
        (
            "Register",
            f"{register.name} "
            f"({REGISTER_TYPE_LABELS.get(register.register_type, register.register_type)})",
        ),
        (
            "How to use",
            "Fill one risk per row on the Risks sheet, starting on row 2. "
            "Title and Category are required.",
        ),
        (
            "Subcategory",
            "Pick the category first. The subcategory list then shows only its subcategories.",
        ),
        (
            "Scores",
            "Likelihood and impact are whole numbers. "
            "Give both or neither for inherent and for residual.",
        ),
        ("Business owner", "Use the member's email address."),
        ("Dates", "Use the format 2026-12-31."),
        ("", ""),
        ("Likelihood", ""),
        *[
            (f"{s['level']}  {s['label']}", s.get("description", ""))
            for s in register.likelihood_scale
        ],
        ("", ""),
        ("Impact", ""),
        *[(f"{s['level']}  {s['label']}", s.get("description", "")) for s in register.impact_scale],
        ("", ""),
        ("Severity bands", "Score is likelihood multiplied by impact."),
        *[(b["label"], f"From {b['min_score']}") for b in register.severity_bands],
    ]
    for r, (label, text) in enumerate(lines, start=1):
        guide.cell(row=r, column=1, value=label).font = Font(
            bold=label in ("Likelihood", "Impact", "Severity bands", "Register")
        )
        guide.cell(row=r, column=2, value=text).alignment = Alignment(wrap_text=True)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


# -- export ----------------------------------------------------------------------------

_EXPORT_HEADERS: Final[tuple[str, ...]] = (
    "Code",
    "Title",
    "Description",
    "Category",
    "Subcategory",
    "Status",
    "Treatment",
    "Business owner",
    "Business unit",
    "Inherent likelihood",
    "Inherent impact",
    "Inherent score",
    "Inherent band",
    "Residual likelihood",
    "Residual impact",
    "Residual score",
    "Residual band",
    "Controls",
    "Treatment due",
    "Next review",
    "Origin",
    "Created",
)


def _band_label(register: RegisterView, key: str | None) -> str:
    return next((str(b["label"]) for b in register.severity_bands if b["key"] == key), "")


def _export_row(register: RegisterView, v: RiskView) -> list[Any]:
    return [
        v.code,
        v.title,
        v.description,
        v.category_name,
        v.sub_category_name or "",
        STATUS_LABELS.get(v.status, v.status),
        TREATMENT_LABELS.get(v.treatment or "", ""),
        v.owner.name if v.owner else "",
        v.department_name or "",
        v.inherent_likelihood,
        v.inherent_impact,
        v.inherent_score,
        _band_label(register, v.inherent_band),
        v.residual_likelihood,
        v.residual_impact,
        v.residual_score,
        _band_label(register, v.residual_band),
        v.control_count,
        v.treatment_due_on.isoformat() if v.treatment_due_on else "",
        v.next_review_on.isoformat() if v.next_review_on else "",
        v.origin,
        v.created_at.astimezone(UTC).date().isoformat(),
    ]


def export_csv(register: RegisterView, risks: Sequence[RiskView]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_EXPORT_HEADERS)
    for v in risks:
        writer.writerow(["" if c is None else c for c in _export_row(register, v)])
    return buffer.getvalue().encode("utf-8-sig")


def export_xlsx(  # noqa: PLR0912, PLR0915 — three sheets, laid out in order
    register: RegisterView,
    risks: Sequence[RiskView],
    summary: dict[str, Any],
    acceptances: Sequence[dict[str, Any]],
) -> bytes:
    from openpyxl import Workbook  # noqa: PLC0415
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side  # noqa: PLC0415
    from openpyxl.utils import get_column_letter  # noqa: PLC0415

    wb = Workbook()
    ws = wb.active
    assert ws is not None  # noqa: S101
    ws.title = "Register"
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor=_HEADER_FILL)
    for i, header in enumerate(_EXPORT_HEADERS, start=1):
        cell = ws.cell(row=1, column=i, value=header)
        cell.font = header_font
        cell.fill = header_fill
        ws.column_dimensions[get_column_letter(i)].width = (
            40 if header in ("Title", "Description") else 16
        )
    band_columns = {
        _EXPORT_HEADERS.index("Inherent band") + 1: "inherent",
        _EXPORT_HEADERS.index("Residual band") + 1: "residual",
    }
    for r, v in enumerate(risks, start=2):
        for c, value in enumerate(_export_row(register, v), start=1):
            cell = ws.cell(row=r, column=c, value=value)
            if c in band_columns:
                key = v.inherent_band if band_columns[c] == "inherent" else v.residual_band
                if key in _BAND_FILL:
                    bg, fg = _BAND_FILL[key]
                    cell.fill = PatternFill("solid", fgColor=bg)
                    cell.font = Font(color=fg, bold=True)
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(_EXPORT_HEADERS))}{max(1, len(risks) + 1)}"

    heat = wb.create_sheet("Heatmaps")
    thin = Side(style="thin", color="FFFFFF")
    heat.column_dimensions["A"].width = 22
    top = 1
    for title, key in (("Inherent", "heatmap_inherent"), ("Residual", "heatmap_residual")):
        grid: list[list[int]] = summary[key]
        heat.cell(row=top, column=1, value=f"{title} risk").font = Font(bold=True, size=13)
        heat.cell(row=top + 1, column=1, value="Likelihood by impact").font = Font(color="6B7280")
        for impact in range(register.impact_levels):
            label = register.impact_scale[impact]["label"]
            cell = heat.cell(row=top + 2, column=impact + 2, value=f"{impact + 1} {label}")
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center", wrap_text=True)
            heat.column_dimensions[get_column_letter(impact + 2)].width = 14
        for offset, likelihood in enumerate(range(register.likelihood_levels, 0, -1)):
            row = top + 3 + offset
            label = register.likelihood_scale[likelihood - 1]["label"]
            heat.cell(row=row, column=1, value=f"{likelihood} {label}").font = Font(bold=True)
            heat.row_dimensions[row].height = 30
            for impact in range(1, register.impact_levels + 1):
                count = grid[likelihood - 1][impact - 1]
                band = (
                    scoring.band_for(
                        register.severity_bands,
                        scoring.formula_score(register.scoring_formula, likelihood, impact),
                    )
                    or "low"
                )
                bg, fg = _BAND_FILL[band]
                cell = heat.cell(row=row, column=impact + 1, value=count or None)
                cell.fill = PatternFill("solid", fgColor=bg)
                cell.font = Font(bold=True, color=fg, size=12)
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
        top += register.likelihood_levels + 5

    treat = wb.create_sheet("Treatment")
    treat.column_dimensions["A"].width = 30
    treat.column_dimensions["B"].width = 44
    treat.column_dimensions["C"].width = 16
    treat.column_dimensions["D"].width = 24
    r = 1
    treat.cell(row=r, column=1, value="Status").font = Font(bold=True, size=13)
    r += 1
    for status, count in summary["by_status"].items():
        treat.cell(row=r, column=1, value=STATUS_LABELS.get(status, status))
        treat.cell(row=r, column=2, value=count)
        r += 1
    r += 1
    treat.cell(row=r, column=1, value="Treatment decision").font = Font(bold=True, size=13)
    r += 1
    for treatment, count in sorted(summary["by_treatment"].items()):
        treat.cell(row=r, column=1, value=TREATMENT_LABELS.get(treatment, "Undecided"))
        treat.cell(row=r, column=2, value=count)
        r += 1
    r += 1
    treat.cell(row=r, column=1, value="Acceptances in force").font = Font(bold=True, size=13)
    r += 1
    for i, header in enumerate(("Risk", "Title", "Expires", "Approver"), start=1):
        treat.cell(row=r, column=i, value=header).font = Font(bold=True)
    r += 1
    for a in acceptances:
        treat.cell(row=r, column=1, value=a["code"])
        treat.cell(row=r, column=2, value=a["title"])
        treat.cell(row=r, column=3, value=a["expires_on"].isoformat())
        treat.cell(row=r, column=4, value=a["approver"] or "")
        r += 1

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


async def export_register(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    filters: RiskFilters,
    file_format: str,
) -> tuple[bytes, str, str]:
    """``(bytes, filename, content_type)`` for the register as filtered."""
    register = await risk_service.get_register(
        session, tenant_id=tenant_id, register_id=filters.register_id
    )
    risks = await risk_service.all_risks(session, tenant_id=tenant_id, filters=filters)
    slug = re.sub(r"[^a-z0-9]+", "_", register.name.lower()).strip("_") or "risk_register"
    stamp = datetime.now(UTC).date().isoformat()
    if file_format == "csv":
        return export_csv(register, risks), f"{slug}_{stamp}.csv", "text/csv"
    summary = await risk_service.summary(session, tenant_id=tenant_id, register_id=register.id)
    acceptances = await risk_service.active_acceptances(
        session, tenant_id=tenant_id, register_id=register.id
    )
    return (
        export_xlsx(register, risks, summary, acceptances),
        f"{slug}_{stamp}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


async def template_for(
    session: AsyncSession, *, tenant_id: uuid.UUID, register_id: uuid.UUID
) -> tuple[bytes, str]:
    register = await risk_service.get_register(
        session, tenant_id=tenant_id, register_id=register_id
    )
    members = await risk_service.members(session, tenant_id=tenant_id)
    groups = await risk_service.groups(session, tenant_id=tenant_id)
    owners = sorted(m.email for m in members if m.status == "active")
    units = sorted(groups.values(), key=str.lower)
    slug = re.sub(r"[^a-z0-9]+", "_", register.name.lower()).strip("_") or "risk_register"
    extras = [
        (d.key, d.label) for d in await risk_service.custom_fields(session, tenant_id=tenant_id)
    ]
    return build_template(register, owners, units, extras), f"{slug}_import_template.xlsx"
