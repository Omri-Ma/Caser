from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import relationship

from shared.database import Base


class PlatformAuditLog(Base):
    """A separate, parallel log for super_admin's own actions (suspending/
    reactivating a tenant) — not a reuse of the tenant-scoped AuditLog.
    AuditLog.user_id references memberships.id, and super_admin is
    deliberately never a Memberships row (CLAUDE.md's Multi-tenancy
    architecture), so this logs identity_id directly instead.
    """

    __tablename__ = "platform_audit_logs"
    __table_args__ = (Index("ix_platform_audit_logs_identity_id", "identity_id"),)

    id = Column(Integer, primary_key=True)
    identity_id = Column(Integer, ForeignKey("identities.id"), nullable=False)
    action = Column(String(100), nullable=False)
    target_tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, server_default=func.now())

    identity = relationship("Identity")
    target_tenant = relationship("Tenant")
