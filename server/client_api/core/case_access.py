from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from shared.models import Case, CaseAssignment, Membership, Tenant
from shared.scoped import get_tenant_scoped


def get_assigned_case(case_id: int, tenant: Tenant, membership: Membership, db: Session) -> Case:
    """Resolve tenant-scoped first (404 if the case isn't even this tenant's),
    then require an explicit CaseAssignment (403 if it exists here but isn't
    assigned to this membership) — lawyers and clients alike have no
    automatic case access. Shared by documents.py and work_logs.py, both of
    which gate every route behind "is this membership actually on this case."
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
