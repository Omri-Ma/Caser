from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import relationship

from core.database import Base


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        Index("ix_cases_tenant_id", "tenant_id"),
        Index("ix_cases_status", "status"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lawyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    client = relationship("User", foreign_keys=[client_id])
    lawyer = relationship("User", foreign_keys=[lawyer_id])
