import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from shared.models import Identity, PasswordResetToken
from shared.security import hash_password, verify_password

# Fourth narrow extension to server/shared (alongside storage.py,
# plan_limits.py, worklog_import.py — see CLAUDE.md's Code quality section):
# self-service password change and the forgot-password token lifecycle are
# identical rules for both apps (same hashing, same expiry, same
# token_version invalidation), so they live here once with each app exposing
# its own thin route, rather than being duplicated per app.

RESET_TOKEN_EXPIRE_MINUTES = 30


class WrongPasswordError(Exception):
    """Raised when a self-service change-password call's current_password
    doesn't match — distinct from an invalid/expired reset token so each
    route can translate it into the right HTTP status."""


def change_password(identity: Identity, current_password: str, new_password: str, db: Session) -> None:
    """Self-service "change my password" while logged in — every role can
    do this for their own account (CLAUDE.md's office_manager authority
    boundary: password changes are entirely self-service, never a lever
    another party has). Bumps token_version so any *other* outstanding
    session (another browser, a stale copy) is invalidated; the caller is
    responsible for re-issuing this request's own session cookies.
    """
    if not verify_password(current_password, identity.password_hash):
        raise WrongPasswordError("Current password is incorrect")

    identity.password_hash = hash_password(new_password)
    identity.token_version += 1
    db.commit()


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_reset_token(identity_id: int, db: Session) -> str:
    """Issue a single-use, expiring password-reset token for this identity.
    Only the hash is stored (same reasoning as password_hash) — the raw
    token only ever exists in the one-time link itself, returned here so the
    caller can build that link.

    Invalidates every earlier outstanding (unused, unexpired) token for this
    identity first — requesting "forgot password" twice used to leave two
    simultaneously-valid links outstanding, both independently redeemable.
    Marking the old ones used (not deleting them — same "used_at is the
    record" pattern a real redemption uses, not a special-cased row) means
    only the newest link is ever valid, matching how most real password-
    reset flows behave (a fresh request supersedes the last one).
    """
    # Filtered in Python, not SQL, for the not-yet-expired check — MySQL's
    # DATETIME column has no timezone of its own, so comparing it against a
    # timezone-aware Python value at the SQL layer is unreliable; the same
    # naive/aware normalization redeem_reset_token already does below is
    # applied here too.
    now = datetime.now(timezone.utc)
    unused_tokens = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.identity_id == identity_id, PasswordResetToken.used_at.is_(None))
        .all()
    )
    for stale in unused_tokens:
        expires_at = stale.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at >= now:
            stale.used_at = now

    raw_token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            identity_id=identity_id,
            token_hash=_hash_token(raw_token),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
        )
    )
    db.commit()
    return raw_token


def redeem_reset_token(raw_token: str, new_password: str, db: Session) -> Optional[Identity]:
    """Validate and consume a reset token: must exist, be unused, and not be
    expired. On success, sets the new password_hash and bumps token_version
    (invalidating any session that was open under the old password), marks
    the token used, and returns the identity. Returns None on any failure —
    deliberately one generic outcome, not distinct "expired" vs "already
    used" vs "unknown" messages, so a stale/guessed token can't be used to
    probe token state.
    """
    token_hash = _hash_token(raw_token)
    token = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()
    if token is None or token.used_at is not None:
        return None

    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None

    identity = db.query(Identity).filter(Identity.id == token.identity_id).first()
    if identity is None:
        return None

    identity.password_hash = hash_password(new_password)
    identity.token_version += 1
    token.used_at = datetime.now(timezone.utc)
    db.commit()
    return identity
