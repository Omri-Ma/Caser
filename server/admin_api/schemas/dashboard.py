from pydantic import BaseModel

from shared.models.enums import Plan


class MonthlyCaseActivityPoint(BaseModel):
    """One point on the case-activity trend chart — the count of cases
    *created* in that calendar month, oldest to newest.
    """

    month: str  # "YYYY-MM"
    new_cases: int


class MonthlyBillableHoursPoint(BaseModel):
    """One point on the billable-hours trend chart — total WorkLog hours
    logged (by date) in that calendar month, oldest to newest. Distinct from
    monthly_case_activity above: this tracks hours worked, not cases opened.
    """

    month: str  # "YYYY-MM"
    total_hours: float


class DashboardStatsResponse(BaseModel):
    """office_manager's own per-tenant dashboard — everything here is
    scoped to the current tenant only (CLAUDE.md's Roles: super_admin's
    cross-tenant /platform/stats is a separate, explicitly different path).
    """

    active_case_count: int
    total_case_count: int
    closed_case_count: int
    lawyer_count: int
    client_count: int
    plan: Plan
    storage_used_bytes: int
    storage_limit_bytes: int
    monthly_case_activity: list[MonthlyCaseActivityPoint]
    monthly_billable_hours: list[MonthlyBillableHoursPoint]
