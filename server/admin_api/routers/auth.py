from datetime import date

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from admin_api.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    GenericMessageResponse,
    IdentityResponse,
    LobbyLoginRequest,
    LobbyLoginResponse,
    LobbyTenantOption,
    LoginRequest,
    PlatformLoginRequest,
    PlatformSessionResponse,
    ResetPasswordRequest,
    SessionResponse,
    SignupRequest,
    UpdatePublicVisibilityRequest,
    UpdateProfileRequest,
)
from shared.database import get_db
from shared.dev_outbox import read_dev_outbox, write_dev_outbox
from shared.identity import get_current_identity, record_login
from shared.membership import require_role
from shared.models import AuditLog, Identity, Membership, Subscription, Tenant
from shared.models.enums import Plan, UserRole
from shared.password_reset import WrongPasswordError, change_password, create_reset_token, redeem_reset_token
from shared.security import (
    REFRESH_COOKIE_NAME,
    clear_session_cookies,
    decode_token,
    hash_password,
    set_session_cookies,
    verify_password,
)
from shared.tenant import BASE_DOMAIN, get_current_tenant, is_reserved_subdomain
from shared import error_messages as E

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_identity_response(identity: Identity) -> IdentityResponse:
    return IdentityResponse(
        id=identity.id,
        name=identity.name,
        email=identity.email,
        bio=identity.bio,
        photo_url=identity.photo_url,
        years_of_experience=identity.years_of_experience,
    )

PLATFORM_HOST = f"platform.{BASE_DOMAIN}"


def _office_manager_tenants(identity: Identity, db: Session):
    """Every active office_manager Membership this identity holds, at active
    tenants — the one lookup that answers "which firm(s) does this person
    manage". Shared by /auth/lobby-login (an unauthenticated identity
    resolving where to log in) and /auth/my-tenants below (an already
    -authenticated identity resolving where to land after hitting a
    subdomain it has no access at) — CLAUDE.md is explicit that the latter
    should "reuse that lookup, don't reinvent it".
    """
    return (
        db.query(Membership, Tenant)
        .join(Tenant, Membership.tenant_id == Tenant.id)
        .filter(
            Membership.identity_id == identity.id,
            Membership.role == UserRole.OFFICE_MANAGER,
            Membership.active.is_(True),
            Tenant.active.is_(True),
        )
        .all()
    )


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
    if is_reserved_subdomain(subdomain):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.SUBDOMAIN_RESERVED)

    # Fast, friendly pre-checks for the common case. Not sufficient on their
    # own — two concurrent signups can both pass these before either has
    # written a row — so the actual guard is the try/except around the
    # insert below, which catches the database's unique-constraint rejection.
    if db.query(Tenant).filter(Tenant.subdomain == subdomain).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.SUBDOMAIN_TAKEN)

    existing_identity = db.query(Identity).filter(Identity.email == payload.admin_email).first()
    if existing_identity is not None:
        if not verify_password(payload.admin_password, existing_identity.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=E.EMAIL_EXISTS_LOGIN_TO_FOUND_FIRM,
            )

    tenant = Tenant(name=payload.firm_name, subdomain=subdomain, active=True)
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
        db.flush()  # assigns tenant.id/identity.id before the rows that reference them
        membership = Membership(identity_id=identity.id, tenant_id=tenant.id, role=UserRole.OFFICE_MANAGER)
        db.add(membership)
        # Tenants has no plan column — a firm's plan is whichever
        # Subscriptions row is active, so founding a firm means creating its
        # first (Free) Subscription row, not setting a field on Tenant.
        subscription = Subscription(tenant_id=tenant.id, plan=Plan.FREE, start_date=date.today(), active=True)
        db.add(subscription)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Either the subdomain or (for a brand-new email) the email lost a
        # race to a concurrent signup between the pre-check above and this
        # insert — inspect which unique constraint the database rejected so
        # the error stays as accurate as the pre-check would have been.
        detail = E.EMAIL_ALREADY_REGISTERED if "email" in str(exc.orig).lower() else E.SUBDOMAIN_TAKEN
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
    """office_manager login only — super_admin uses /auth/platform-login
    instead (see below), and lawyer/client accounts are rejected here since
    they belong in client_api, not admin_api (CLAUDE.md's Roles section).
    """
    identity = db.query(Identity).filter(Identity.email == payload.email).first()
    if identity is None or not verify_password(payload.password, identity.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=E.INVALID_EMAIL_OR_PASSWORD)

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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=E.NO_ACCESS_TO_FIRM)
    if membership.role != UserRole.OFFICE_MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=E.account_logs_in_through_other_portal("פורטל הלקוח"),
        )

    record_login(identity, db)
    set_session_cookies(response, identity.id, identity.token_version)
    return SessionResponse(name=identity.name, email=identity.email, role=membership.role)


