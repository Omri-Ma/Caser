from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from client_api.core.pagination import Page, PageParams, paginate
from client_api.schemas.cases import CaseResponse
from shared.database import get_db
from shared.membership import require_role
from shared.models import Case, CaseAssignment, Membership, Tenant
from shared.models.enums import UserRole
from shared.scoped import get_tenant_scoped
from shared.tenant import get_current_tenant

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=Page[CaseResponse])
def list_my_cases(
    params: PageParams = Depends(),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_role(UserRole.LAWYER, UserRole.CLIENT)),
):
    """Only cases this membership is explicitly assigned to via
    CaseAssignment — unlike office_manager, a lawyer/client has no automatic
    tenant-wide visibility.
    """
    query = (
        db.query(Case)
        .join(CaseAssignment, CaseAssignment.case_id == Case.id)
        .filter(
            Case.tenant_id == tenant.id,
            CaseAssignment.tenant_id == tenant.id,
            CaseAssignment.membership_id == membership.id,
        )
        .order_by(Case.created_at.desc())
    )
    items, total = paginate(query, params)
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/{case_id}", response_model=CaseResponse)
def get_my_case(
    case_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_role(UserRole.LAWYER, UserRole.CLIENT)),
):
    """view only if assigned — the case is resolved tenant-scoped first
    (404 if it doesn't even belong to this tenant), then checked for an
    assignment (403 if it exists here but this membership can't see it).
    """
    case = get_tenant_scoped(Case, case_id, tenant.id, db, "Case not found")

    assigned = (
        db.query(CaseAssignment)
        .filter(
            CaseAssignment.tenant_id == tenant.id,
            CaseAssignment.case_id == case.id,
            CaseAssignment.membership_id == membership.id,
        )
        .first()
    )
    if assigned is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not assigned to this case")

    return case
