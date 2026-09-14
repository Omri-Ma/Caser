from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from admin_api.core.pagination import Page, PageParams, paginate
from admin_api.schemas.platform import (
    EarningsPoint,
    MembershipSummary,
    PlanDistributionEntry,
    PlatformAuditLogEntryResponse,
    PlatformEarningsResponse,
    PlatformStatsResponse,
    PlatformUserResponse,
    TenantGrowthPoint,
    TenantStorageOverviewEntry,
    TenantSummaryResponse,
)
from shared.database import get_db
from shared.models import Case, Document, Identity, Membership, PlatformAuditLog, Subscription, Tenant
from shared.models.enums import Plan, UserRole
from shared.plan_limits import PLAN_LAWYER_LIMITS, PLAN_PRICES_ILS, PLAN_STORAGE_LIMIT_BYTES, get_active_plan
from shared.platform import require_super_admin
from shared import error_messages as E

router = APIRouter(prefix="/platform", tags=["platform"])

# super_admin's own explicitly separate code path (CLAUDE.md's Multi-tenancy
# architecture): every query in this file spans every tenant on purpose, so
# none of it goes through get_current_tenant / get_tenant_scoped — those
# assume exactly one tenant in request scope, which doesn't apply here at
# all. Firm-level/aggregate data only — nothing here ever touches Cases'
# content, CaseAssignments, Documents, or WorkLogs rows themselves, only
# counts against them, matching the boundary CLAUDE.md's Roles section draws
# for super_admin.

TREND_MONTHS = 6


def _tenant_summary(tenant: Tenant, db: Session) -> TenantSummaryResponse:
    lawyer_count = (
        db.query(Membership)
        .filter(
            Membership.tenant_id == tenant.id,
            Membership.role == UserRole.LAWYER,
            Membership.active.is_(True),
        )
        .count()
    )
    case_count = db.query(Case).filter(Case.tenant_id == tenant.id).count()
    return TenantSummaryResponse(
        id=tenant.id,
        name=tenant.name,
        subdomain=tenant.subdomain,
        active=tenant.active,
        plan=get_active_plan(tenant.id, db),
        lawyer_count=lawyer_count,
        case_count=case_count,
    )


def _log_platform_action(identity: Identity, action: str, target_tenant_id: int, db: Session) -> None:
    db.add(PlatformAuditLog(identity_id=identity.id, action=action, target_tenant_id=target_tenant_id))
    db.commit()


def _last_n_months(n: int) -> list[tuple[int, int]]:
    """Same trailing-window/Python-bucketing approach as admin_api's own
    dashboard.py — case volume there and tenant/subscription volume here are
    both small enough that this is simpler than a dialect-specific
    date-trunc query, and it stays portable across MySQL and the test DB.
    """
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


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end_year, end_month = (year + 1, 1) if month == 12 else (year, month + 1)
    end = date(end_year, end_month, 1)
    return start, end


@router.get("/tenants", response_model=Page[TenantSummaryResponse])
def list_tenants(
    search: Optional[str] = Query(None, description="Partial, case-insensitive match on name or subdomain"),
    params: PageParams = Depends(),
    db: Session = Depends(get_db),
    _super_admin: Identity = Depends(require_super_admin),
):
    """Every Tenant, regardless of subdomain — the cross-tenant firm list
    the platform dashboard shows. Note this query intentionally omits the
    `active = True` filter get_current_tenant applies: a super_admin has to
    see suspended firms too, in order to reactivate them.
    """
    query = db.query(Tenant)
    if search:
        like = f"%{search}%"
        query = query.filter((Tenant.name.ilike(like)) | (Tenant.subdomain.ilike(like)))
    query = query.order_by(Tenant.name)
    total = query.count()
    rows = query.offset((params.page - 1) * params.page_size).limit(params.page_size).all()
    items = [_tenant_summary(tenant, db) for tenant in rows]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.post("/tenants/{tenant_id}/suspend", response_model=TenantSummaryResponse)
