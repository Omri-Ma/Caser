from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from client_api.core.file_validation import MAX_IMPORT_FILE_SIZE_BYTES, is_xlsx_file
from client_api.schemas.work_log_import import WorkLogImportErrorResponse, WorkLogImportResponse
from shared.database import get_db
from shared.membership import require_role
from shared.models import Case, CaseAssignment, Membership, Tenant, WorkLog
from shared.models.enums import CaseStatus, UserRole, WorkLogSource
from shared.tenant import get_current_tenant
from shared import error_messages as E
from shared.worklog_import import build_template_workbook, parse_and_validate_import

# Deliberately not nested under /cases/{case_id} like the manual work-logs
# router — a lawyer's import template spans every case they're assigned to,
# and one uploaded file can carry rows for more than one of those cases.
router = APIRouter(prefix="/work-logs/import", tags=["work-logs"])

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/template")
def download_import_template(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_role(UserRole.LAWYER)),
):
    """A lawyer's own template — the Case column's dropdown is restricted to
    cases they're currently assigned to and that aren't closed (CLAUDE.md:
    "a typo'd or unauthorized case ID can't even be entered in the first
    place").
    """
    cases = (
        db.query(Case)
        .join(CaseAssignment, CaseAssignment.case_id == Case.id)
        .filter(
            CaseAssignment.tenant_id == tenant.id,
            CaseAssignment.membership_id == membership.id,
            Case.status != CaseStatus.CLOSED,
        )
        .order_by(Case.title)
        .all()
    )
    content = build_template_workbook(cases, include_lawyer_email=False)
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="work_log_import_template.xlsx"'},
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=WorkLogImportResponse)
async def import_work_logs(
    file: UploadFile = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_role(UserRole.LAWYER)),
):
    """Self-import — every row is this lawyer's own hours, no lawyer-email
    column (see admin_api's variant for the bulk, on-someone-else's-behalf
    version). Whole-file validation: any row failing rejects the entire file,
    nothing is written (shared/worklog_import.py enforces the actual rules).
    """
    content = await file.read()
    if len(content) > MAX_IMPORT_FILE_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.FILE_TOO_LARGE)
    if not is_xlsx_file(content):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.UNSUPPORTED_FILE_TYPE_XLSX)

    results, errors = parse_and_validate_import(
        content, tenant.id, db, include_lawyer_email=False, self_membership=membership
    )
    if errors:
        body = WorkLogImportErrorResponse(
            error=E.import_failed_summary(len(errors)),
            row_errors=[{"row": e.row, "message": e.message} for e in errors],
        )
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=body.model_dump())

    for result in results:
        db.add(
            WorkLog(
                tenant_id=tenant.id,
                case_id=result.case_id,
                lawyer_id=result.lawyer_membership_id,
                date=result.date,
                hours=result.hours,
                description=result.description,
                source=WorkLogSource.EXCEL_IMPORT,
            )
        )
    db.commit()
    return WorkLogImportResponse(imported_count=len(results))
