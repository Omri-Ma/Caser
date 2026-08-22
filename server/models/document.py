from sqlalchemy import Column, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from core.database import Base
from models.enums import DocumentFolderType


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_tenant_id", "tenant_id"),
        Index("ix_documents_case_id", "case_id"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_url = Column(String(500), nullable=False)
    folder_type = Column(Enum(DocumentFolderType), nullable=False)
    # Optional extra restriction beyond folder_type, e.g. a specific role or
    # user id this document is scoped to. Nullable: most documents are just
    # governed by folder_type.
    visible_to = Column(String(255), nullable=True)

    case = relationship("Case")
    uploader = relationship("User")
