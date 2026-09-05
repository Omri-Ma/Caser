import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from client_api.schemas.auth import IdentityResponse, LoginRequest, RegisterRequest, SessionResponse
from shared.database import get_db
from shared.identity import get_current_identity
from shared.models import Identity, Membership, Tenant
from shared.models.enums import UserRole
from shared.security import (
    REFRESH_COOKIE_NAME,
    clear_session_cookies,
    decode_token,
    hash_password,
    set_session_cookies,
    verify_password,
)
from shared.tenant import get_current_tenant

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=IdentityResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    """Create a bare global account (no firm yet). Used by lawyers/clients
    before an office manager attaches them to a firm via admin_api.
    """
    if db.query(Identity).filter(Identity.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    identity = Identity(name=payload.name, email=payload.email, password_hash=hash_password(payload.password))
    db.add(identity)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    db.refresh(identity)

    set_session_cookies(response, identity.id, identity.token_version)
    return IdentityResponse(id=identity.id, name=identity.name, email=identity.email)


@router.post("/login", response_model=SessionResponse)
def login(
    payload: LoginRequest,
    response: Response,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """lawyer/client login only — nobody cross-logs into the other app
    (CLAUDE.md's Roles section). An office_manager account exists too (same
    Identities table), but its Membership.role at this tenant won't be
    LAWYER/CLIENT, so it's rejected here and pointed at the admin portal.
    """
    identity = db.query(Identity).filter(Identity.email == payload.email).first()
    if identity is None or not verify_password(payload.password, identity.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    membership = (
        db.query(Membership)
        .filter(Membership.identity_id == identity.id, Membership.tenant_id == tenant.id)
        .first()
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to this firm")
    if membership.role not in (UserRole.LAWYER, UserRole.CLIENT):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account logs in through the admin portal, not the client portal",
        )

    set_session_cookies(response, identity.id, identity.token_version)
    return SessionResponse(name=identity.name, email=identity.email, role=membership.role)


@router.post("/refresh", status_code=status.HTTP_204_NO_CONTENT)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in")

    try:
        decoded = decode_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")

    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    identity = db.query(Identity).filter(Identity.id == decoded["identity_id"]).first()
    if identity is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account no longer exists")

    if decoded.get("token_version") != identity.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has been invalidated, please log in again")

    set_session_cookies(response, identity.id, identity.token_version)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    # Bumping token_version is the actual invalidation: JWTs aren't stored
    # server-side, so deleting the cookie alone would leave any other copy
    # of the token (another browser, a saved cookie, or one held by the
    # other app's session) valid until it expires.
    identity.token_version += 1
    db.commit()
    clear_session_cookies(response)


@router.get("/me", response_model=IdentityResponse)
def me(identity: Identity = Depends(get_current_identity)):
    return IdentityResponse(id=identity.id, name=identity.name, email=identity.email)
