from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from admin_api.core.pagination import Page, PageParams, paginate
from admin_api.schemas.cases import (
    AssignCaseRequest,
    CaseAssignmentResponse,
    CaseResponse,
    CreateCaseRequest,
    UpdateCaseStatusRequest,
    UpdateCaseTitleRequest,
)
from shared.database import get_db
from shared.membership import require_role
from shared.models import Case, CaseAssignment, Identity, Membership, Tenant
from shared.models.enums import UserRole
from shared.scoped import get_tenant_scoped
from shared.tenant import get_current_tenant

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: CreateCaseRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    case = Case(tenant_id=tenant.id, title=payload.title)
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.get("", response_model=Page[CaseResponse])
def list_cases(
    params: PageParams = Depends(),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """office_manager sees every case at their own tenant automatically —
    no CaseAssignment row needed, unlike a lawyer/client.
    """
    query = db.query(Case).filter(Case.tenant_id == tenant.id).order_by(Case.created_at.desc())
    items, total = paginate(query, params)
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    case_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    return get_tenant_scoped(Case, case_id, tenant.id, db, "Case not found")


@router.patch("/{case_id}", response_model=CaseResponse)
def update_case_title(
    case_id: int,
    payload: UpdateCaseTitleRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Editing case metadata is office_manager-only — lawyers work within a
    case, office_manager controls its administrative facts.
    """
    case = get_tenant_scoped(Case, case_id, tenant.id, db, "Case not found")
    case.title = payload.title
    db.commit()
    db.refresh(case)
    return case


@router.patch("/{case_id}/status", response_model=CaseResponse)
def update_case_status(
    case_id: int,
    payload: UpdateCaseStatusRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """office_manager-only, no restriction on timing — reopening a closed
    case is explicitly allowed, same as any other transition.
    """
    case = get_tenant_scoped(Case, case_id, tenant.id, db, "Case not found")
    case.status = payload.status
    db.commit()
    db.refresh(case)
    return case


@router.get("/{case_id}/assignments", response_model=Page[CaseAssignmentResponse])
def list_case_assignments(
    case_id: int,
    params: PageParams = Depends(),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    case = get_tenant_scoped(Case, case_id, tenant.id, db, "Case not found")
    query = (
        db.query(CaseAssignment, Membership, Identity)
        .join(Membership, CaseAssignment.membership_id == Membership.id)
        .join(Identity, Membership.identity_id == Identity.id)
        .filter(CaseAssignment.tenant_id == tenant.id, CaseAssignment.case_id == case.id)
        .order_by(CaseAssignment.id)
    )
    total = query.count()
    rows = query.offset((params.page - 1) * params.page_size).limit(params.page_size).all()
    items = [
        CaseAssignmentResponse(
            id=assignment.id,
            case_id=assignment.case_id,
            membership_id=assignment.membership_id,
            role=membership.role,
            identity_name=identity.name,
            identity_email=identity.email,
        )
        for assignment, membership, identity in rows
    ]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.post("/{case_id}/assignments", response_model=CaseAssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_to_case(
    case_id: int,
    payload: AssignCaseRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Assign a lawyer or client membership to a case. Both the case and the
    membership are resolved through get_tenant_scoped — a bare id lookup on
    either would only prove the row exists *somewhere*, not that it belongs
    to this tenant.
    """
    case = get_tenant_scoped(Case, case_id, tenant.id, db, "Case not found")
    membership = get_tenant_scoped(Membership, payload.membership_id, tenant.id, db, "Membership not found")

    if membership.role not in (UserRole.LAWYER, UserRole.CLIENT):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only lawyers and clients can be assigned to a case — an office manager already has access to every case",
        )

    existing = (
        db.query(CaseAssignment)
        .filter(CaseAssignment.case_id == case.id, CaseAssignment.membership_id == membership.id)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already assigned to this case")

    assignment = CaseAssignment(tenant_id=tenant.id, case_id=case.id, membership_id=membership.id)
    db.add(assignment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already assigned to this case")
    db.refresh(assignment)

    identity = db.query(Identity).filter(Identity.id == membership.identity_id).first()
    return CaseAssignmentResponse(
        id=assignment.id,
        case_id=assignment.case_id,
        membership_id=assignment.membership_id,
        role=membership.role,
        identity_name=identity.name,
        identity_email=identity.email,
    )


@router.delete("/{case_id}/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_from_case(
    case_id: int,
    assignment_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Real (hard) delete — nothing else references case_assignments.id, so
    there's no history-preservation reason to soft-delete it. Immediate,
    full loss of access to that case, including documents/hours already
    tied to it (CaseAssignment is the one access gate, no carve-outs).
    """
    case = get_tenant_scoped(Case, case_id, tenant.id, db, "Case not found")
    assignment = get_tenant_scoped(CaseAssignment, assignment_id, tenant.id, db, "Assignment not found")
    if assignment.case_id != case.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    db.delete(assignment)
    db.commit()
