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


class IdentityResponse(BaseModel):
    id: int
    name: str
    email: EmailStr


class SessionResponse(BaseModel):
    name: str
    email: EmailStr
    role: UserRole
