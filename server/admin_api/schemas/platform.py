from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from shared.models.enums import Plan


class TenantSummaryResponse(BaseModel):
    """One row of the super_admin firm list — firm-level/aggregate data
    only (name, plan, active/suspended, lawyer/case counts), never anything
    that reaches into a firm's case or document content (CLAUDE.md's
    Roles section boundary on what super_admin may see).
    """

    id: int
    name: str
    subdomain: str
    active: bool
    plan: Plan
    lawyer_count: int
    case_count: int


class PlanDistributionEntry(BaseModel):
    plan: Plan
    tenant_count: int


class PlatformStatsResponse(BaseModel):
    total_tenants: int
    active_tenants: int
    total_lawyers: int
    total_clients: int
    total_cases: int
    total_storage_bytes: int
    plan_distribution: List[PlanDistributionEntry]


class TenantGrowthPoint(BaseModel):
    month: str
    new_tenants: int


class EarningsPoint(BaseModel):
    month: str
    earnings_ils: int


class PlatformEarningsResponse(BaseModel):
    current_month_earnings_ils: int
    trend: List[EarningsPoint]


class TenantStorageOverviewEntry(BaseModel):
    tenant_id: int
    name: str
    subdomain: str
    plan: Plan
    storage_used_bytes: int
    storage_limit_bytes: int


class MembershipSummary(BaseModel):
    tenant_id: int
    tenant_name: str
    subdomain: str
    role: str


class PlatformUserResponse(BaseModel):
    """One row of super_admin's cross-tenant users view — still firm-level/
    account-level data, not case/document content (CLAUDE.md's Roles
    section): knowing *that* someone is a lawyer at two firms is not the
    same as seeing anything about their casework.
    """

    id: int
    name: str
    email: str
    last_login_at: Optional[datetime]
    memberships: List[MembershipSummary]


class PlatformAuditLogEntryResponse(BaseModel):
    id: int
    action: str
    target_tenant_name: str
    actor_name: str
    actor_email: str
    timestamp: datetime
