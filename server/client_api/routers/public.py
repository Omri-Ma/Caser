from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from client_api.schemas.public import PublicTeamMember, PublicTenantProfile
from shared.database import get_db
from shared.models import Identity, Membership, Tenant
from shared.models.enums import UserRole
from shared.settings import ABOUT_KEY, get_setting
from shared.storage import get_file_url
from shared.tenant import get_current_tenant

router = APIRouter(prefix="/public", tags=["public"])

# office_managers listed first, then lawyers (CLAUDE.md's public homepage
# note) — a fixed sort key, not alphabetical/role-name order.
_ROLE_SORT_ORDER = {UserRole.OFFICE_MANAGER: 0, UserRole.LAWYER: 1}


@router.get("/profile", response_model=PublicTenantProfile)
def get_public_profile(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Public, unauthenticated firm profile for the tenant subdomain's
    landing page — reuses get_current_tenant with no auth dependency on top
    of it. Response is whitelisted to firm profile info plus the public
    team section; never returns cases, documents, or any other tenant data.
    """
    rows = (
        db.query(Membership, Identity)
        .join(Identity, Membership.identity_id == Identity.id)
        .filter(
            Membership.tenant_id == tenant.id,
            Membership.active.is_(True),
            Membership.show_on_public_page.is_(True),
            Membership.role.in_([UserRole.OFFICE_MANAGER, UserRole.LAWYER]),
        )
        .all()
    )
    team = sorted(
        (
            PublicTeamMember(
                name=identity.name,
                role=membership.role,
                bio=identity.bio,
                photo_url=identity.photo_url,
                years_of_experience=identity.years_of_experience,
            )
            for membership, identity in rows
        ),
        # Most experienced first within each role group; no-experience-set
        # sorts last within its group rather than crashing on None.
        key=lambda member: (_ROLE_SORT_ORDER[member.role], -(member.years_of_experience or -1)),
    )

    return PublicTenantProfile(
        name=tenant.name,
        has_logo=bool(tenant.logo_url),
        primary_color=tenant.primary_color,
        about=get_setting(db, tenant.id, ABOUT_KEY),
        team=team,
    )


@router.get("/logo")
def get_public_logo(tenant: Tenant = Depends(get_current_tenant)):
    """Unauthenticated — this is what the public homepage's <img> actually
    fetches. admin_api's GET /tenant/logo is the authenticated equivalent,
    used for the BrandingPage's own preview.
    """
    if not tenant.logo_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No logo uploaded")
    return FileResponse(get_file_url(tenant.logo_url))
