from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from admin_api.core.pagination import Page, PageParams
from admin_api.schemas.platform import PlatformStatsResponse, TenantSummaryResponse
from shared.database import get_db
from shared.models import Case, Identity, Membership, Tenant
from shared.models.enums import UserRole
from shared.plan_limits import get_active_plan
from shared.platform import require_super_admin

router = APIRouter(prefix="/platform", tags=["platform"])

# super_admin's own explicitly separate code path (CLAUDE.md's Multi-tenancy
# architecture): every query in this file spans every tenant on purpose, so
# none of it goes through get_current_tenant / get_tenant_scoped — those
# assume exactly one tenant in request scope, which doesn't apply here at
# all. Firm-level/aggregate data only — nothing here ever touches Cases'
# content, CaseAssignments, Documents, or WorkLogs rows themselves, only
# counts against them, matching the boundary CLAUDE.md's Roles section draws
# for super_admin.


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


@router.get("/tenants", response_model=Page[TenantSummaryResponse])
def list_tenants(
    params: PageParams = Depends(),
    db: Session = Depends(get_db),
    _super_admin: Identity = Depends(require_super_admin),
):
    """Every Tenant, regardless of subdomain — the cross-tenant firm list
    the platform dashboard shows. Note this query intentionally omits the
    `active = True` filter get_current_tenant applies: a super_admin has to
    see suspended firms too, in order to reactivate them.
    """
    query = db.query(Tenant).order_by(Tenant.name)
    total = query.count()
    rows = query.offset((params.page - 1) * params.page_size).limit(params.page_size).all()
    items = [_tenant_summary(tenant, db) for tenant in rows]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.post("/tenants/{tenant_id}/suspend", response_model=TenantSummaryResponse)
def suspend_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    _super_admin: Identity = Depends(require_super_admin),
):
    """Flips Tenants.active off. get_current_tenant already filters on
    active = True, so this alone is a full, immediate lockout for every
    role at that firm, including its own office_manager (CLAUDE.md's
    Tenants note) — reactivate_tenant below is the only way back in.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    tenant.active = False
    db.commit()
    db.refresh(tenant)
    return _tenant_summary(tenant, db)


@router.post("/tenants/{tenant_id}/reactivate", response_model=TenantSummaryResponse)
def reactivate_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    _super_admin: Identity = Depends(require_super_admin),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    tenant.active = True
    db.commit()
    db.refresh(tenant)
    return _tenant_summary(tenant, db)


@router.get("/stats", response_model=PlatformStatsResponse)
def platform_stats(
    db: Session = Depends(get_db),
    _super_admin: Identity = Depends(require_super_admin),
):
    """Platform-wide aggregate stats for the overview dashboard — totals
    only, no per-firm breakdown (that's what /platform/tenants is for).
    """
    total_tenants = db.query(Tenant).count()
    active_tenants = db.query(Tenant).filter(Tenant.active.is_(True)).count()
    total_lawyers = (
        db.query(Membership)
        .filter(Membership.role == UserRole.LAWYER, Membership.active.is_(True))
        .count()
    )
    total_cases = db.query(Case).count()
    return PlatformStatsResponse(
        total_tenants=total_tenants,
        active_tenants=active_tenants,
        total_lawyers=total_lawyers,
        total_cases=total_cases,
    )
