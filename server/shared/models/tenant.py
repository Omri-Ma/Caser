from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from shared.database import Base


class Tenant(Base):
    """No `plan` column: a firm's current plan is whichever Subscriptions
    row for this tenant has active = true, not a separate cached copy — see
    the Subscription model.
    """

    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    subdomain = Column(String(63), nullable=False, unique=True, index=True)
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    # Powers super_admin's tenant-growth-per-month chart — the only consumer;
    # not otherwise part of any tenant-scoped route's behavior.
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    memberships = relationship("Membership", back_populates="tenant")
