import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from admin_api.schemas.dashboard import (
    DashboardStatsResponse,
    MonthlyBillableHoursPoint,
    MonthlyCaseActivityPoint,
)
from shared.database import get_db
from shared.membership import require_role
from shared.models import Case, Identity, Membership, Tenant, WorkLog
from shared.models.enums import CaseStatus, UserRole
from shared.plan_limits import count_active_lawyers, get_plan_usage
from shared.tenant import get_current_tenant

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# office_manager's own per-tenant dashboard (CLAUDE.md's Roles: "scoped to
# their own tenant only") — a clearly different code path from
# admin_api/routers/platform.py's cross-tenant super_admin stats: every
# query here filters on the current tenant, resolved the normal way via
# get_current_tenant, never the separate super_admin-only path.

MONTHLY_ACTIVITY_MONTHS = 6


def _last_n_months(n: int) -> list[tuple[int, int]]:
    today = date.today()
    year, month = today.year, today.month
    months = []
    for _ in range(n):
        months.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    months.reverse()
    return months


def _monthly_case_activity(tenant_id: int, db: Session) -> list[MonthlyCaseActivityPoint]:
    """New-case counts for the trailing MONTHLY_ACTIVITY_MONTHS months.
    Grouped in Python rather than a DB date-trunc function — case volume per
    tenant is small enough that this is simpler than a dialect-specific
    query, and it keeps this endpoint portable across the MySQL used in
    production and whatever the test database is.
    """
    months = _last_n_months(MONTHLY_ACTIVITY_MONTHS)
    counts = {key: 0 for key in months}

    created_dates = (
        db.query(Case.created_at).filter(Case.tenant_id == tenant_id).all()
    )
    for (created_at,) in created_dates:
        key = (created_at.year, created_at.month)
        if key in counts:
            counts[key] += 1

    return [
        MonthlyCaseActivityPoint(month=f"{year:04d}-{month:02d}", new_cases=counts[(year, month)])
        for year, month in months
    ]


def _monthly_billable_hours(tenant_id: int, db: Session) -> list[MonthlyBillableHoursPoint]:
    """Total WorkLog hours (by work date) for the trailing
    MONTHLY_ACTIVITY_MONTHS months — same trailing-window/Python-bucketing
    approach as _monthly_case_activity above, for the same portability
    reason. Distinct chart from case activity: hours worked, not cases opened.
    """
    months = _last_n_months(MONTHLY_ACTIVITY_MONTHS)
    totals = {key: 0.0 for key in months}

    entries = db.query(WorkLog.date, WorkLog.hours).filter(WorkLog.tenant_id == tenant_id).all()
    for work_date, hours in entries:
        key = (work_date.year, work_date.month)
        if key in totals:
            totals[key] += float(hours)

    return [
        MonthlyBillableHoursPoint(month=f"{year:04d}-{month:02d}", total_hours=round(totals[(year, month)], 2))
        for year, month in months
    ]


@router.get("/stats", response_model=DashboardStatsResponse)
def dashboard_stats(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    total_case_count = db.query(Case).filter(Case.tenant_id == tenant.id).count()
    closed_case_count = (
        db.query(Case).filter(Case.tenant_id == tenant.id, Case.status == CaseStatus.CLOSED).count()
    )
    client_count = (
        db.query(Membership)
        .filter(
            Membership.tenant_id == tenant.id,
            Membership.role == UserRole.CLIENT,
            Membership.active.is_(True),
        )
        .count()
    )
    usage = get_plan_usage(tenant.id, db)

    return DashboardStatsResponse(
        active_case_count=total_case_count - closed_case_count,
        total_case_count=total_case_count,
        closed_case_count=closed_case_count,
        lawyer_count=count_active_lawyers(tenant.id, db),
        client_count=client_count,
        plan=usage["plan"],
        storage_used_bytes=usage["storage_used_bytes"],
        storage_limit_bytes=usage["storage_limit_bytes"],
        monthly_case_activity=_monthly_case_activity(tenant.id, db),
        monthly_billable_hours=_monthly_billable_hours(tenant.id, db),
    )


@router.get("/export")
def export_data(
    resource: str = Query("cases", pattern="^(cases|members)$"),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """CSV export of this tenant's own cases or members. Per CLAUDE.md's
    explicit warning, export queries are exactly the kind most likely to
    accidentally skip tenant_id filtering — both branches below filter on
    `tenant.id` from get_current_tenant the same way every other route in
    this file does, rather than a separate one-off query written just for
    this feature.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    if resource == "cases":
        writer.writerow(["id", "title", "status", "created_at"])
        rows = (
            db.query(Case)
            .filter(Case.tenant_id == tenant.id)
            .order_by(Case.created_at)
            .all()
        )
        for case in rows:
            writer.writerow([case.id, case.title, case.status.value, case.created_at.isoformat()])
    else:
        writer.writerow(["id", "name", "email", "role", "active"])
        rows = (
            db.query(Membership, Identity)
            .join(Identity, Membership.identity_id == Identity.id)
            .filter(Membership.tenant_id == tenant.id)
            .order_by(Identity.name)
            .all()
        )
        for membership, identity in rows:
            writer.writerow([membership.id, identity.name, identity.email, membership.role.value, membership.active])

    filename = f"{tenant.subdomain}-{resource}.csv"
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
