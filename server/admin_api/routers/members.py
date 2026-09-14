from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from admin_api.core.pagination import Page, PageParams
from admin_api.schemas.auth import MemberResponse
from shared.database import get_db
from shared.membership import require_role
from shared.models import AuditLog, Identity, Membership, Tenant
from shared.models.enums import UserRole
from shared.scoped import get_tenant_scoped
from shared.tenant import get_current_tenant

router = APIRouter(prefix="/members", tags=["members"])


def _to_member_response(membership: Membership, identity: Identity) -> MemberResponse:
    return MemberResponse(
        id=membership.id,
        identity_id=membership.identity_id,
        tenant_id=membership.tenant_id,
        role=membership.role,
        identity_name=identity.name,
        identity_email=identity.email,
        active=membership.active,
    )


@router.get("", response_model=Page[MemberResponse])
def list_members(
    role: Optional[UserRole] = Query(None),
    active: bool = Query(True),
    params: PageParams = Depends(),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Real (accepted) memberships at this firm, optionally filtered by
    role — powers pickers like the case-assignment modal (lawyers/clients
    only, never office managers/super_admin) as well as the members
    screen's "active"/"removed" tabs. `active` is an exclusive filter (not
    an "also include" toggle) so it maps directly onto those two tabs —
    the third tab, pending invites, comes from GET /invites instead, since
    a pending invite isn't a Membership row at all yet.
    """
    query = (
        db.query(Membership, Identity)
        .join(Identity, Membership.identity_id == Identity.id)
        .filter(Membership.tenant_id == tenant.id, Membership.active.is_(active))
    )
    if role is not None:
        query = query.filter(Membership.role == role)
    query = query.order_by(Identity.name)

    total = query.count()
    rows = query.offset((params.page - 1) * params.page_size).limit(params.page_size).all()
    items = [_to_member_response(membership, identity) for membership, identity in rows]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.post("/{membership_id}/deactivate", response_model=MemberResponse)
def deactivate_member(
    membership_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Soft delete (CLAUDE.md's Memberships.active) — removes them from every
    "who currently works here" query and (via get_current_membership /
    the login routes) actually revokes their access to this firm, while
    WorkLogs/Documents/CaseAssignments/AuditLogs referencing this
    membership_id keep resolving correctly regardless.
    """
    membership = get_tenant_scoped(Membership, membership_id, tenant.id, db, "Member not found")
    if membership.id == office_manager.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can't deactivate your own membership")

    membership.active = False
    db.add(
        AuditLog(
            tenant_id=tenant.id,
            user_id=office_manager.id,
            action="member_deactivated",
            target=f"membership:{membership.id}",
        )
    )
    db.commit()
    db.refresh(membership)

    identity = db.query(Identity).filter(Identity.id == membership.identity_id).first()
    return _to_member_response(membership, identity)
