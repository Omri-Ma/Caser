from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from admin_api.schemas.tenant import TenantResponse, UpdateTenantRequest
from shared.database import get_db
from shared.membership import require_role
from shared.models import Membership, Tenant
from shared.models.enums import UserRole
from shared.settings import ABOUT_KEY, get_setting, set_setting
from shared.tenant import get_current_tenant

router = APIRouter(prefix="/tenant", tags=["tenant"])


def _to_response(tenant: Tenant, db: Session) -> TenantResponse:
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        subdomain=tenant.subdomain,
        logo_url=tenant.logo_url,
        primary_color=tenant.primary_color,
        active=tenant.active,
        about=get_setting(db, tenant.id, ABOUT_KEY),
    )


@router.get("", response_model=TenantResponse)
def get_tenant(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    return _to_response(tenant, db)


@router.patch("", response_model=TenantResponse)
def update_tenant(
    payload: UpdateTenantRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """name/logo_url/primary_color are direct Tenants columns; about goes
    through the generic Settings table instead (CLAUDE.md's Branding
    requirement).
    """
    tenant.name = payload.name
    tenant.logo_url = payload.logo_url
    tenant.primary_color = payload.primary_color
    set_setting(db, tenant.id, ABOUT_KEY, payload.about)
    db.commit()
    db.refresh(tenant)
    return _to_response(tenant, db)
