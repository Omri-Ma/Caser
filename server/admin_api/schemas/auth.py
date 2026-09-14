from datetime import datetime

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
