from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from shared.membership import get_current_membership
from shared.models import Case, CaseAssignment, Membership, Tenant
from shared.models.enums import UserRole
from shared.scoped import get_tenant_scoped
from shared import error_messages as E


def has_full_case_visibility(membership: Membership) -> bool:
    """A lawyer holding the office_manager-set Memberships.is_manager flag
    gets the same automatic full-tenant case visibility office_manager
    already has in admin_api (CLAUDE.md's Memberships/CaseAssignments
    note) — orthogonal to role: this lawyer never becomes a firm
    administrator, only a case overseer. Always False for a client
    membership (is_manager is meaningless there and never set).
    """
    return membership.role == UserRole.LAWYER and bool(membership.is_manager)


def get_assigned_case(case_id: int, tenant: Tenant, membership: Membership, db: Session) -> Case:
    """Resolve tenant-scoped first (404 if the case isn't even this tenant's).
    A manager-authority lawyer (has_full_case_visibility) skips the
    assignment check entirely, same as office_manager's oversight in
    admin_api; everyone else needs an explicit CaseAssignment (403 if the
    case exists here but isn't assigned to this membership). Shared by
    documents.py, work_logs.py, and narratives.py, all of which gate every
    route behind "can this membership actually see this case."
    """
    case = get_tenant_scoped(Case, case_id, tenant.id, db, E.CASE_NOT_FOUND)
    if has_full_case_visibility(membership):
        return case
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=E.NOT_ASSIGNED_TO_CASE)
    return case


def require_manager_lawyer(membership: Membership = Depends(get_current_membership)) -> Membership:
    """Route dependency gating client_api's narrative generation/export
    (CLAUDE.md's Narratives note) — manager-level case-oversight authority,
    not just any assigned lawyer: a lawyer without Memberships.is_manager
    set, or a client, is rejected outright.
    """
    if not has_full_case_visibility(membership):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=E.NOT_ALLOWED_FOR_ROLE)
    return membership
