from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from client_api.core.case_access import get_assigned_case
from client_api.core.pagination import Page, PageParams, paginate
from client_api.schemas.work_logs import CreateWorkLogRequest, UpdateWorkLogRequest, WorkLogResponse
from shared.database import get_db
from shared.membership import require_role
from shared.models import AuditLog, Case, Identity, Membership, Tenant, WorkLog
from shared.models.enums import CaseStatus, UserRole
from shared.scoped import get_tenant_scoped
from shared.tenant import get_current_tenant
from shared import error_messages as E

# Lawyer-only, never client — CLAUDE.md: "WorkLogs are never client-visible,"
# so require_role only ever lists LAWYER here, unlike documents.py which also
# allows CLIENT.
router = APIRouter(prefix="/cases/{case_id}/work-logs", tags=["work-logs"])


def _get_case_work_log(case: Case, work_log_id: int, tenant: Tenant, db: Session) -> WorkLog:
    work_log = get_tenant_scoped(WorkLog, work_log_id, tenant.id, db, E.WORK_LOG_NOT_FOUND)
    if work_log.case_id != case.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=E.WORK_LOG_NOT_FOUND)
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


@router.post("", response_model=WorkLogResponse, status_code=status.HTTP_201_CREATED)
def create_work_log(
    case_id: int,
    payload: CreateWorkLogRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_role(UserRole.LAWYER)),
):
    """Manual entry — the case must be one this lawyer is currently assigned
    to, and not closed (CLAUDE.md: a closed case blocks new WorkLogs the same
    way it blocks new Documents).
    """
    case = get_assigned_case(case_id, tenant, membership, db)

    if case.status == CaseStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.CASE_CLOSED_CANNOT_ADD_WORK_LOGS)

    work_log = WorkLog(
        tenant_id=tenant.id,
        case_id=case.id,
        lawyer_id=membership.id,
        date=payload.date,
        hours=payload.hours,
        description=payload.description,
    )
    db.add(work_log)
    db.commit()
    db.refresh(work_log)
    return _to_response(work_log, db)


@router.get("", response_model=Page[WorkLogResponse])
def list_work_logs(
    case_id: int,
    params: PageParams = Depends(),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_role(UserRole.LAWYER)),
):
    case = get_assigned_case(case_id, tenant, membership, db)

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
    membership: Membership = Depends(require_role(UserRole.LAWYER)),
):
    """Any lawyer assigned to the case can edit any entry on it, not just
    their own (CLAUDE.md: same broad, collaborative authority as Documents).
    Locked entirely once the case is closed — same cutoff as creating new
    entries, one consistent "closed means frozen" rule. Every edit is logged
    in AuditLogs (who changed which entry, when — not before/after values).
    """
    case = get_assigned_case(case_id, tenant, membership, db)
    work_log = _get_case_work_log(case, work_log_id, tenant, db)

    if case.status == CaseStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.CASE_CLOSED_CANNOT_EDIT_WORK_LOGS)

    work_log.date = payload.date
    work_log.hours = payload.hours
    work_log.description = payload.description
    db.add(
        AuditLog(
            tenant_id=tenant.id,
            user_id=membership.id,
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
    membership: Membership = Depends(require_role(UserRole.LAWYER)),
):
    case = get_assigned_case(case_id, tenant, membership, db)
    work_log = _get_case_work_log(case, work_log_id, tenant, db)

    if case.status == CaseStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.CASE_CLOSED_CANNOT_DELETE_WORK_LOGS)

    db.add(
        AuditLog(
            tenant_id=tenant.id,
            user_id=membership.id,
            action="work_log_deleted",
            target=f"work_log:{work_log.id}",
        )
    )
    db.delete(work_log)
    db.commit()
