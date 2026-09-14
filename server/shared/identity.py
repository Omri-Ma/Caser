from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.security import ACCESS_COOKIE_NAME, decode_token
from shared.models import Identity
from shared import error_messages as E


def record_login(identity: Identity, db: Session) -> None:
    """Stamps Identities.last_login_at on a successful login — one column
    regardless of which app/entry point was used (a tenant subdomain,
    either lobby, or platform.<BASE_DOMAIN> for super_admin), since it's the
    same global account either way (CLAUDE.md's Identities note). Shared so
    every login route stamps it identically instead of five separate copies.
    """
    identity.last_login_at = datetime.now(timezone.utc)
    db.commit()


def get_current_identity(request: Request, db: Session = Depends(get_db)) -> Identity:
    """Resolve who is logged in from the session cookie. Tenant-agnostic —
    just answers "who is this person", not "what can they do here".
    """
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=E.NOT_LOGGED_IN)

    try:
        decoded = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=E.INVALID_OR_EXPIRED_SESSION)

    if decoded.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=E.INVALID_SESSION_TOKEN)

    identity = db.query(Identity).filter(Identity.id == decoded["identity_id"]).first()
    if identity is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=E.ACCOUNT_NO_LONGER_EXISTS)

    if decoded.get("token_version") != identity.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=E.SESSION_INVALIDATED)

    return identity
