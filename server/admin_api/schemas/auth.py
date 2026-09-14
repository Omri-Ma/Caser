from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from shared.models.enums import InviteStatus, UserRole


class SignupRequest(BaseModel):
    """Register a brand-new firm (tenant) plus its first office_manager."""

    firm_name: str = Field(..., min_length=1, max_length=255)
    subdomain: str = Field(..., min_length=1, max_length=63, pattern=r"^[a-z0-9-]+$")
    admin_name: str = Field(..., min_length=1, max_length=255)
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LobbyLoginRequest(BaseModel):
    """office_manager login from the lobby (www.<BASE_DOMAIN>) — no tenant
    subdomain known yet, unlike LoginRequest's per-tenant version.
    """

    email: EmailStr
    password: str


class LobbyTenantOption(BaseModel):
    tenant_id: int
    subdomain: str
    firm_name: str


class LobbyLoginResponse(BaseModel):
    name: str
    email: EmailStr
    # Every active office_manager Membership this identity holds, across
    # every active tenant — one entry redirects straight there, more than one
    # means the frontend shows a "choose your firm" picker.
    tenants: list[LobbyTenantOption]


class PlatformLoginRequest(BaseModel):
    """super_admin login at the fixed platform address — no tenant/subdomain
    involved, just Identity + Identities.is_super_admin.
    """

    email: EmailStr
    password: str


class InviteMemberRequest(BaseModel):
    """Office manager invites a lawyer or client to their firm — this is a
    request, not an instant Membership (CLAUDE.md's MembershipInvites note):
    nobody should find themselves listed as a firm's lawyer/client without
    ever agreeing to it. Never office_manager — founding a firm's first
    office_manager is signup, adding another isn't part of this flow.
    """

    email: EmailStr
    role: UserRole


class InviteResponse(BaseModel):
    id: int
    tenant_id: int
    email: EmailStr
    role: UserRole
    status: InviteStatus
    created_at: datetime
    invited_by_name: str


class ChangePasswordRequest(BaseModel):
    """Self-service "change my password" while logged in — every role can
    do this for their own account. Never touches another person's account
    (see CLAUDE.md's office_manager authority boundary)."""

    current_password: str
    new_password: str = Field(..., min_length=8)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class GenericMessageResponse(BaseModel):
    message: str


class IdentityResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    bio: str | None = None
    photo_url: str | None = None
    years_of_experience: int | None = None


class UpdateProfileRequest(BaseModel):
    """Self-service profile edit — see client_api's identical schema for the
    full reasoning (bio/photo_url/years_of_experience are global to the
    person, never an office_manager lever over someone else's account).
    """

    bio: str | None = Field(None, max_length=2000)
    photo_url: str | None = Field(None, max_length=500)
    years_of_experience: int | None = Field(None, ge=0, le=80)


class SessionResponse(BaseModel):
    name: str
    email: EmailStr
    role: UserRole


class PlatformSessionResponse(BaseModel):
    """super_admin has no Membership/role — just a name and email."""

    name: str
    email: EmailStr


class MemberResponse(BaseModel):
    """A membership joined with its identity's name/email — what the case
    assignment picker (and any future members list screen) actually needs to
    display, not just the bare ids MembershipResponse carries.
    """

    id: int
    identity_id: int
    tenant_id: int
    role: UserRole
    identity_name: str
    identity_email: EmailStr
    active: bool
    # Only meaningful for office_manager/lawyer rows — a client is never
    # eligible for the public team section (CLAUDE.md's public homepage
    # note), so the frontend simply never renders the toggle for one.
    show_on_public_page: bool
    # Only meaningful for lawyer rows (CLAUDE.md's Memberships note) — feeds
    # Narratives.total_fee. Nullable: a brand-new lawyer membership has no
    # rate set yet.
    hourly_rate: Optional[Decimal] = None
    # Only meaningful for lawyer rows (CLAUDE.md's Memberships note) —
    # office_manager-set case-oversight flag, orthogonal to role/promotion:
    # grants full case visibility + narrative authority in client_api
    # without making this lawyer a firm administrator.
    is_manager: bool = False


class UpdatePublicVisibilityRequest(BaseModel):
    show_on_public_page: bool


class UpdateManagerStatusRequest(BaseModel):
    """Grant or revoke Memberships.is_manager (CLAUDE.md's Memberships
    note) — case-oversight authority only, never firm administration. There
    is no promote/demote-to-office_manager action to be separate from: a
    firm's role is fixed at founding and never changes (see Memberships).
    """

    is_manager: bool


class UpdateHourlyRateRequest(BaseModel):
    """office_manager-set billing rate for a lawyer membership (CLAUDE.md's
    Memberships note) — a fact about their employment at *this* firm, not a
    global attribute of the person. Must be positive: a rate of exactly 0
    would silently zero out every narrative fee for that lawyer, which is
    never the intent of *setting* a rate (an unset rate — None — already
    covers "no rate yet" without conflating it with "billed at zero").
    """

    hourly_rate: Decimal = Field(gt=0)
