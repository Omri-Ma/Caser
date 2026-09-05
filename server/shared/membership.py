from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.identity import get_current_identity
from shared.tenant import get_current_tenant
from shared.models import Identity, Membership, Tenant


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
        .filter(Membership.identity_id == identity.id, Membership.tenant_id == tenant.id)
        .first()
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this firm",
        )
    return membership


def require_role(*allowed_roles):
    """Dependency factory: guard a route to only the given roles, e.g.
    Depends(require_role(UserRole.OFFICE_MANAGER)).
    """

    def _check(membership: Membership = Depends(get_current_membership)) -> Membership:
        if membership.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for your role")
        return membership

    return _check
