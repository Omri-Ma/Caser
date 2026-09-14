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


class PublicDirectoryEntry(BaseModel):
    """One row of the lobby's public firm directory (CLAUDE.md's "general,
    non-tenant product homepage" requirement) — name/logo/subdomain only,
    same non-sensitive boundary as a tenant's own public homepage. The
    logo itself is fetched from that tenant's own GET /public/logo (keyed
    by subdomain via the Host header, same as everywhere else), not a new
    logo route here — has_logo just tells the frontend whether to try.
    """

    name: str
    subdomain: str
    has_logo: bool = False


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
