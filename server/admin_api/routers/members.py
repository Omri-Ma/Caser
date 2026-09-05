from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from admin_api.schemas.auth import AddMemberRequest, MembershipResponse
from shared.database import get_db
from shared.membership import require_role
from shared.models import Identity, Membership, Tenant
from shared.models.enums import UserRole
from shared.tenant import get_current_tenant

router = APIRouter(prefix="/members", tags=["members"])


@router.post("", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
def add_member(
    payload: AddMemberRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Attach an existing global account to this firm, by email — no new
    password is created, the person logs in with their existing account.
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
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already a member of this firm")

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
