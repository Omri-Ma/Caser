from pydantic import BaseModel, EmailStr, Field

from shared.models.enums import UserRole


class RegisterRequest(BaseModel):
    """Create a bare global account — no firm attached yet. A lawyer/client
    uses this once, then an office manager attaches them to a firm via
    admin_api's POST /members.
    """

    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LobbyLoginRequest(BaseModel):
    """lawyer/client login from the lobby (www.<BASE_DOMAIN>) — no tenant
    subdomain known yet, unlike LoginRequest's per-tenant version.
    """

    email: EmailStr
    password: str


class LobbyTenantOption(BaseModel):
    tenant_id: int
    subdomain: str
    firm_name: str
    # Included here (unlike admin_api's version) because client/'s nav
    # differs by role (lawyer vs client) — the lobby redirect needs to carry
    # it across, since the tenant subdomain it lands on is a different origin
    # and can't read anything the lobby page stored client-side.
    role: UserRole
    # Same reasoning as role — a manager-authority lawyer (CLAUDE.md's
    # Memberships.is_manager note) needs the client/ UI on the landing
    # subdomain to know it can offer narrative generation, and that
    # subdomain can't read anything stored on the lobby's own origin.
    is_manager: bool = False


class PendingInviteOption(BaseModel):
    """A lawyer/client invite still awaiting this identity's response —
    surfaced at lobby-login the same way active memberships are (CLAUDE.md's
    MembershipInvites note: "the invite shows up as a pending action for
    them the next time they log in").
    """

    invite_id: int
    tenant_id: int
    subdomain: str
    firm_name: str
    role: UserRole


class LobbyLoginResponse(BaseModel):
    name: str
    email: EmailStr
    tenants: list[LobbyTenantOption]
    pending_invites: list[PendingInviteOption] = []


class AcceptInviteResponse(BaseModel):
    tenant_id: int
    subdomain: str
    firm_name: str
    role: UserRole
    is_manager: bool = False


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
    """Self-service profile edit — bio/photo_url/years_of_experience are all
    self-reported and global to the person (CLAUDE.md's Identities note),
    never a lever another party (e.g. an office_manager) gets to pull.
    """

    bio: str | None = Field(None, max_length=2000)
    photo_url: str | None = Field(None, max_length=500)
    years_of_experience: int | None = Field(None, ge=0, le=80)


class SessionResponse(BaseModel):
    name: str
    email: EmailStr
    role: UserRole
    is_manager: bool = False
