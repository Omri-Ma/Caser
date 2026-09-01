from pydantic import BaseModel, EmailStr, Field

from models.enums import UserRole


class RegisterRequest(BaseModel):
    """Create a bare global account — no firm attached yet. A lawyer/client
    uses this once, then an office manager attaches them to a firm via
    POST /members.
    """

    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)


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


class AddMemberRequest(BaseModel):
    """Office manager attaches an existing global account to their firm."""

    email: EmailStr
    role: UserRole


class IdentityResponse(BaseModel):
    id: int
    name: str
    email: EmailStr


class SessionResponse(BaseModel):
    name: str
    email: EmailStr
    role: UserRole


class MembershipResponse(BaseModel):
    id: int
    identity_id: int
    tenant_id: int
    role: UserRole
