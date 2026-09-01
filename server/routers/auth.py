import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.database import get_db
from core.identity import get_current_identity
from core.security import (
    REFRESH_COOKIE_NAME,
    clear_session_cookies,
    decode_token,
    hash_password,
    set_session_cookies,
    verify_password,
)
from core.tenant import RESERVED_SUBDOMAINS, get_current_tenant
from models import Identity, Membership, Tenant
from models.enums import Plan, UserRole
from schemas.auth import IdentityResponse, LoginRequest, RegisterRequest, SessionResponse, SignupRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=IdentityResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    """Create a bare global account (no firm yet). Used by lawyers/clients
    before an office manager attaches them to a firm.
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


@router.post("/signup", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, response: Response, db: Session = Depends(get_db)):
    """Register a new firm (tenant) plus its first office_manager account.

    If admin_email already has an Identity, that's allowed, not rejected:
    the submitted password is verified against the existing password_hash
    (never a second password created) and a new office_manager Membership
    for the new Tenant is attached to it — the same "attach an existing
    Identity" pattern POST /members already uses, just self-service. This is
    what makes "one login, many firms" hold up in practice.
    """
    subdomain = payload.subdomain.lower()
    if subdomain in RESERVED_SUBDOMAINS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This subdomain is reserved")

    # Fast, friendly pre-checks for the common case. Not sufficient on their
    # own — two concurrent signups can both pass these before either has
    # written a row — so the actual guard is the try/except around the
    # insert below, which catches the database's unique-constraint rejection.
    if db.query(Tenant).filter(Tenant.subdomain == subdomain).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subdomain already taken")

    existing_identity = db.query(Identity).filter(Identity.email == payload.admin_email).first()
    if existing_identity is not None:
        if not verify_password(payload.admin_password, existing_identity.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="An account with this email already exists — log in with its existing password to found a firm",
            )

    tenant = Tenant(name=payload.firm_name, subdomain=subdomain, plan=Plan.FREE, active=True)
    db.add(tenant)

    if existing_identity is not None:
        identity = existing_identity
    else:
        identity = Identity(
            name=payload.admin_name,
            email=payload.admin_email,
            password_hash=hash_password(payload.admin_password),
        )
        db.add(identity)

    try:
        db.flush()  # assigns tenant.id/identity.id before the row that references them
        membership = Membership(identity_id=identity.id, tenant_id=tenant.id, role=UserRole.OFFICE_MANAGER)
        db.add(membership)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Either the subdomain or (for a brand-new email) the email lost a
        # race to a concurrent signup between the pre-check above and this
        # insert — inspect which unique constraint the database rejected so
        # the error stays as accurate as the pre-check would have been.
        detail = "Email already registered" if "email" in str(exc.orig).lower() else "Subdomain already taken"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    db.refresh(identity)

    set_session_cookies(response, identity.id, identity.token_version)
    return SessionResponse(name=identity.name, email=identity.email, role=membership.role)


@router.post("/login", response_model=SessionResponse)
def login(
    payload: LoginRequest,
    response: Response,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
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
    # of the token (another browser, a saved cookie) valid until it expires.
    identity.token_version += 1
    db.commit()
    clear_session_cookies(response)


@router.get("/me", response_model=IdentityResponse)
def me(identity: Identity = Depends(get_current_identity)):
    return IdentityResponse(id=identity.id, name=identity.name, email=identity.email)
