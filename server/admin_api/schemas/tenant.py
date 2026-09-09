from typing import Optional

from pydantic import BaseModel, Field


class TenantResponse(BaseModel):
    id: int
    name: str
    subdomain: str
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    active: bool


class UpdateTenantRequest(BaseModel):
    """Direct Tenants columns only (name/logo_url/primary_color) — not the
    generic Settings table, per CLAUDE.md's Branding requirement. subdomain
    and active are deliberately not editable here: subdomain is fixed at
    signup (changing it would break every existing bookmark/link), and
    active is a super_admin-only lockout switch, not a self-service one.
    """

    name: str = Field(..., min_length=1, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=500)
    primary_color: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
