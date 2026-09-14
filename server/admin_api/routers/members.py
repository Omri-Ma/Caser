from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from admin_api.core.pagination import Page, PageParams
from admin_api.schemas.auth import MemberResponse, UpdateMemberRoleRequest, UpdatePublicVisibilityRequest
from shared.database import get_db
from shared.membership import require_role
from shared.models import AuditLog, Identity, Membership, Tenant
from shared.models.enums import UserRole
from shared.scoped import get_tenant_scoped
from shared.tenant import get_current_tenant
from shared import error_messages as E

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
        show_on_public_page=membership.show_on_public_page,
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
    membership = get_tenant_scoped(Membership, membership_id, tenant.id, db, E.MEMBER_NOT_FOUND)
    if membership.id == office_manager.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.CANNOT_DEACTIVATE_OWN_MEMBERSHIP)

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


@router.patch("/{membership_id}/role", response_model=MemberResponse)
def update_member_role(
    membership_id: int,
    payload: UpdateMemberRoleRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Promote a lawyer to office_manager, or demote an office_manager back
    to lawyer, at this office_manager's own firm (CLAUDE.md's Memberships
    note). Never touches a client membership — UpdateMemberRoleRequest's
    schema already restricts the *target* role to office_manager/lawyer,
    and this additionally rejects a *source* membership that's a client, so
    a client can never be promoted this way either.

    Deliberately allows changing your own role (including an office_manager
    demoting themselves) with no "last office_manager standing" guard: this
    is the exact mechanism CLAUDE.md's Memberships note relies on to make
    self-service firm-leaving safe to allow at all ("any office_manager can
    promote someone else before or after the fact, so a firm is never
    actually strandable") — adding a block here would be inconsistent with
    that reasoning, and super_admin remains the last-resort fallback either
    way.
    """
    membership = get_tenant_scoped(Membership, membership_id, tenant.id, db, E.MEMBER_NOT_FOUND)
    if membership.role not in (UserRole.OFFICE_MANAGER, UserRole.LAWYER):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.ROLE_CHANGE_ONLY_FOR_LAWYER_OR_MANAGER)
    if not membership.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.MEMBERSHIP_NOT_ACTIVE)

    membership.role = payload.role
    db.add(
        AuditLog(
            tenant_id=tenant.id,
            user_id=office_manager.id,
            action=f"member_role_changed_to_{payload.role.value}",
            target=f"membership:{membership.id}",
        )
    )
    db.commit()
    db.refresh(membership)

    identity = db.query(Identity).filter(Identity.id == membership.identity_id).first()
    return _to_member_response(membership, identity)


@router.patch("/{membership_id}/public-visibility", response_model=MemberResponse)
def update_public_visibility(
    membership_id: int,
    payload: UpdatePublicVisibilityRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Whether this person's profile (Identity.bio/photo_url) appears on
    this firm's public team section (CLAUDE.md's Memberships note) —
    office_manager-only to set, since it's the firm's public page, not the
    individual's. Only office_manager/lawyer memberships are eligible: a
    client is never "the firm" the way staff are, and an inactive
    membership has nothing to show publicly in the first place (an active
    row is itself the "genuinely accepted" signal — every Membership row
    now only ever comes to exist via an accepted invite, or a pre-existing
    one predating that flow, either way a real agreed membership).
    """
    membership = get_tenant_scoped(Membership, membership_id, tenant.id, db, E.MEMBER_NOT_FOUND)
    if membership.role not in (UserRole.OFFICE_MANAGER, UserRole.LAWYER):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.ONLY_MANAGERS_LAWYERS_ON_PUBLIC_PAGE)
    if not membership.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.MEMBERSHIP_NOT_ACTIVE)

    membership.show_on_public_page = payload.show_on_public_page
    db.commit()
    db.refresh(membership)

    identity = db.query(Identity).filter(Identity.id == membership.identity_id).first()
    return _to_member_response(membership, identity)
