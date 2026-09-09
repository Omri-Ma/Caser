from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from admin_api.core.pagination import Page, PageParams, paginate
from admin_api.schemas.work_logs import UpdateWorkLogRequest, WorkLogResponse
from shared.database import get_db
from shared.membership import require_role
from shared.models import AuditLog, Case, Identity, Membership, Tenant, WorkLog
from shared.models.enums import CaseStatus, UserRole
from shared.scoped import get_tenant_scoped
from shared.tenant import get_current_tenant

router = APIRouter(prefix="/cases/{case_id}/work-logs", tags=["work-logs"])


def _get_case_work_log(case: Case, work_log_id: int, tenant: Tenant, db: Session) -> WorkLog:
    work_log = get_tenant_scoped(WorkLog, work_log_id, tenant.id, db, "Work log entry not found")
    if work_log.case_id != case.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work log entry not found")
    return work_log


def _to_response(work_log: WorkLog, db: Session) -> WorkLogResponse:
    identity = (
        db.query(Identity)
        .join(Membership, Membership.identity_id == Identity.id)
        .filter(Membership.id == work_log.lawyer_id)
        .first()
    )
    return WorkLogResponse(
        id=work_log.id,
        case_id=work_log.case_id,
        lawyer_id=work_log.lawyer_id,
        lawyer_name=identity.name if identity else "Unknown",
        date=work_log.date,
        hours=work_log.hours,
        description=work_log.description,
        source=work_log.source,
    )


@router.get("", response_model=Page[WorkLogResponse])
def list_work_logs(
    case_id: int,
    params: PageParams = Depends(),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """office_manager sees every case's work logs automatically — no
    CaseAssignment check, same oversight authority as Documents.
    """
    case = get_tenant_scoped(Case, case_id, tenant.id, db, "Case not found")

    query = (
        db.query(WorkLog, Identity)
        .join(Membership, WorkLog.lawyer_id == Membership.id)
        .join(Identity, Membership.identity_id == Identity.id)
        .filter(WorkLog.tenant_id == tenant.id, WorkLog.case_id == case.id)
        .order_by(WorkLog.date.desc(), WorkLog.id.desc())
    )
    rows, total = paginate(query, params)
    items = [
        WorkLogResponse(
            id=work_log.id,
            case_id=work_log.case_id,
            lawyer_id=work_log.lawyer_id,
            lawyer_name=identity.name,
            date=work_log.date,
            hours=work_log.hours,
            description=work_log.description,
            source=work_log.source,
        )
        for work_log, identity in rows
    ]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.patch("/{work_log_id}", response_model=WorkLogResponse)
def update_work_log(
    case_id: int,
    work_log_id: int,
    payload: UpdateWorkLogRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """office_manager gets the same broad edit authority as any assigned
    lawyer (CLAUDE.md: "office_manager can too, as with everything else").
    Locked once the case is closed, same as the lawyer-facing route.
    """
    case = get_tenant_scoped(Case, case_id, tenant.id, db, "Case not found")
    work_log = _get_case_work_log(case, work_log_id, tenant, db)

    if case.status == CaseStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This case is closed — work log entries can't be edited")

    work_log.date = payload.date
    work_log.hours = payload.hours
    work_log.description = payload.description
    db.add(
        AuditLog(
            tenant_id=tenant.id,
            user_id=office_manager.id,
            action="work_log_edited",
            target=f"work_log:{work_log.id}",
        )
    )
    db.commit()
    db.refresh(work_log)
    return _to_response(work_log, db)


@router.delete("/{work_log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_work_log(
    case_id: int,
    work_log_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    case = get_tenant_scoped(Case, case_id, tenant.id, db, "Case not found")
    work_log = _get_case_work_log(case, work_log_id, tenant, db)

    if case.status == CaseStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This case is closed — work log entries can't be deleted")

    db.add(
        AuditLog(
            tenant_id=tenant.id,
            user_id=office_manager.id,
            action="work_log_deleted",
            target=f"work_log:{work_log.id}",
        )
    )
    db.delete(work_log)
    db.commit()
