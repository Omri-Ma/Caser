from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import relationship

from core.database import Base
from models.enums import CaseStatus


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        Index("ix_cases_tenant_id", "tenant_id"),
        Index("ix_cases_status", "status"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(Enum(CaseStatus), nullable=False, default=CaseStatus.OPEN)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    assignments = relationship("CaseAssignment", back_populates="case")
