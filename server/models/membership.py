from sqlalchemy import Boolean, Column, Enum, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from core.database import Base
from models.enums import UserRole


class Membership(Base):
    """One person's role at one firm. This is what used to be baked directly
    into Users(tenant_id, role) — split out so one Identity can hold a
    Membership at more than one tenant.
    """

    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("identity_id", "tenant_id", name="uq_memberships_identity_tenant"),
        Index("ix_memberships_tenant_id", "tenant_id"),
        Index("ix_memberships_identity_id", "identity_id"),
    )

    id = Column(Integer, primary_key=True)
    identity_id = Column(Integer, ForeignKey("identities.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    # Per-firm control: the office manager decides whether this person's
    # profile (bio/photo, from Identity) appears on *this* firm's public
    # page. Only meaningful for lawyer memberships in practice.
    show_on_public_page = Column(Boolean, nullable=False, default=True)

    identity = relationship("Identity", back_populates="memberships")
    tenant = relationship("Tenant", back_populates="memberships")
