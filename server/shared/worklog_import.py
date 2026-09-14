from dataclasses import dataclass
from datetime import date as date_cls, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Optional

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from sqlalchemy.orm import Session

# Third narrow extension to server/shared (alongside storage.py and
# plan_limits.py — see CLAUDE.md's Code quality section): the row-validation
# rules here (lawyer assigned+active, case not closed, hours/date sanity)
# must be enforced *identically* whether a lawyer self-imports their own
# hours (client_api) or an office_manager bulk-imports on other lawyers'
# behalf (admin_api) — a genuine cross-app invariant, not a per-app
# presentation choice. Deliberately narrow: only parsing/validation lives
# here, never the multipart upload handling itself (that stays per-app, each
# backend parses its own incoming file with its own `UploadFile`/xlsx
# magic-byte check before handing the raw bytes to this module).

from shared.models import Case, CaseAssignment, Identity, Membership, WorkLog
from shared.models.enums import CaseStatus, UserRole
from shared import error_messages as E

# Same upper bound as CreateWorkLogRequest/UpdateWorkLogRequest's `le=24` —
# one hours sanity threshold, not two independently-chosen numbers.
MAX_HOURS_PER_ROW = Decimal("24")
# Sanity cap on one import batch — keeps a single upload from turning into an
# enormous, hard-to-review insert.
MAX_IMPORT_ROWS = 500

# Hebrew header labels (CLAUDE.md's RTL UI copy rule — the sheet a
# Hebrew-speaking lawyer/office_manager actually fills in should read like
# the rest of the product, same as every frontend screen). Column *position*
# is what parse_and_validate_import actually keys off of below, never the
# header text itself — these constants only gate "did you use the right
# template layout" (wrong column count/order) via a whole-row equality check.
HEADER_SELF = ["תיק", "תאריך (DD/MM/YYYY)", "שעות", "תיאור"]
HEADER_WITH_LAWYER_EMAIL = ["אימייל עורך/ת דין", "תיק", "תאריך (DD/MM/YYYY)", "שעות", "תיאור"]


@dataclass
class ImportRowError:
    row: int  # 1-based, matching the spreadsheet's own row numbers (header = row 1)
    message: str


@dataclass
class ImportRowResult:
    case_id: int
    lawyer_membership_id: int
    date: date_cls
    hours: Decimal
    description: Optional[str]


def _case_option_label(case: Case) -> str:
    return f"{case.id} - {case.title}"


