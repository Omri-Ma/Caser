from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from admin_api.core.file_validation import MAX_LOGO_FILE_SIZE_BYTES, detect_image_type
from admin_api.schemas.tenant import TenantResponse, UpdateTenantRequest
from shared.cache import invalidate_tenant_cache
from shared.database import get_db
from shared.membership import require_role
from shared.models import Membership, Tenant
from shared.models.enums import UserRole
from shared.settings import ABOUT_KEY, get_setting, set_setting
from shared.storage import get_file_url, save_tenant_logo
from shared.tenant import get_current_tenant
from shared import error_messages as E

router = APIRouter(prefix="/tenant", tags=["tenant"])


def _to_response(tenant: Tenant, db: Session) -> TenantResponse:
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        subdomain=tenant.subdomain,
        has_logo=bool(tenant.logo_url),
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
    """name/primary_color are direct Tenants columns; about goes through the
    generic Settings table instead (CLAUDE.md's Branding requirement). The
    logo is a separate upload — see POST /tenant/logo below.
    """
    tenant.name = payload.name
    tenant.primary_color = payload.primary_color
    set_setting(db, tenant.id, ABOUT_KEY, payload.about)
    db.commit()
    db.refresh(tenant)
    # Active invalidation (CLAUDE.md's Cache section) — the whole point is
    # that the very next request sees this update, not after the TTL expires.
    invalidate_tenant_cache(tenant.subdomain)
    return _to_response(tenant, db)


@router.post("/logo", response_model=TenantResponse)
async def upload_logo(
    file: UploadFile = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Real file upload replacing the old URL-only text field — validated
    against actual content/magic bytes, same as every other upload in this
    app, never trusting the filename extension.
    """
    content = await file.read()
    if len(content) > MAX_LOGO_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=E.logo_file_exceeds_limit(MAX_LOGO_FILE_SIZE_BYTES // (1024 * 1024)),
        )

    detected = detect_image_type(content)
    if detected is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.ONLY_JPEG_PNG_LOGOS_ALLOWED)

    tenant.logo_url = save_tenant_logo(content, tenant.id, file.filename or "logo")
    db.commit()
    db.refresh(tenant)
    invalidate_tenant_cache(tenant.subdomain)
    return _to_response(tenant, db)


@router.get("/logo")
def get_logo(
    tenant: Tenant = Depends(get_current_tenant),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Authenticated read for admin/'s own BrandingPage preview — the public
    homepage's copy is client_api's GET /public/logo instead, unauthenticated
    (a public visitor never has an admin_api session).
    """
    if not tenant.logo_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=E.NO_LOGO_UPLOADED)
    return FileResponse(get_file_url(tenant.logo_url))
