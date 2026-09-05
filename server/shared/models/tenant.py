from sqlalchemy import Boolean, Column, Enum, Integer, String
from sqlalchemy.orm import relationship

from shared.database import Base
from shared.models.enums import Plan


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    subdomain = Column(String(63), nullable=False, unique=True, index=True)
    plan = Column(Enum(Plan), nullable=False, default=Plan.FREE)
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), nullable=True)
    active = Column(Boolean, nullable=False, default=True)

    memberships = relationship("Membership", back_populates="tenant")
