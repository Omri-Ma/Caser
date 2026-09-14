import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from client_api.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    GenericMessageResponse,
    IdentityResponse,
    LobbyLoginRequest,
    LobbyLoginResponse,
    LobbyTenantOption,
    LoginRequest,
    PendingInviteOption,
    RegisterRequest,
    ResetPasswordRequest,
    SessionResponse,
)
from shared.database import get_db
from shared.dev_outbox import read_dev_outbox, write_dev_outbox
from shared.identity import get_current_identity
from shared.invites import resolve_invites_on_register
from shared.models import Identity, Membership, MembershipInvite, Tenant
from shared.models.enums import InviteStatus, UserRole
from shared.password_reset import WrongPasswordError, change_password, create_reset_token, redeem_reset_token
from shared.security import (
    REFRESH_COOKIE_NAME,
    clear_session_cookies,
    decode_token,
    hash_password,
    set_session_cookies,
    verify_password,
)
from shared.tenant import BASE_DOMAIN, get_current_tenant

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_identity_response(identity: Identity) -> IdentityResponse:
    return IdentityResponse(id=identity.id, name=identity.name, email=identity.email)


@router.post("/register", response_model=IdentityResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    """Create a bare global account. Used two ways: a lawyer/client
    registering with no invite yet (an office manager attaches them to a
    firm afterward), or — more commonly now — someone following an invite
    link for an email with no Identity yet. In the second case, a
    *successful* registration for that exact email is itself the
    acceptance (CLAUDE.md's MembershipInvites note) — no separate
    confirmation step, so every matching pending invite resolves to
    accepted immediately below.
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

    resolve_invites_on_register(identity, db)

    set_session_cookies(response, identity.id, identity.token_version)
    return _to_identity_response(identity)


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
        .filter(
            Membership.identity_id == identity.id,
            Membership.tenant_id == tenant.id,
            Membership.active.is_(True),
        )
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


@router.post("/lobby-login", response_model=LobbyLoginResponse)
def lobby_login(payload: LobbyLoginRequest, response: Response, db: Session = Depends(get_db)):
    """lawyer/client login from the lobby (www.<BASE_DOMAIN>) — CLAUDE.md's
    Multi-tenancy architecture. Mirrors admin_api's lobby-login: same
    password check, but resolves active LAWYER/CLIENT memberships (at active
    tenants) instead of OFFICE_MANAGER ones. role is included per option
    since it's needed to redirect straight into the right nav on the tenant
    subdomain landing page — that page is a different origin, so it can't
    read anything stored here.
    """
    identity = db.query(Identity).filter(Identity.email == payload.email).first()
    if identity is None or not verify_password(payload.password, identity.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    memberships = (
        db.query(Membership, Tenant)
        .join(Tenant, Membership.tenant_id == Tenant.id)
        .filter(
            Membership.identity_id == identity.id,
            Membership.role.in_([UserRole.LAWYER, UserRole.CLIENT]),
            Membership.active.is_(True),
            Tenant.active.is_(True),
        )
        .all()
    )
    pending_invites = (
        db.query(MembershipInvite, Tenant)
        .join(Tenant, MembershipInvite.tenant_id == Tenant.id)
        .filter(MembershipInvite.email == identity.email, MembershipInvite.status == InviteStatus.PENDING)
        .all()
    )

    if not memberships and not pending_invites:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No lawyer or client account found for this email at any firm",
        )

    set_session_cookies(response, identity.id, identity.token_version)
    return LobbyLoginResponse(
        name=identity.name,
        email=identity.email,
        tenants=[
            LobbyTenantOption(
                tenant_id=tenant.id, subdomain=tenant.subdomain, firm_name=tenant.name, role=membership.role
            )
            for membership, tenant in memberships
        ],
        pending_invites=[
            PendingInviteOption(
                invite_id=invite.id, tenant_id=tenant.id, subdomain=tenant.subdomain, firm_name=tenant.name, role=invite.role
            )
            for invite, tenant in pending_invites
        ],
    )


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
    return _to_identity_response(identity)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_my_password(
    payload: ChangePasswordRequest,
    response: Response,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """Self-service, for every role — see admin_api's identical route for
    the full reasoning (shared/password_reset.py is the actual shared
    logic; this is just this app's thin route on top of it).
    """
    try:
        change_password(identity, payload.current_password, payload.new_password, db)
    except WrongPasswordError:
        # 400, not 401 — see admin_api's identical route for the full
        # reasoning (a 401 here collided with apiFetch's generic
        # "401 == expired session" handling and bounced the user to /login).
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    set_session_cookies(response, identity.id, identity.token_version)


@router.post("/forgot-password", response_model=GenericMessageResponse)
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """Always the same generic response regardless of whether the email
    matched a real account (CLAUDE.md's PasswordResetTokens note — never
    reveal which emails are registered). See admin_api's identical route.
    """
    identity = db.query(Identity).filter(Identity.email == payload.email).first()
    if identity is not None:
        raw_token = create_reset_token(identity.id, db)
        origin = request.headers.get("origin") or f"http://www.{BASE_DOMAIN}"
        link = f"{origin}/reset-password?token={raw_token}"
        write_dev_outbox(identity.email, link)

    return GenericMessageResponse(message="If an account exists for that email, a reset link has been sent.")


@router.post("/reset-password", response_model=GenericMessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    identity = redeem_reset_token(payload.token, payload.new_password, db)
    if identity is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This reset link is invalid or has expired")

    return GenericMessageResponse(message="Password updated. You can now log in with your new password.")


@router.get("/dev-outbox")
def dev_outbox(email: str | None = None):
    """Dev-only stand-in for real email delivery — see forgot_password above."""
    return read_dev_outbox(email)
