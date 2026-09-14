from datetime import datetime, timezone

from sqlalchemy.orm import Session

from shared.models import Identity, Membership, MembershipInvite
from shared.models.enums import InviteStatus, UserRole
from shared import error_messages as E

# Fifth narrow extension to server/shared (alongside storage.py,
# plan_limits.py, worklog_import.py, password_reset.py — see CLAUDE.md's
# Code quality section): the invite lifecycle is identical for both apps
# (admin_api creates invites, client_api accepts/declines them, register()
# auto-resolves them), so it lives here once rather than being duplicated.


class DuplicateInviteError(Exception):
    """Raised when the target email already has a pending invite at this
    tenant, or an already-active Membership there (CLAUDE.md's
    MembershipInvites note: both are rejected outright, no duplicate)."""


def create_invite(tenant_id: int, email: str, role: UserRole, invited_by_membership_id: int, db: Session) -> MembershipInvite:
    identity = db.query(Identity).filter(Identity.email == email).first()
    if identity is not None:
        existing_membership = (
            db.query(Membership)
            .filter(Membership.identity_id == identity.id, Membership.tenant_id == tenant_id)
            .first()
        )
        if existing_membership is not None and existing_membership.active:
            raise DuplicateInviteError(E.ALREADY_MEMBER_OF_FIRM)

    existing_pending = (
        db.query(MembershipInvite)
        .filter(
            MembershipInvite.tenant_id == tenant_id,
            MembershipInvite.email == email,
            MembershipInvite.status == InviteStatus.PENDING,
        )
        .first()
    )
    if existing_pending is not None:
        raise DuplicateInviteError(E.INVITE_ALREADY_PENDING)

    invite = MembershipInvite(tenant_id=tenant_id, email=email, role=role, invited_by=invited_by_membership_id)
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


def _attach_membership(identity_id: int, tenant_id: int, role: UserRole, db: Session) -> Membership:
    """Create or reactivate the Membership row an accepted invite grants —
    same "reactivate an inactive row instead of a duplicate insert" logic
    the old instant-add route used (CLAUDE.md's Memberships.active note):
    the identity_id+tenant_id unique constraint would reject a fresh insert
    while a previously-removed row still exists.
    """
    existing = (
        db.query(Membership)
        .filter(Membership.identity_id == identity_id, Membership.tenant_id == tenant_id)
        .first()
    )
    if existing is not None:
        existing.active = True
        existing.role = role
        db.commit()
        db.refresh(existing)
        return existing

    membership = Membership(identity_id=identity_id, tenant_id=tenant_id, role=role)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def accept_invite(invite: MembershipInvite, identity: Identity, db: Session) -> Membership:
    membership = _attach_membership(identity.id, invite.tenant_id, invite.role, db)
    invite.status = InviteStatus.ACCEPTED
    invite.responded_at = datetime.now(timezone.utc)
    db.commit()
    return membership


def decline_invite(invite: MembershipInvite, db: Session) -> None:
    invite.status = InviteStatus.DECLINED
    invite.responded_at = datetime.now(timezone.utc)
    db.commit()


def resolve_invites_on_register(identity: Identity, db: Session) -> None:
    """A successful registration for an email with pending invites *is* the
    acceptance (CLAUDE.md's MembershipInvites note) — no separate
    confirmation step after that. Resolves every pending invite for this
    email, not just one: the same not-yet-registered person could have
    been invited by more than one firm before ever creating an account.
    """
    pending = (
        db.query(MembershipInvite)
        .filter(MembershipInvite.email == identity.email, MembershipInvite.status == InviteStatus.PENDING)
        .all()
    )
    for invite in pending:
        accept_invite(invite, identity, db)


def list_pending_invites_for_email(email: str, db: Session) -> list[MembershipInvite]:
    return (
        db.query(MembershipInvite)
        .filter(MembershipInvite.email == email, MembershipInvite.status == InviteStatus.PENDING)
        .all()
    )
