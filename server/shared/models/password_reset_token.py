from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from shared.database import Base


class PasswordResetToken(Base):
    """Backs the self-service forgot-password flow. Tenant-less on purpose —
    a forgotten password is an Identities-level problem, not a per-firm one,
    same as the password itself (see CLAUDE.md's Data model). token_hash is
    a hash of the actual token, never the raw value — the raw token only
    ever exists in the one-time link itself.
    """

    __tablename__ = "password_reset_tokens"
    __table_args__ = (Index("ix_password_reset_tokens_identity_id", "identity_id"),)

    id = Column(Integer, primary_key=True)
    identity_id = Column(Integer, ForeignKey("identities.id"), nullable=False)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)

    identity = relationship("Identity")
