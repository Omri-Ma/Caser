from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import relationship

from core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_tenant_id", "tenant_id"),)

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("memberships.id"), nullable=False)
    action = Column(String(100), nullable=False)
    target = Column(String(255), nullable=False)
    timestamp = Column(DateTime, nullable=False, server_default=func.now())

    user = relationship("Membership")
