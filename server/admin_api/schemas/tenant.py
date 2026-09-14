from typing import Optional

from pydantic import BaseModel, Field


class TenantResponse(BaseModel):
    id: int
    name: str
    subdomain: str
    # A real file upload now (see admin_api/routers/tenant.py's POST
    # /tenant/logo), not a URL text field — this is deliberately just a
    # presence flag, not the internal storage key, so nothing internal
    # leaks into a response. The frontend fetches the actual image from
    # GET /tenant/logo (this app) or GET /public/logo (client_api's public
    # homepage) when this is true.
    has_logo: bool
    primary_color: Optional[str] = None
    active: bool
    about: Optional[str] = None


class UpdateTenantRequest(BaseModel):
    """name/primary_color are direct Tenants columns; about is stored via
    the generic Settings table instead (CLAUDE.md's Branding requirement —
    branding proper lives on Tenants, but the free-text public "about"
    blurb is a good fit for Settings's purpose). subdomain and active are
    deliberately not editable here: subdomain is fixed at signup (changing
    it would break every existing bookmark/link), and active is a
    super_admin-only lockout switch, not a self-service one. The logo is a
    separate multipart upload (POST /tenant/logo), not part of this
    JSON-body request.
    """

    name: str = Field(..., min_length=1, max_length=255)
    primary_color: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    about: Optional[str] = Field(None, max_length=2000)
