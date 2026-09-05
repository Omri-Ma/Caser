from sqlalchemy import Column, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from shared.database import Base


class CaseAssignment(Base):
    """Who has access to a case — lawyers and clients alike. Whether an
    assigned membership is a lawyer or client comes from Membership.role, not
    a field here; this table just answers "is this person on this case".
    An office manager sees every case at their own tenant automatically and
    doesn't need a row here; super_admin never gets case-level access at all.
    """

    __tablename__ = "case_assignments"
    __table_args__ = (
        UniqueConstraint("case_id", "membership_id", name="uq_case_assignments_case_membership"),
        Index("ix_case_assignments_tenant_id", "tenant_id"),
        Index("ix_case_assignments_case_id", "case_id"),
        Index("ix_case_assignments_membership_id", "membership_id"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    membership_id = Column(Integer, ForeignKey("memberships.id"), nullable=False)

    case = relationship("Case", back_populates="assignments")
    membership = relationship("Membership")
