from typing import Optional

from pydantic import BaseModel


class PublicTenantProfile(BaseModel):
    """Deliberately whitelisted to only the four fields a public,
    unauthenticated visitor may see — never case/document/user data, even
    indirectly (CLAUDE.md's public homepage requirement).
    """

    name: str
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    about: Optional[str] = None