def build_template_workbook(cases: list[Case], include_lawyer_email: bool, lawyer_emails: Optional[list[str]] = None) -> bytes:
    """Build a downloadable .xlsx template. `cases` is the exact set of
    options offered in the Case column's dropdown — the caller decides the
    scope (a lawyer's own assigned, non-closed cases for the self-import
    template; every non-closed case at the tenant for the office_manager
    bulk-import variant, since the dropdown can't be scoped per-row to
    whichever lawyer's email ends up in that row). `lawyer_emails` (required
    when `include_lawyer_email` is set) is likewise a real dropdown — sourced
    from the tenant's currently-active lawyers — so a typo'd or unauthorized
    email can't even be entered in the first place, same reasoning as the
    Case dropdown.
    """
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Import"
    # Sheet-level RTL — Hebrew header/description text and right-aligned
    # columns read correctly, matching the rest of the product's RTL UI.
    sheet.sheet_view.rightToLeft = True
    headers = HEADER_WITH_LAWYER_EMAIL if include_lawyer_email else HEADER_SELF
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    sheet.freeze_panes = "A2"

    # Position, not header text, is what actually locates each column — the
    # Case column is always second-to-last-but-one before Date, i.e. right
    # after Lawyer Email when that column is present, first otherwise.
    case_column_index = 2 if include_lawyer_email else 1
    date_column_index = case_column_index + 1
    hours_column_index = date_column_index + 1
    case_column_letter = get_column_letter(case_column_index)
    date_column_letter = get_column_letter(date_column_index)
    hours_column_letter = get_column_letter(hours_column_index)

    # A hardcoded comma-list DataValidation formula has a ~255-char limit —
    # a hidden sheet + range reference has no such cap, so it scales to
    # however many cases a real firm has.
    options_sheet = workbook.create_sheet("Cases")
    options_sheet.sheet_state = "hidden"
    for i, case in enumerate(cases, start=1):
        options_sheet.cell(row=i, column=1, value=_case_option_label(case))

    if cases:
        validation = DataValidation(
            type="list",
            formula1=f"Cases!$A$1:$A${len(cases)}",
            allow_blank=True,
        )
        validation.error = "Choose a case from the dropdown list"
        validation.errorTitle = "Invalid case"
        sheet.add_data_validation(validation)
        validation.add(f"{case_column_letter}2:{case_column_letter}1000")

    if include_lawyer_email:
        lawyer_emails = lawyer_emails or []
        lawyers_sheet = workbook.create_sheet("Lawyers")
        lawyers_sheet.sheet_state = "hidden"
        for i, email in enumerate(lawyer_emails, start=1):
            lawyers_sheet.cell(row=i, column=1, value=email)
        if lawyer_emails:
            lawyer_column_letter = get_column_letter(1)
            lawyer_validation = DataValidation(
                type="list",
                formula1=f"Lawyers!$A$1:$A${len(lawyer_emails)}",
                allow_blank=True,
            )
            lawyer_validation.error = "Choose a lawyer's email from the dropdown list"
            lawyer_validation.errorTitle = "Invalid lawyer"
            sheet.add_data_validation(lawyer_validation)
            lawyer_validation.add(f"{lawyer_column_letter}2:{lawyer_column_letter}1000")

    # Proper date + hours column layout: real date-formatted cells (so
    # Excel's own date picker/validation kicks in when someone types into
    # them) and a fixed decimal format for hours, instead of both columns
    # looking like plain, unformatted text.
    for row in range(2, 1001):
        sheet.cell(row=row, column=date_column_index).number_format = "dd/mm/yyyy"
        sheet.cell(row=row, column=hours_column_index).number_format = "0.##"

    for column_index in range(1, len(headers) + 1):
        sheet.column_dimensions[get_column_letter(column_index)].width = 28

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _parse_case_id(raw_value) -> Optional[int]:
    if raw_value is None:
        return None
    text = str(raw_value).strip()
    if not text:
        return None
    # Accepts either the dropdown's "12 - Some Title" format or a bare id.
    head = text.split("-", 1)[0].strip()
    try:
        return int(head)
    except ValueError:
        return None


def _parse_date(raw_value) -> Optional[date_cls]:
    if raw_value is None:
        return None
    if isinstance(raw_value, datetime):
        return raw_value.date()
    if isinstance(raw_value, date_cls):
        return raw_value
    text = str(raw_value).strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%d/%m/%Y").date()
    except ValueError:
        return None


