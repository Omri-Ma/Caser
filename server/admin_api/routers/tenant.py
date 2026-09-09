from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from admin_api.schemas.tenant import TenantResponse, UpdateTenantRequest
from shared.database import get_db
from shared.membership import require_role
from shared.models import Membership, Tenant
from shared.models.enums import UserRole
from shared.tenant import get_current_tenant

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("", response_model=TenantResponse)
def get_tenant(
    tenant: Tenant = Depends(get_current_tenant),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    return tenant


@router.patch("", response_model=TenantResponse)
def update_tenant(
    payload: UpdateTenantRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Branding settings — direct Tenants columns, not the generic Settings
    table (CLAUDE.md's Branding requirement).
    """
    tenant.name = payload.name
    tenant.logo_url = payload.logo_url
    tenant.primary_color = payload.primary_color
    db.commit()
    db.refresh(tenant)
    return tenant
