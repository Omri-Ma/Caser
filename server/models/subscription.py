from sqlalchemy import Boolean, Column, Date, Enum, ForeignKey, Index, Integer
from sqlalchemy.orm import relationship

from core.database import Base
from models.enums import Plan


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (Index("ix_subscriptions_tenant_id", "tenant_id"),)

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    plan = Column(Enum(Plan), nullable=False, default=Plan.FREE)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    active = Column(Boolean, nullable=False, default=True)

    tenant = relationship("Tenant")
