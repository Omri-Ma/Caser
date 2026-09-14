from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.identity import get_current_identity
from shared.tenant import get_current_tenant
from shared.models import Identity, Membership, Tenant
from shared import error_messages as E


def get_current_membership(
    identity: Identity = Depends(get_current_identity),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> Membership:
    """Resolve the logged-in identity's role at *this* tenant (from the
    subdomain). This is the "what can they do here" half — the role is
    looked up fresh on every request instead of being baked into the token,
    since one Identity can hold a different role at a different firm.
    """
    membership = (
        db.query(Membership)
        .filter(
            Membership.identity_id == identity.id,
            Membership.tenant_id == tenant.id,
            Membership.active.is_(True),
        )
        .first()
    )
    if membership is None:
        # A deactivated membership (CLAUDE.md's Memberships.active) is
        # indistinguishable from no membership at all here — deactivation
        # has to actually revoke access, not just hide the row from list
        # views, or it wouldn't be a real removal from the firm.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=E.NO_ACCESS_TO_FIRM,
        )
    return membership


def require_role(*allowed_roles):
    """Dependency factory: guard a route to only the given roles, e.g.
    Depends(require_role(UserRole.OFFICE_MANAGER)).
    """

    def _check(membership: Membership = Depends(get_current_membership)) -> Membership:
        if membership.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=E.NOT_ALLOWED_FOR_ROLE)
        return membership

    return _check
