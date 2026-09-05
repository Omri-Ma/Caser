from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, Text, func
from sqlalchemy.orm import relationship

from shared.database import Base


class Narrative(Base):
    __tablename__ = "narratives"
    __table_args__ = (
        Index("ix_narratives_tenant_id", "tenant_id"),
        Index("ix_narratives_case_id", "case_id"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    generated_text = Column(Text, nullable=False)
    total_hours = Column(Numeric(8, 2), nullable=False)
    total_fee = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    case = relationship("Case")
