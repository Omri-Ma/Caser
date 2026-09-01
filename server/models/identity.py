from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from core.database import Base


class Identity(Base):
    """A person's global CaseHub login (email + password) — not tied to any
    one firm. Which firm(s) they can access, and their role in each, lives on
    Membership instead. One person, one Identity, many possible Memberships.

    bio/photo_url are self-reported profile info (mainly for lawyers, shown
    on a firm's public page) — global to the person, not per-firm, since it's
    "their own page." Whether it's actually shown at a given firm is a
    per-Membership toggle instead (Membership.show_on_public_page).
    """

    __tablename__ = "identities"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    bio = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)
    # Bumped on logout/password change. JWTs aren't stored server-side, so
    # this is the only way to invalidate an outstanding token early — every
    # request compares the token's embedded value against this column.
    token_version = Column(Integer, nullable=False, default=0)

    memberships = relationship("Membership", back_populates="identity")
