from sqlalchemy import BigInteger, Column, DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import relationship

from shared.database import Base
from shared.models.enums import DocumentFolderType


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_tenant_id", "tenant_id"),
        Index("ix_documents_case_id", "case_id"),
        Index("ix_documents_original_filename", "original_filename"),
        Index("ix_documents_folder_type", "folder_type"),
        Index("ix_documents_archived_at", "archived_at"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("memberships.id"), nullable=False)
    # Storage key returned by shared.storage.save_file() — never a public
    # URL by itself (local disk has none); shared.storage.get_file_url()
    # resolves this back into something the download route can actually
    # read from. Swapping storage backends later only touches that module.
    file_url = Column(String(500), nullable=False)
    original_filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    folder_type = Column(Enum(DocumentFolderType), nullable=False)
    # Two-stage trash (CLAUDE.md): set on archive, cleared on restore. A real
    # DELETE (row + file both erased) only happens on permanent delete, which
    # is only reachable from inside the archive. No separate visible_to
    # column — visibility is fully derived from CaseAssignments + folder_type.
    archived_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    case = relationship("Case")
    uploader = relationship("Membership")
