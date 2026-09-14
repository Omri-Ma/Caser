from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import relationship

from shared.database import Base
from shared.models.enums import InviteStatus, UserRole


class MembershipInvite(Base):
    """An office manager adding a lawyer/client to their firm is a request,
    not an instant Membership (CLAUDE.md's Data model) — nobody should find
    themselves listed as a firm's lawyer or client without ever agreeing to
    it. Keyed by email, not identity_id: the invited person may not have an
    Identity yet at all, and this table has to work either way (see
    shared/invites.py for the two paths that follow from that).
    """

    __tablename__ = "membership_invites"
    __table_args__ = (
        Index("ix_membership_invites_tenant_id", "tenant_id"),
        Index("ix_membership_invites_email", "email"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    email = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    invited_by = Column(Integer, ForeignKey("memberships.id"), nullable=False)
    status = Column(Enum(InviteStatus), nullable=False, default=InviteStatus.PENDING)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    responded_at = Column(DateTime, nullable=True)

    tenant = relationship("Tenant")
    inviter = relationship("Membership")
