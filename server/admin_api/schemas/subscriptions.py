from pydantic import BaseModel

from shared.models.enums import Plan


class SubscriptionUsageResponse(BaseModel):
    """The firm's current plan (from the active Subscriptions row — Tenants
    itself has no plan column, CLAUDE.md) plus usage against that plan's
    hardcoded limits (shared/plan_limits.py, the same numbers
    check_plan_limit actually enforces).
    """

    plan: Plan
    lawyer_count: int
    # Broken out separately from lawyer_count (not merged into it) so the
    # UI can show both facts, but lawyer_count + pending_lawyer_invites is
    # what actually needs comparing against lawyer_limit — matching
    # check_plan_limit exactly (shared/plan_limits.py's MembershipInvites
    # note: pending invites count toward the limit too).
    pending_lawyer_invites: int
    lawyer_limit: int
    storage_used_bytes: int
    storage_limit_bytes: int


class SwitchPlanRequest(BaseModel):
    plan: Plan
