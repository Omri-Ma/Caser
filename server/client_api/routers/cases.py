from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from client_api.core.case_access import get_assigned_case, has_full_case_visibility
from client_api.core.pagination import Page, PageParams, paginate
from client_api.schemas.cases import CaseResponse
from shared.database import get_db
from shared.membership import require_role
from shared.models import Case, CaseAssignment, CaseTag, Membership, Tenant
from shared.models.enums import CaseStatus, PracticeArea, UserRole
from shared.tenant import get_current_tenant

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=Page[CaseResponse])
def list_my_cases(
    search: Optional[str] = Query(None, description="Partial, case-insensitive match on case title"),
    status_filter: Optional[CaseStatus] = Query(None, alias="status"),
    practice_area: Optional[PracticeArea] = Query(None, description="Filter to cases carrying this tag"),
    params: PageParams = Depends(),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_role(UserRole.LAWYER, UserRole.CLIENT)),
):
    """Only cases this membership is explicitly assigned to via
    CaseAssignment — unless it has full tenant-wide visibility, either as
    office_manager (never reaches this router) or a lawyer with
    Memberships.is_manager set (CLAUDE.md's CaseAssignments note), the same
    automatic oversight office_manager already has in admin_api. Optional
    server-side title search + status + practice-area tag filter, same as
    the admin case list.
    """
    if has_full_case_visibility(membership):
        query = db.query(Case).filter(Case.tenant_id == tenant.id)
    else:
        query = (
            db.query(Case)
            .join(CaseAssignment, CaseAssignment.case_id == Case.id)
            .filter(
                Case.tenant_id == tenant.id,
                CaseAssignment.tenant_id == tenant.id,
                CaseAssignment.membership_id == membership.id,
            )
        )
    if search:
        query = query.filter(Case.title.ilike(f"%{search}%"))
    if status_filter is not None:
        query = query.filter(Case.status == status_filter)
    if practice_area is not None:
        query = query.join(CaseTag, CaseTag.case_id == Case.id).filter(CaseTag.practice_area == practice_area)
    query = query.order_by(Case.created_at.desc())
    items, total = paginate(query, params)
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/{case_id}", response_model=CaseResponse)
def get_my_case(
    case_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_role(UserRole.LAWYER, UserRole.CLIENT)),
):
    """View only if assigned — or, as of Memberships.is_manager, if this
    membership has full tenant-wide case visibility instead. Delegates to
    the same get_assigned_case helper documents.py/work_logs.py/
    narratives.py already use, rather than duplicating the assignment
    check inline.
    """
    return get_assigned_case(case_id, tenant, membership, db)
