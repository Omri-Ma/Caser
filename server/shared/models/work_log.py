from sqlalchemy import Column, Date, Enum, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import relationship

from shared.database import Base
from shared.models.enums import WorkLogSource


class WorkLog(Base):
    __tablename__ = "work_logs"
    __table_args__ = (
        Index("ix_work_logs_tenant_id", "tenant_id"),
        Index("ix_work_logs_case_id", "case_id"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    lawyer_id = Column(Integer, ForeignKey("memberships.id"), nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    date = Column(Date, nullable=False)
    hours = Column(Numeric(6, 2), nullable=False)
    description = Column(String(1000), nullable=True)
    source = Column(Enum(WorkLogSource), nullable=False, default=WorkLogSource.MANUAL)

    lawyer = relationship("Membership")
    case = relationship("Case")
