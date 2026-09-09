from fastapi import Depends, HTTPException, status

from shared.identity import get_current_identity
from shared.models import Identity


def require_super_admin(identity: Identity = Depends(get_current_identity)) -> Identity:
    """Guards every platform-only route (cross-tenant firm list, suspend/
    reactivate, aggregate stats). Checks Identities.is_super_admin directly,
    never Memberships — super_admin can't be a Memberships row at all (see
    CLAUDE.md's Multi-tenancy architecture), so there's no role to check
    through require_role. This is the one gate every cross-tenant query in
    admin_api sits behind.
    """
    if not identity.is_super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform staff only")
    return identity