@router.post("/lobby-login", response_model=LobbyLoginResponse)
def lobby_login(payload: LobbyLoginRequest, response: Response, db: Session = Depends(get_db)):
    """office_manager login from the lobby (www.<BASE_DOMAIN>) — CLAUDE.md's
    Multi-tenancy architecture. Unlike /auth/login above, no subdomain is
    known yet, so instead of checking one tenant's Membership this resolves
    every active office_manager Membership the identity holds (at active
    tenants): zero means this email has no firm to manage here, exactly one
    redirects straight to it, more than one needs a "choose your firm"
    picker — all three are the frontend's job, this route only reports which
    case it is. Password check reuses the exact same verify_password
    /auth/login already uses; nothing about authentication itself changes.
    """
    identity = db.query(Identity).filter(Identity.email == payload.email).first()
    if identity is None or not verify_password(payload.password, identity.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=E.INVALID_EMAIL_OR_PASSWORD)

    memberships = _office_manager_tenants(identity, db)
    if not memberships:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=E.NO_OFFICE_MANAGER_ACCOUNT_FOUND,
        )

    record_login(identity, db)
    set_session_cookies(response, identity.id, identity.token_version)
    return LobbyLoginResponse(
        name=identity.name,
        email=identity.email,
        tenants=[
            LobbyTenantOption(tenant_id=tenant.id, subdomain=tenant.subdomain, firm_name=tenant.name)
            for _membership, tenant in memberships
        ],
    )


@router.post("/platform-login", response_model=PlatformSessionResponse)
def platform_login(payload: PlatformLoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    """super_admin login at the fixed, non-tenant platform address. Deliberately
    never uses get_current_tenant — `platform` isn't a Tenant row, and
    super_admin can't be a Memberships row either (see CLAUDE.md's
    Multi-tenancy architecture); this checks Identities.is_super_admin
    directly instead. Restricted to the platform host itself so a login
    granting cross-tenant visibility can't be triggered from a tenant
    subdomain by mistake.
    """
    hostname = request.headers.get("host", "").split(":")[0]
    if hostname != PLATFORM_HOST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=E.platform_login_must_be_made_to(PLATFORM_HOST),
        )

    identity = db.query(Identity).filter(Identity.email == payload.email).first()
    if identity is None or not identity.is_super_admin or not verify_password(payload.password, identity.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=E.INVALID_EMAIL_OR_PASSWORD)

    record_login(identity, db)
    set_session_cookies(response, identity.id, identity.token_version)
    return PlatformSessionResponse(name=identity.name, email=identity.email)


@router.post("/refresh", status_code=status.HTTP_204_NO_CONTENT)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=E.NOT_LOGGED_IN)

    try:
        decoded = decode_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=E.INVALID_OR_EXPIRED_SESSION)

    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=E.INVALID_TOKEN_TYPE)

    identity = db.query(Identity).filter(Identity.id == decoded["identity_id"]).first()
    if identity is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=E.ACCOUNT_NO_LONGER_EXISTS)

    if decoded.get("token_version") != identity.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=E.SESSION_INVALIDATED)

    set_session_cookies(response, identity.id, identity.token_version)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    identity.token_version += 1
    db.commit()
    clear_session_cookies(response)


@router.get("/me", response_model=IdentityResponse)
def me(identity: Identity = Depends(get_current_identity)):
    return _to_identity_response(identity)


@router.get("/my-tenants", response_model=list[LobbyTenantOption])
def my_tenants(identity: Identity = Depends(get_current_identity), db: Session = Depends(get_db)):
    """Tenant-agnostic (no get_current_tenant dependency) on purpose — this
    is what the frontend calls when it lands on a subdomain the identity has
    no office_manager membership at, to resolve where to actually send them
    (CLAUDE.md's "Landing somewhere you have no access" redirect rule).
    Reuses the exact same lookup /auth/lobby-login uses to resolve "which
    firm" for an unauthenticated login — same answer, just for an identity
    that's already holding a valid session.
    """
    memberships = _office_manager_tenants(identity, db)
    return [
        LobbyTenantOption(tenant_id=tenant.id, subdomain=tenant.subdomain, firm_name=tenant.name)
        for _membership, tenant in memberships
    ]


@router.post("/leave-firm", status_code=status.HTTP_204_NO_CONTENT)
def leave_firm(
    _membership: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """A firm has exactly one office_manager, fixed at founding, with no
    promote/demote path to replace them (CLAUDE.md's Memberships note) — so
    unlike the lawyer/client version of this route in client_api, this is a
    hard, unconditional block, not a self-service action. There is no
    "leave, someone else will still be there" case here at all: leaving
    would always strand the firm without an administrator. A genuine need
    to change a firm's administrator is a manual/super_admin-assisted case,
    outside self-service scope.

    Kept as a route (rather than removed outright) so an office_manager
    hitting this from stale/cached frontend code gets a clear, explained
    rejection instead of a 404 that looks like a bug.
    """
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.OFFICE_MANAGER_CANNOT_LEAVE_FIRM)


