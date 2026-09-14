import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from admin_api.core.pagination import Page, PageParams
from admin_api.schemas.auth import InviteMemberRequest, InviteResponse
from shared.database import get_db
from shared.dev_outbox import write_dev_outbox
from shared.invites import DuplicateInviteError, create_invite
from shared.membership import require_role
from shared.models import Identity, Membership, MembershipInvite, Tenant
from shared.models.enums import InviteStatus, UserRole
from shared.plan_limits import check_plan_limit
from shared.tenant import BASE_DOMAIN, get_current_tenant
from shared import error_messages as E

router = APIRouter(prefix="/invites", tags=["invites"])

# /register is only routed on a tenant subdomain in client/'s App.jsx (not
# the lobby), so the invite link points at *this* tenant's own subdomain —
# admin_api already knows it (it's the tenant the invite belongs to). Only
# the client app's port isn't knowable from this request (its Origin header
# is admin/'s own, not client/'s — unlike forgot-password's link, which is
# built from the *calling* app's own Origin), so that's the one piece that
# needs its own env var.
CLIENT_APP_PORT = os.getenv("CLIENT_APP_PORT", "5173")


def _to_invite_response(invite: MembershipInvite, inviter_identity: Identity) -> InviteResponse:
    return InviteResponse(
        id=invite.id,
        tenant_id=invite.tenant_id,
        email=invite.email,
        role=invite.role,
        status=invite.status,
        created_at=invite.created_at,
        invited_by_name=inviter_identity.name,
    )


@router.get("", response_model=Page[InviteResponse])
def list_invites(
    status_filter: InviteStatus = Query(InviteStatus.PENDING, alias="status"),
    role: Optional[UserRole] = Query(None),
    params: PageParams = Depends(),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Powers the Members screen's "pending" tab (and, with status=declined,
    a history view if ever needed) — a separate list from GET /members
    since a pending invite isn't a Membership row at all yet.
    """
    query = (
        db.query(MembershipInvite, Identity)
        .join(Membership, MembershipInvite.invited_by == Membership.id)
        .join(Identity, Membership.identity_id == Identity.id)
        .filter(MembershipInvite.tenant_id == tenant.id, MembershipInvite.status == status_filter)
    )
    if role is not None:
        query = query.filter(MembershipInvite.role == role)
    query = query.order_by(MembershipInvite.created_at.desc())

    total = query.count()
    rows = query.offset((params.page - 1) * params.page_size).limit(params.page_size).all()
    items = [_to_invite_response(invite, identity) for invite, identity in rows]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.post("", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
def invite_member(
    payload: InviteMemberRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Invite a lawyer or client to this firm — replaces the old instant
    POST /members (CLAUDE.md's MembershipInvites note): adding someone to a
    firm is a request now, not an instant action, whether or not they
    already have an Identity elsewhere in the system.
    """
    if payload.role not in (UserRole.LAWYER, UserRole.CLIENT):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.ONLY_LAWYER_CLIENT_INVITES_SUPPORTED)

    if payload.role == UserRole.LAWYER:
        # Pending invites count toward the limit too (CLAUDE.md) — see
        # shared/plan_limits.py's count_pending_lawyer_invites.
        check_plan_limit(tenant.id, "lawyer_count", db, additional=1)

    try:
        invite = create_invite(tenant.id, payload.email, payload.role, office_manager.id, db)
    except DuplicateInviteError as err:
        # DuplicateInviteError already carries a Hebrew message (shared/invites.py).
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    # An email with no Identity yet has nowhere to log in and see the
    # invite, so it goes out through the dev-outbox stand-in instead
    # (CLAUDE.md's MembershipInvites note) — an email that already has an
    # Identity sees it the next time they log in (client/'s lobby resolves
    # it), no delivery step needed.
    identity = db.query(Identity).filter(Identity.email == payload.email).first()
    if identity is None:
        link = f"http://{tenant.subdomain}.{BASE_DOMAIN}:{CLIENT_APP_PORT}/register?email={payload.email}"
        write_dev_outbox(payload.email, link)

    inviter_identity = db.query(Identity).filter(Identity.id == office_manager.identity_id).first()
    return _to_invite_response(invite, inviter_identity)