def suspend_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    super_admin: Identity = Depends(require_super_admin),
):
    """Flips Tenants.active off. get_current_tenant already filters on
    active = True, so this alone is a full, immediate lockout for every
    role at that firm, including its own office_manager (CLAUDE.md's
    Tenants note) — reactivate_tenant below is the only way back in.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=E.TENANT_NOT_FOUND)
    tenant.active = False
    db.commit()
    db.refresh(tenant)
    _log_platform_action(super_admin, "tenant_suspended", tenant.id, db)
    return _tenant_summary(tenant, db)


@router.post("/tenants/{tenant_id}/reactivate", response_model=TenantSummaryResponse)
def reactivate_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    super_admin: Identity = Depends(require_super_admin),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=E.TENANT_NOT_FOUND)
    tenant.active = True
    db.commit()
    db.refresh(tenant)
    _log_platform_action(super_admin, "tenant_reactivated", tenant.id, db)
    return _tenant_summary(tenant, db)


@router.get("/stats", response_model=PlatformStatsResponse)
def platform_stats(
    db: Session = Depends(get_db),
    _super_admin: Identity = Depends(require_super_admin),
):
    """Platform-wide aggregate stats for the overview dashboard — totals
    and a plan-distribution breakdown only, no per-firm detail (that's what
    /platform/tenants is for). Counts only, never case/document content.
    """
    total_tenants = db.query(Tenant).count()
    active_tenants = db.query(Tenant).filter(Tenant.active.is_(True)).count()
    total_lawyers = (
        db.query(Membership)
        .filter(Membership.role == UserRole.LAWYER, Membership.active.is_(True))
        .count()
    )
    total_clients = (
        db.query(Membership)
        .filter(Membership.role == UserRole.CLIENT, Membership.active.is_(True))
        .count()
    )
    total_cases = db.query(Case).count()
    total_storage_bytes = db.query(func.coalesce(func.sum(Document.file_size), 0)).scalar()

    plan_counts = {plan: 0 for plan in Plan}
    active_subscriptions = db.query(Subscription.plan).filter(Subscription.active.is_(True)).all()
    for (plan,) in active_subscriptions:
        plan_counts[plan] = plan_counts.get(plan, 0) + 1
    # A tenant with no active Subscription row at all still counts as Free
    # (get_active_plan's own fallback) — tenants_with_subscription avoids
    # double-counting one that does have a row.
    tenants_with_subscription = db.query(Subscription.tenant_id).filter(Subscription.active.is_(True)).distinct().count()
    plan_counts[Plan.FREE] += total_tenants - tenants_with_subscription

    return PlatformStatsResponse(
        total_tenants=total_tenants,
        active_tenants=active_tenants,
        total_lawyers=total_lawyers,
        total_clients=total_clients,
        total_cases=total_cases,
        total_storage_bytes=total_storage_bytes,
        plan_distribution=[PlanDistributionEntry(plan=plan, tenant_count=count) for plan, count in plan_counts.items()],
    )


@router.get("/tenant-growth", response_model=list[TenantGrowthPoint])
def tenant_growth(
    db: Session = Depends(get_db),
    _super_admin: Identity = Depends(require_super_admin),
):
    """New tenants per month, trailing TREND_MONTHS months."""
    months = _last_n_months(TREND_MONTHS)
    counts = {key: 0 for key in months}

    created_dates = db.query(Tenant.created_at).all()
    for (created_at,) in created_dates:
        key = (created_at.year, created_at.month)
        if key in counts:
            counts[key] += 1

    return [TenantGrowthPoint(month=f"{year:04d}-{month:02d}", new_tenants=counts[(year, month)]) for year, month in months]


@router.get("/earnings", response_model=PlatformEarningsResponse)
def platform_earnings(
    db: Session = Depends(get_db),
    _super_admin: Identity = Depends(require_super_admin),
):
    """"Earnings" = sum of the hardcoded price of every Subscription active
    at any point in a given month, across all tenants (CLAUDE.md's
    super_admin note) — still no real billing integration, this is a
    display figure only. A subscription is "active during month M" if its
    start_date is before month M ends and it has no end_date, or its
    end_date is on/after month M's start — deliberately a plain sum over
    qualifying rows (not deduped per tenant), matching CLAUDE.md's wording
    literally: a tenant that switched plans mid-month counts both rows that
    month, same as a firm's real bill would reflect both plans being active
    for part of the month.
    """
    months = _last_n_months(TREND_MONTHS)
    subscriptions = db.query(Subscription.plan, Subscription.start_date, Subscription.end_date).all()

    trend: list[EarningsPoint] = []
    for year, month in months:
        month_start, month_end = _month_bounds(year, month)
        total = 0
        for plan, start_date, end_date in subscriptions:
            if start_date >= month_end:
                continue
            if end_date is not None and end_date < month_start:
                continue
            total += PLAN_PRICES_ILS[plan]
        trend.append(EarningsPoint(month=f"{year:04d}-{month:02d}", earnings_ils=total))

    return PlatformEarningsResponse(
        current_month_earnings_ils=trend[-1].earnings_ils if trend else 0,
        trend=trend,
    )


@router.get("/storage-overview", response_model=list[TenantStorageOverviewEntry])
def storage_overview(
    db: Session = Depends(get_db),
    _super_admin: Identity = Depends(require_super_admin),
):
    """Per-tenant storage usage vs. plan quota — which firms are nearing
    their plan's GB quota (CLAUDE.md's super_admin note). Not paginated:
    bounded by how many tenants exist, and the frontend sorts/highlights
    by usage percentage rather than paging through it.
    """
    tenants = db.query(Tenant).order_by(Tenant.name).all()
    usage_by_tenant = dict(
        db.query(Document.tenant_id, func.coalesce(func.sum(Document.file_size), 0)).group_by(Document.tenant_id).all()
    )
    entries = []
    for tenant in tenants:
        plan = get_active_plan(tenant.id, db)
        entries.append(
            TenantStorageOverviewEntry(
                tenant_id=tenant.id,
                name=tenant.name,
                subdomain=tenant.subdomain,
                plan=plan,
                storage_used_bytes=usage_by_tenant.get(tenant.id, 0),
                storage_limit_bytes=PLAN_STORAGE_LIMIT_BYTES[plan],
            )
        )
    return entries


SORTABLE_USER_FIELDS = {
    "name": Identity.name,
    "last_login_at": Identity.last_login_at,
}


@router.get("/users", response_model=Page[PlatformUserResponse])
def list_platform_users(
    search: Optional[str] = Query(None, description="Partial, case-insensitive match on name or email"),
    sort: str = Query("name", description="Column to sort by: name or last_login_at"),
    order: str = Query("asc", description="asc or desc"),
    params: PageParams = Depends(),
    db: Session = Depends(get_db),
    _super_admin: Identity = Depends(require_super_admin),
):
    """Every Identity platform-wide, their last_login_at, and which firms/
    roles they hold — a cross-tenant join through Memberships. Still
    firm-level/account-level data, not case/document content (CLAUDE.md's
    Roles section): knowing *that* someone is a lawyer at two firms is not
    the same as seeing anything about their casework.
    """
    query = db.query(Identity).filter(Identity.is_super_admin.is_(False))
    if search:
        like = f"%{search}%"
        query = query.filter((Identity.name.ilike(like)) | (Identity.email.ilike(like)))

    sort_column = SORTABLE_USER_FIELDS.get(sort, Identity.name)
    # Ties broken by name so pagination stays stable across pages, and so
    # a shared last_login_at value (most often many NULLs, never logged in)
    # renders in a consistent, predictable order rather than DB-default.
    # MySQL has no NULLS FIRST/LAST syntax (unlike Postgres) — SQLAlchemy's
    # .nullslast()/.nullsfirst() compile to invalid SQL on this dialect, so
    # nulls are pushed to the end explicitly via a boolean sort key instead,
    # regardless of direction ("never logged in" trails real timestamps
    # either way, rather than flipping to the front on ascending sort).
    if sort_column is Identity.last_login_at:
        ordering = [
            sort_column.is_(None),
            sort_column.desc() if order == "desc" else sort_column.asc(),
            Identity.name,
        ]
    else:
        ordering = [sort_column.desc() if order == "desc" else sort_column.asc()]
    query = query.order_by(*ordering)

    total = query.count()
    identities = query.offset((params.page - 1) * params.page_size).limit(params.page_size).all()

    identity_ids = [identity.id for identity in identities]
    memberships_by_identity: dict[int, list[MembershipSummary]] = {identity_id: [] for identity_id in identity_ids}
    if identity_ids:
        rows = (
            db.query(Membership, Tenant)
            .join(Tenant, Membership.tenant_id == Tenant.id)
            .filter(Membership.identity_id.in_(identity_ids), Membership.active.is_(True))
            .all()
        )
        for membership, tenant in rows:
            memberships_by_identity[membership.identity_id].append(
                MembershipSummary(
                    tenant_id=tenant.id,
                    tenant_name=tenant.name,
                    subdomain=tenant.subdomain,
                    role=membership.role.value,
                )
            )

    items = [
        PlatformUserResponse(
            id=identity.id,
            name=identity.name,
            email=identity.email,
            last_login_at=identity.last_login_at,
            memberships=memberships_by_identity.get(identity.id, []),
        )
        for identity in identities
    ]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/audit-log", response_model=Page[PlatformAuditLogEntryResponse])
def list_platform_audit_log(
    params: PageParams = Depends(),
    db: Session = Depends(get_db),
    _super_admin: Identity = Depends(require_super_admin),
):
    """super_admin's own action trail (suspend/reactivate) — a separate,
    parallel log from the tenant-scoped AuditLogs every other role writes
    to (CLAUDE.md's PlatformAuditLogs note).
    """
    query = (
        db.query(PlatformAuditLog, Identity, Tenant)
        .join(Identity, PlatformAuditLog.identity_id == Identity.id)
        .join(Tenant, PlatformAuditLog.target_tenant_id == Tenant.id)
        # MySQL's DATETIME default precision is whole seconds, so two
        # actions in quick succession (e.g. this test's own suspend then
        # reactivate) can land the exact same timestamp — id as a
        # tiebreaker is what actually guarantees newest-first, same pattern
        # Narratives' own newest-first ordering already uses.
        .order_by(PlatformAuditLog.timestamp.desc(), PlatformAuditLog.id.desc())
    )
    total = query.count()
    rows = query.offset((params.page - 1) * params.page_size).limit(params.page_size).all()
    items = [
        PlatformAuditLogEntryResponse(
            id=log.id,
            action=log.action,
            target_tenant_name=tenant.name,
            actor_name=identity.name,
            actor_email=identity.email,
            timestamp=log.timestamp,
        )
        for log, identity, tenant in rows
    ]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)
