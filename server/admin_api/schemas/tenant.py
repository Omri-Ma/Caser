from typing import Optional

from pydantic import BaseModel, Field


class TenantResponse(BaseModel):
    id: int
    name: str
    subdomain: str
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    active: bool
    about: Optional[str] = None


class UpdateTenantRequest(BaseModel):
    """name/logo_url/primary_color are direct Tenants columns; about is
    stored via the generic Settings table instead (CLAUDE.md's Branding
    requirement — branding proper lives on Tenants, but the free-text public
    "about" blurb is a good fit for Settings's purpose). subdomain and active
    are deliberately not editable here: subdomain is fixed at signup
    (changing it would break every existing bookmark/link), and active is a
    super_admin-only lockout switch, not a self-service one.
    """

    name: str = Field(..., min_length=1, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=500)
    primary_color: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    about: Optional[str] = Field(None, max_length=2000)
