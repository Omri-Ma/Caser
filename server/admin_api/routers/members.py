from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from admin_api.core.pagination import Page, PageParams, paginate
from admin_api.schemas.auth import (
    AddMemberRequest,
    MemberResponse,
    MembershipResponse,
    ResetMemberPasswordRequest,
)
from shared.database import get_db
from shared.membership import require_role
from shared.models import AuditLog, Identity, Membership, Tenant
from shared.models.enums import UserRole
from shared.plan_limits import check_plan_limit
from shared.scoped import get_tenant_scoped
from shared.security import hash_password
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
    include_inactive: bool = Query(False),
    params: PageParams = Depends(),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Currently-active members at this firm, optionally filtered by role —
    powers pickers like the case-assignment modal (lawyers/clients only,
    never office managers/super_admin) as well as the members screen. Same
    "active = true" convention as every other "who currently works here"
    query (see CLAUDE.md's Memberships.active note). `include_inactive` is
    the one exception — the members screen itself needs to also show
    deactivated people (to re-add them), pickers never pass it.
    """
    query = (
        db.query(Membership, Identity)
        .join(Identity, Membership.identity_id == Identity.id)
        .filter(Membership.tenant_id == tenant.id)
    )
    if not include_inactive:
        query = query.filter(Membership.active.is_(True))
    if role is not None:
        query = query.filter(Membership.role == role)
    query = query.order_by(Identity.name)

    total = query.count()
    rows = query.offset((params.page - 1) * params.page_size).limit(params.page_size).all()
    items = [_to_member_response(membership, identity) for membership, identity in rows]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.post("", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
def add_member(
    payload: AddMemberRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Attach an existing global account to this firm, by email — no new
    password is created, the person logs in with their existing account.

    If this identity already has an *inactive* Membership at this tenant
    (someone previously removed), that row is reactivated in place instead
    of inserting a new one — a fresh insert would fail the identity_id+
    tenant_id unique constraint while the old row still exists, active or
    not (CLAUDE.md's Memberships.active note).
    """
    identity = db.query(Identity).filter(Identity.email == payload.email).first()
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with that email — ask them to register first",
        )

    existing = (
        db.query(Membership)
        .filter(Membership.identity_id == identity.id, Membership.tenant_id == tenant.id)
        .first()
    )
    if existing is not None and existing.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already a member of this firm")

    if payload.role == UserRole.LAWYER:
        check_plan_limit(tenant.id, "lawyer_count", db, additional=1)

    if existing is not None:
        existing.active = True
        existing.role = payload.role
        db.commit()
        db.refresh(existing)
        return MembershipResponse(id=existing.id, identity_id=existing.identity_id, tenant_id=existing.tenant_id, role=existing.role)

    membership = Membership(identity_id=identity.id, tenant_id=tenant.id, role=payload.role)
    db.add(membership)
    try:
        db.commit()
    except IntegrityError:
        # Pre-check above is a race, not a guard on its own — two concurrent
        # adds can both pass it before either has written a row.
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already a member of this firm")
    db.refresh(membership)

    return MembershipResponse(
        id=membership.id,
        identity_id=membership.identity_id,
        tenant_id=membership.tenant_id,
        role=membership.role,
    )


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


@router.post("/{membership_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_member_password(
    membership_id: int,
    payload: ResetMemberPasswordRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """office_manager sets a new password for a member by hand — the interim
    stand-in for real password recovery (CLAUDE.md's Future additions).
    Bumps token_version so any of the member's outstanding sessions are
    invalidated too, same as a self-service password change would.
    """
    membership = get_tenant_scoped(Membership, membership_id, tenant.id, db, "Member not found")
    identity = db.query(Identity).filter(Identity.id == membership.identity_id).first()

    identity.password_hash = hash_password(payload.new_password)
    identity.token_version += 1
    db.add(
        AuditLog(
            tenant_id=tenant.id,
            user_id=office_manager.id,
            action="member_password_reset",
            target=f"membership:{membership.id}",
        )
    )
    db.commit()
