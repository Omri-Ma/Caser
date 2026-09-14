from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from shared.models import Document, Membership, MembershipInvite, Subscription
from shared.models.enums import InviteStatus, Plan, UserRole
from shared import error_messages as E

GB = 1024**3

# Hardcoded per-plan limits (CLAUDE.md: "a resource gate, not a commerce
# system" — no billing integration, just a fixed table). Enterprise is a
# hard ceiling for self-service; a firm needing more is a manual/negotiated
# case outside this product's scope.
PLAN_STORAGE_LIMIT_BYTES = {
    Plan.FREE: 1 * GB,
    Plan.PRO: 20 * GB,
    Plan.ENTERPRISE: 100 * GB,
}

# Hardcoded per-plan monthly price (CLAUDE.md's super_admin platform-earnings
# note: "same lightweight pattern already used for per-plan resource
# limits"). No real billing integration anywhere — this is only ever used
# to multiply into a display figure for super_admin's earnings chart.
PLAN_PRICES_ILS = {
    Plan.FREE: 0,
    Plan.PRO: 99,
    Plan.ENTERPRISE: 499,
}

PLAN_LAWYER_LIMITS = {
    Plan.FREE: 3,
    Plan.PRO: 15,
    # Effectively unlimited (still a real, enforced number — check_plan_limit
    # never special-cases Enterprise, per CLAUDE.md's "keep enforcement
    # simple" rule) — the UI displays this plan's lawyer count as "unlimited"
    # rather than "X / 10000", but the mechanism underneath is unchanged.
    Plan.ENTERPRISE: 10_000,
}

# In server/shared on purpose, not duplicated per app (unlike pagination.py/
# errors.py): a plan's limit is a business invariant both apps must agree on
# — two independently-maintained copies risk drifting apart with nothing to
# catch it, unlike pagination's page size which can validly differ per app.


def get_active_plan(tenant_id: int, db: Session) -> Plan:
    """A firm's current plan is whichever Subscriptions row is active — see
    CLAUDE.md's Tenants/Subscriptions notes on why there's no cached copy.
    Falls back to Free if a tenant somehow has no active subscription row.
    """
    subscription = (
        db.query(Subscription)
        .filter(Subscription.tenant_id == tenant_id, Subscription.active.is_(True))
        .first()
    )
    return subscription.plan if subscription else Plan.FREE


def check_plan_limit(tenant_id: int, resource_type: str, db: Session, additional: int = 0) -> None:
    """One reusable per-plan resource guard (CLAUDE.md's Subscriptions
    section). Raises 400 if adding `additional` units of `resource_type`
    would put the tenant over its active plan's limit; otherwise does
    nothing. Only blocks *new* additions, never touches existing resources
    (no forced downgrade cleanup, matching CLAUDE.md's grandfathering rule).

    Two resource types are wired up: "storage_bytes" (Documents upload) and
    "lawyer_count" (adding/reactivating a lawyer membership); more can be
    added as new branches later without changing any call site.
    """
    plan = get_active_plan(tenant_id, db)

    if resource_type == "storage_bytes":
        limit = PLAN_STORAGE_LIMIT_BYTES[plan]
        # Archived documents still count against quota (CLAUDE.md) — only a
        # permanent delete actually frees space — so this sums every
        # Document row regardless of archived_at.
        used = (
            db.query(func.coalesce(func.sum(Document.file_size), 0))
            .filter(Document.tenant_id == tenant_id)
            .scalar()
        )
        if used + additional > limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=E.storage_quota_exceeded(limit // GB),
            )
    elif resource_type == "lawyer_count":
        limit = PLAN_LAWYER_LIMITS[plan]
        # Pending invites count toward the limit here too (CLAUDE.md's
        # MembershipInvites note) — otherwise a firm at its limit could
        # invite far past it and have every invite land at once the moment
        # people accept. A declined (or never-answered) invite doesn't
        # permanently consume a seat: this only blocks *creating new*
        # invites/lawyers while over capacity, never revokes one already sent.
        used = count_active_lawyers(tenant_id, db) + count_pending_lawyer_invites(tenant_id, db)
        if used + additional > limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=E.lawyer_limit_reached(limit),
            )
    else:
        raise ValueError(f"Unknown resource_type: {resource_type}")


def count_active_lawyers(tenant_id: int, db: Session) -> int:
    return (
        db.query(Membership)
        .filter(Membership.tenant_id == tenant_id, Membership.role == UserRole.LAWYER, Membership.active.is_(True))
        .count()
    )


def count_pending_lawyer_invites(tenant_id: int, db: Session) -> int:
    return (
        db.query(MembershipInvite)
        .filter(
            MembershipInvite.tenant_id == tenant_id,
            MembershipInvite.role == UserRole.LAWYER,
            MembershipInvite.status == InviteStatus.PENDING,
        )
        .count()
    )


def get_storage_used_bytes(tenant_id: int, db: Session) -> int:
    # Archived documents still count (see check_plan_limit above).
    return (
        db.query(func.coalesce(func.sum(Document.file_size), 0))
        .filter(Document.tenant_id == tenant_id)
        .scalar()
    )


def get_plan_usage(tenant_id: int, db: Session) -> dict:
    """Everything the office_manager's subscription/plan screen needs in one
    call: current plan plus usage against both hardcoded limits above. Kept
    here rather than in admin_api so the numbers it reports can never drift
    from the numbers check_plan_limit actually enforces.
    """
    plan = get_active_plan(tenant_id, db)
    # lawyer_count is active lawyers only; pending_lawyer_invites is broken
    # out separately (not merged into lawyer_count) so the UI can show both
    # facts ("2 active + 1 pending"), while their *sum* is what actually
    # needs to be compared against lawyer_limit — matching check_plan_limit
    # exactly, which was the actual bug here: this used to report active
    # lawyers only, understating usage relative to what really blocks a new
    # invite (CLAUDE.md's MembershipInvites note: pending invites count too).
    pending_invites = count_pending_lawyer_invites(tenant_id, db)
    return {
        "plan": plan,
        "lawyer_count": count_active_lawyers(tenant_id, db),
        "pending_lawyer_invites": pending_invites,
        "lawyer_limit": PLAN_LAWYER_LIMITS[plan],
        "storage_used_bytes": get_storage_used_bytes(tenant_id, db),
        "storage_limit_bytes": PLAN_STORAGE_LIMIT_BYTES[plan],
    }

