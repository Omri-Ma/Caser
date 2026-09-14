from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from admin_api.schemas.subscriptions import SubscriptionUsageResponse, SwitchPlanRequest
from shared.database import get_db
from shared.membership import require_role
from shared.models import Membership, Subscription, Tenant
from shared.models.enums import UserRole
from shared.plan_limits import get_plan_usage
from shared.tenant import get_current_tenant
from shared import error_messages as E

router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.get("", response_model=SubscriptionUsageResponse)
def get_subscription(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    return SubscriptionUsageResponse(**get_plan_usage(tenant.id, db))


@router.post("/plan", response_model=SubscriptionUsageResponse)
def switch_plan(
    payload: SwitchPlanRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Self-service plan switch — no payment flow, just marking a new
    Subscriptions row active (CLAUDE.md: "a resource gate, not a commerce
    system"). Downgrades don't retroactively touch existing resources —
    check_plan_limit only ever blocks *new* additions, never deactivates
    anyone or deletes anything, so switching plans here is safe regardless
    of current usage.
    """
    current = (
        db.query(Subscription)
        .filter(Subscription.tenant_id == tenant.id, Subscription.active.is_(True))
        .first()
    )
    if current is not None and current.plan == payload.plan:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.ALREADY_ON_THIS_PLAN)

    if current is not None:
        current.active = False
        current.end_date = date.today()

    new_subscription = Subscription(tenant_id=tenant.id, plan=payload.plan, start_date=date.today(), active=True)
    db.add(new_subscription)
    db.commit()

    return SubscriptionUsageResponse(**get_plan_usage(tenant.id, db))
