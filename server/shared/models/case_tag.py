from sqlalchemy import Column, Enum, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from shared.database import Base
from shared.models.enums import PracticeArea


class CaseTag(Base):
    """Many-to-many practice-area tagging on a case — a case can carry more
    than one tag (e.g. a case that's genuinely both family-law and a related
    traffic matter), so this is a real join table, not a single column on
    Cases. tenant_id is duplicated here (technically derivable through
    case_id) so the generic get_tenant_scoped helper works the same way it
    does for every other tenant-scoped table.
    """

    __tablename__ = "case_tags"
    __table_args__ = (
        UniqueConstraint("case_id", "practice_area", name="uq_case_tags_case_practice_area"),
        Index("ix_case_tags_tenant_id", "tenant_id"),
        Index("ix_case_tags_case_id", "case_id"),
        Index("ix_case_tags_practice_area", "practice_area"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    practice_area = Column(Enum(PracticeArea), nullable=False)

    case = relationship("Case", back_populates="tags")
