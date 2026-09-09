from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from client_api.schemas.public import PublicTenantProfile
from shared.database import get_db
from shared.models import Tenant
from shared.settings import ABOUT_KEY, get_setting
from shared.tenant import get_current_tenant

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/profile", response_model=PublicTenantProfile)
def get_public_profile(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Public, unauthenticated firm profile for the tenant subdomain's
    landing page — reuses get_current_tenant with no auth dependency on top
    of it. Response is whitelisted to name/logo_url/primary_color/about
    only; never returns cases, documents, members, or any other tenant data.
    """
    return PublicTenantProfile(
        name=tenant.name,
        logo_url=tenant.logo_url,
        primary_color=tenant.primary_color,
        about=get_setting(db, tenant.id, ABOUT_KEY),
    )