def _parse_hours(raw_value) -> Optional[Decimal]:
    if raw_value is None:
        return None
    text = str(raw_value).strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def parse_and_validate_import(
    content: bytes,
    tenant_id: int,
    db: Session,
    include_lawyer_email: bool,
    self_membership: Optional[Membership] = None,
) -> tuple[list[ImportRowResult], list[ImportRowError]]:
    """Whole-file validation (CLAUDE.md: reject the whole file if any row
    fails, report which row and why, no partial imports). Returns
    (results, errors) — if `errors` is non-empty, `results` is always empty
    and must not be persisted by the caller.

    Row rules (identical for both callers): the lawyer (the fixed
    `self_membership`, or whoever the row's email resolves to) must be an
    existing active lawyer Membership at this tenant AND currently assigned
    to the referenced case; the case must not be closed; hours must be a
    positive, sane number; the date must be a real date.
    """
    try:
        workbook = load_workbook(BytesIO(content), data_only=True)
    except Exception:
        return [], [ImportRowError(row=0, message=E.import_could_not_read_file())]

    sheet = workbook["Import"] if "Import" in workbook.sheetnames else workbook.active
    expected_headers = HEADER_WITH_LAWYER_EMAIL if include_lawyer_email else HEADER_SELF

    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return [], [ImportRowError(row=0, message=E.import_file_is_empty())]

    header_row = [str(cell).strip() if cell is not None else "" for cell in rows[0][: len(expected_headers)]]
    if header_row != expected_headers:
        return [], [ImportRowError(row=1, message=E.import_expected_columns(", ".join(expected_headers)))]

    data_rows = [row for row in rows[1:] if row is not None and any(cell is not None for cell in row)]
    if not data_rows:
        return [], [ImportRowError(row=0, message=E.import_no_data_rows())]
    if len(data_rows) > MAX_IMPORT_ROWS:
        return [], [ImportRowError(row=0, message=E.import_too_many_rows(MAX_IMPORT_ROWS))]

    results: list[ImportRowResult] = []
    errors: list[ImportRowError] = []
    # Exact-duplicate-row detection: same lawyer + case + date + hours +
    # description already seen either earlier in this same file, or already
    # recorded as a real WorkLog — catches both "pasted the same row twice"
    # and "re-uploading a file already imported once before".
    seen_in_file: dict[tuple, int] = {}

    for offset, raw_row in enumerate(data_rows, start=2):  # spreadsheet row 2 = first data row
        column = 0
        lawyer_membership = self_membership

        if include_lawyer_email:
            email = str(raw_row[column]).strip() if raw_row[column] is not None else ""
            column += 1
            if not email:
                errors.append(ImportRowError(offset, E.import_lawyer_email_required()))
                continue
            lawyer_membership = (
                db.query(Membership)
                .join(Identity, Identity.id == Membership.identity_id)
                .filter(
                    Identity.email == email,
                    Membership.tenant_id == tenant_id,
                    Membership.role == UserRole.LAWYER,
                    Membership.active.is_(True),
                )
                .first()
            )
            if lawyer_membership is None:
                errors.append(ImportRowError(offset, E.import_no_active_lawyer(email)))
                continue

        case_id = _parse_case_id(raw_row[column]) if column < len(raw_row) else None
        column += 1
        if case_id is None:
            errors.append(ImportRowError(offset, E.import_case_required()))
            continue

        row_date = _parse_date(raw_row[column]) if column < len(raw_row) else None
        column += 1
        if row_date is None:
            errors.append(ImportRowError(offset, E.import_invalid_date()))
            continue

        hours = _parse_hours(raw_row[column]) if column < len(raw_row) else None
        column += 1
        if hours is None or hours <= 0 or hours > MAX_HOURS_PER_ROW:
            errors.append(ImportRowError(offset, E.import_invalid_hours(MAX_HOURS_PER_ROW)))
            continue

        description = None
        if column < len(raw_row) and raw_row[column] is not None:
            description = str(raw_row[column]).strip() or None

        case = db.query(Case).filter(Case.id == case_id, Case.tenant_id == tenant_id).first()
        if case is None:
            errors.append(ImportRowError(offset, E.import_case_not_found(case_id)))
            continue
        if case.status == CaseStatus.CLOSED:
            errors.append(ImportRowError(offset, E.import_case_closed(case_id, case.title)))
            continue

        assigned = (
            db.query(CaseAssignment)
            .filter(
                CaseAssignment.tenant_id == tenant_id,
                CaseAssignment.case_id == case_id,
                CaseAssignment.membership_id == lawyer_membership.id,
            )
            .first()
        )
        if assigned is None:
            errors.append(ImportRowError(offset, E.import_lawyer_not_assigned(case_id)))
            continue

        duplicate_key = (case_id, lawyer_membership.id, row_date, hours, description or "")
        if duplicate_key in seen_in_file:
            errors.append(ImportRowError(offset, E.import_duplicate_within_file(seen_in_file[duplicate_key])))
            continue
        existing = (
            db.query(WorkLog)
            .filter(
                WorkLog.tenant_id == tenant_id,
                WorkLog.case_id == case_id,
                WorkLog.lawyer_id == lawyer_membership.id,
                WorkLog.date == row_date,
                WorkLog.hours == hours,
                WorkLog.description.is_(None) if not description else WorkLog.description == description,
            )
            .first()
        )
        if existing is not None:
            errors.append(ImportRowError(offset, E.import_duplicate_of_existing()))
            continue
        seen_in_file[duplicate_key] = offset

        results.append(
            ImportRowResult(
                case_id=case_id,
                lawyer_membership_id=lawyer_membership.id,
                date=row_date,
                hours=hours,
                description=description,
            )
        )

    if errors:
        return [], errors
    return results, []
