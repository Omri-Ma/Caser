from sqlalchemy import Column, Enum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from core.database import Base
from models.enums import UserRole


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        Index("ix_users_tenant_id", "tenant_id"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)

    tenant = relationship("Tenant", back_populates="users")
