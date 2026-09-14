from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from client_api.schemas.auth import AcceptInviteResponse, PendingInviteOption
from shared.database import get_db
from shared.identity import get_current_identity
from shared.invites import accept_invite, decline_invite
from shared.models import Identity, MembershipInvite, Tenant
from shared.models.enums import InviteStatus

router = APIRouter(prefix="/invites", tags=["invites"])

# Deliberately not tenant-scoped (no get_current_tenant dependency) — a
# MembershipInvite is looked up by email match against the logged-in
# identity, same as the lobby-login flow that surfaces these in the first
# place. Reachable from the lobby right after login, or from within an
# already-active tenant session (an identity can hold a membership at one
# firm and a pending invite at another simultaneously).


def _get_own_pending_invite(invite_id: int, identity: Identity, db: Session) -> MembershipInvite:
    invite = (
        db.query(MembershipInvite)
        .filter(
            MembershipInvite.id == invite_id,
            MembershipInvite.email == identity.email,
            MembershipInvite.status == InviteStatus.PENDING,
        )
        .first()
    )
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    return invite


@router.get("", response_model=list[PendingInviteOption])
def list_my_invites(identity: Identity = Depends(get_current_identity), db: Session = Depends(get_db)):
    rows = (
        db.query(MembershipInvite, Tenant)
        .join(Tenant, MembershipInvite.tenant_id == Tenant.id)
        .filter(MembershipInvite.email == identity.email, MembershipInvite.status == InviteStatus.PENDING)
        .all()
    )
    return [
        PendingInviteOption(
            invite_id=invite.id, tenant_id=tenant.id, subdomain=tenant.subdomain, firm_name=tenant.name, role=invite.role
        )
        for invite, tenant in rows
    ]


@router.post("/{invite_id}/accept", response_model=AcceptInviteResponse)
def accept_my_invite(invite_id: int, identity: Identity = Depends(get_current_identity), db: Session = Depends(get_db)):
    invite = _get_own_pending_invite(invite_id, identity, db)
    accept_invite(invite, identity, db)
    tenant = db.query(Tenant).filter(Tenant.id == invite.tenant_id).first()
    return AcceptInviteResponse(tenant_id=tenant.id, subdomain=tenant.subdomain, firm_name=tenant.name, role=invite.role)


@router.post("/{invite_id}/decline", status_code=status.HTTP_204_NO_CONTENT)
def decline_my_invite(invite_id: int, identity: Identity = Depends(get_current_identity), db: Session = Depends(get_db)):
    invite = _get_own_pending_invite(invite_id, identity, db)
    decline_invite(invite, db)