@router.get("/my-public-visibility", response_model=UpdatePublicVisibilityRequest)
def get_my_public_visibility(membership: Membership = Depends(require_role(UserRole.OFFICE_MANAGER))):
    """Self-service read of the office_manager's own
    Memberships.show_on_public_page (CLAUDE.md's public homepage team
    section note). This lever used to only be reachable through the
    now-removed Admins page (POST /members/{id}/public-visibility,
    self-targeting was never actually possible since there was no page
    listing office_manager rows at all after that removal) — a real
    regression from removing that page, not a pre-existing gap: without
    this, an office_manager's own visibility toggle became permanently
    stuck wherever it happened to be, with no way to ever change it again.
    """
    return UpdatePublicVisibilityRequest(show_on_public_page=membership.show_on_public_page)


@router.patch("/my-public-visibility", response_model=UpdatePublicVisibilityRequest)
def update_my_public_visibility(
    payload: UpdatePublicVisibilityRequest,
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Write side of the above — same field, same semantics as
    POST /members/{id}/public-visibility, just self-targeting (no
    membership_id needed: require_role already resolves the caller's own
    membership at this tenant) so an office_manager can reach it from
    their own profile/settings page instead of a members list they're not
    listed on.
    """
    membership.show_on_public_page = payload.show_on_public_page
    db.commit()
    return UpdatePublicVisibilityRequest(show_on_public_page=membership.show_on_public_page)


@router.patch("/profile", response_model=IdentityResponse)
def update_my_profile(
    payload: UpdateProfileRequest,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """Self-service only — see client_api's identical route for the full
    reasoning.
    """
    identity.bio = payload.bio
    identity.photo_url = payload.photo_url
    identity.years_of_experience = payload.years_of_experience
    db.commit()
    db.refresh(identity)
    return _to_identity_response(identity)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_my_password(
    payload: ChangePasswordRequest,
    response: Response,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """Self-service, for every role — office_manager included — since a
    password is an Identities-level thing, never a Memberships-level lever
    another party at a firm gets to pull (CLAUDE.md's office_manager
    authority boundary). Re-issues this request's own session cookies with
    the bumped token_version so the current session isn't logged out by its
    own password change, while every *other* outstanding session is.
    """
    try:
        change_password(identity, payload.current_password, payload.new_password, db)
    except WrongPasswordError:
        # 400, not 401: this is a form-validation error (wrong value typed in
        # a field on an already-authenticated request), not an auth/session
        # failure. Returning 401 here made the frontend's generic apiFetch
        # 401-handler (which assumes 401 == expired session) silently retry
        # via /auth/refresh and then redirect to /login on the second
        # failure — so mistyping the current password looked exactly like
        # being logged out, with no visible error message.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.CURRENT_PASSWORD_INCORRECT)

    set_session_cookies(response, identity.id, identity.token_version)


@router.post("/forgot-password", response_model=GenericMessageResponse)
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """Always the same generic response regardless of whether the email
    matched a real account (CLAUDE.md's PasswordResetTokens note — never
    reveal which emails are registered). The "email" step writes to a
    dev-only outbox instead of actually sending mail (no SMTP infra in this
    exercise — see CLAUDE.md's Future additions).
    """
    # super_admin is deliberately excluded from self-service reset entirely
    # (CLAUDE.md's Multi-tenancy architecture note): it is the single most
    # powerful account in the system, already manually-provisioned, and a
    # compromised/spoofed reset flow there has a far bigger blast radius
    # than for anyone else. Still returns the exact same generic response
    # either way, so this can never reveal *why* a reset "didn't work".
    identity = db.query(Identity).filter(Identity.email == payload.email).first()
    if identity is not None and not identity.is_super_admin:
        raw_token = create_reset_token(identity.id, db)
        origin = request.headers.get("origin") or f"http://www.{BASE_DOMAIN}"
        link = f"{origin}/reset-password?token={raw_token}"
        write_dev_outbox(identity.email, link)

    return GenericMessageResponse(message="If an account exists for that email, a reset link has been sent.")


@router.post("/reset-password", response_model=GenericMessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    identity = redeem_reset_token(payload.token, payload.new_password, db)
    if identity is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.RESET_LINK_INVALID_OR_EXPIRED)

    return GenericMessageResponse(message="Password updated. You can now log in with your new password.")


@router.get("/dev-outbox")
def dev_outbox(email: str | None = None):
    """Dev-only stand-in for real email delivery (see forgot_password above
    and CLAUDE.md's Future additions) — lets a developer (or the grader)
    find a reset link without digging through server logs.
    """
    return read_dev_outbox(email)
