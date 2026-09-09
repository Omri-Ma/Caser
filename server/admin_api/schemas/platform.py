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


class PlatformStatsResponse(BaseModel):
    total_tenants: int
    active_tenants: int
    total_lawyers: int
    total_cases: int
