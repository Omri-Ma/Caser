from typing import Optional

from pydantic import BaseModel

from shared.models.enums import UserRole


class PublicTeamMember(BaseModel):
    """Only office_manager/lawyer profiles can appear here (CLAUDE.md's
    public homepage note) — never a client, they aren't "the firm" the way
    staff are.
    """

    name: str
    role: UserRole
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    years_of_experience: Optional[int] = None


class PublicTenantProfile(BaseModel):
    """Deliberately whitelisted to only non-sensitive firm profile info a
    public, unauthenticated visitor may see — never case/document/user data,
    even indirectly (CLAUDE.md's public homepage requirement). has_logo is a
    presence flag, not the internal storage key — the actual image is
    fetched separately from GET /public/logo.
    """

    name: str
    has_logo: bool = False
    primary_color: Optional[str] = None
    about: Optional[str] = None
    team: list[PublicTeamMember] = []
