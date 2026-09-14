from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from admin_api.core.pagination import Page, PageParams, paginate
from admin_api.schemas.audit_log import AuditLogEntryResponse
from shared.database import get_db
from shared.membership import require_role
from shared.models import AuditLog, Identity, Membership, Tenant
from shared.models.enums import UserRole
from shared.tenant import get_current_tenant

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


@router.get("", response_model=Page[AuditLogEntryResponse])
def list_audit_log(
    action: Optional[str] = Query(None),
    params: PageParams = Depends(),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Read-only browsing of this tenant's AuditLog — no write path here,
    entries are produced by the actions that already write them (document
    archive/restore/permanent-delete, work log edit/delete, member
    deactivate, narrative PDF export, Excel import). Newest first, same
    tenant-scoped + paginated shape as every other list endpoint.
    """
    query = (
        db.query(AuditLog, Membership, Identity)
        .join(Membership, AuditLog.user_id == Membership.id)
        .join(Identity, Membership.identity_id == Identity.id)
        .filter(AuditLog.tenant_id == tenant.id)
    )
    if action is not None:
        query = query.filter(AuditLog.action == action)
    query = query.order_by(AuditLog.timestamp.desc())

    rows, total = paginate(query, params)
    items = [
        AuditLogEntryResponse(
            id=log.id,
            action=log.action,
            target=log.target,
            timestamp=log.timestamp,
            actor_name=identity.name,
            actor_email=identity.email,
        )
        for log, _membership, identity in rows
    ]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)
