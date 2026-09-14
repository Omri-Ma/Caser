from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from admin_api.core.file_validation import MAX_IMPORT_FILE_SIZE_BYTES, is_xlsx_file
from admin_api.schemas.work_log_import import WorkLogImportErrorResponse, WorkLogImportResponse
from shared.database import get_db
from shared.membership import require_role
from shared.models import AuditLog, Case, Identity, Membership, Tenant, WorkLog
from shared.models.enums import CaseStatus, UserRole, WorkLogSource
from shared.tenant import get_current_tenant
from shared import error_messages as E
from shared.worklog_import import build_template_workbook, parse_and_validate_import

router = APIRouter(prefix="/work-logs/import", tags=["work-logs"])

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/template")
def download_import_template(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """office_manager's bulk variant — adds the Lawyer Email column. The
    Case dropdown can't be scoped per-lawyer the way the self-import
    template is (a single sheet can't know ahead of time which lawyer's
    email ends up in a given row), so it offers every non-closed case at the
    tenant instead — row validation below still rejects a case the resolved
    lawyer isn't actually assigned to.
    """
    cases = (
        db.query(Case)
        .filter(Case.tenant_id == tenant.id, Case.status != CaseStatus.CLOSED)
        .order_by(Case.title)
        .all()
    )
    lawyer_emails = [
        email
        for (email,) in db.query(Identity.email)
        .join(Membership, Membership.identity_id == Identity.id)
        .filter(
            Membership.tenant_id == tenant.id,
            Membership.role == UserRole.LAWYER,
            Membership.active.is_(True),
        )
        .order_by(Identity.email)
        .all()
    ]
    content = build_template_workbook(cases, include_lawyer_email=True, lawyer_emails=lawyer_emails)
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="work_log_bulk_import_template.xlsx"'},
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=WorkLogImportResponse)
async def import_work_logs(
    file: UploadFile = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Bulk, on-someone-else's-behalf import across multiple lawyers at
    once. `WorkLogs.lawyer_id` still records whose billable hours each row
    is (resolved per-row by email), kept separate from who performed the
    import — that's recorded here as a single AuditLogs entry for the whole
    batch (CLAUDE.md: "that's recorded in AuditLogs — who actually triggered
    the import").
    """
    content = await file.read()
    if len(content) > MAX_IMPORT_FILE_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.FILE_TOO_LARGE)
    if not is_xlsx_file(content):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.UNSUPPORTED_FILE_TYPE_XLSX)

    results, errors = parse_and_validate_import(content, tenant.id, db, include_lawyer_email=True)
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
    db.add(
        AuditLog(
            tenant_id=tenant.id,
            user_id=office_manager.id,
            action="work_log_excel_imported",
            target=f"{len(results)} entries from {file.filename}",
        )
    )
    db.commit()
    return WorkLogImportResponse(imported_count=len(results))
