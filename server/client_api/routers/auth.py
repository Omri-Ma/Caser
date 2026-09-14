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
    UpdateProfileRequest,
)
from shared.database import get_db
from shared.dev_outbox import read_dev_outbox, write_dev_outbox
from shared.identity import get_current_identity, record_login
from shared.membership import get_current_membership
from shared.models import AuditLog, Identity, Membership, MembershipInvite, Tenant
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


def _lawyer_client_tenants(identity: Identity, db: Session):
    """Every active lawyer/client Membership this identity holds, at active
    tenants — shared by /auth/lobby-login (unauthenticated) and
    /auth/my-tenants below (already-authenticated, used by the multi-firm
    switcher and the no-access redirect check) so both resolve "which
    firms does this person work with" identically.
    """
    return (
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


@router.post("/register", response_model=IdentityResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    """Create a bare global account. Used two ways: a lawyer/client
    registering with no invite yet (an office manager attaches them to a
    firm afterward), or someone following an invite link for an email with
    no Identity yet. In the second case, registering does *not* by itself
    accept any pending invite for this email (CLAUDE.md's MembershipInvites
    note, reversed from an earlier draft) — creating an account and
    agreeing to join a specific firm are two separate, deliberate acts.
    After a successful registration the frontend lands on the same explicit
    accept/decline screen an already-registered invitee sees (GET /invites
    + POST /invites/{id}/accept|decline, both already tenant-agnostic and
    now reachable immediately since this route logs the new identity in).
    """
    if db.query(Identity).filter(Identity.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.EMAIL_ALREADY_REGISTERED)

    identity = Identity(name=payload.name, email=payload.email, password_hash=hash_password(payload.password))
    db.add(identity)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.EMAIL_ALREADY_REGISTERED)
    db.refresh(identity)

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
    if membership.role not in (UserRole.LAWYER, UserRole.CLIENT):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=E.account_logs_in_through_other_portal("פורטל הניהול"),
        )

    record_login(identity, db)
    set_session_cookies(response, identity.id, identity.token_version)
    return SessionResponse(name=identity.name, email=identity.email, role=membership.role, is_manager=membership.is_manager)


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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=E.INVALID_EMAIL_OR_PASSWORD)

    memberships = _lawyer_client_tenants(identity, db)
    pending_invites = (
        db.query(MembershipInvite, Tenant)
        .join(Tenant, MembershipInvite.tenant_id == Tenant.id)
        .filter(MembershipInvite.email == identity.email, MembershipInvite.status == InviteStatus.PENDING)
        .all()
    )

    if not memberships and not pending_invites:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=E.NO_LAWYER_OR_CLIENT_ACCOUNT_FOUND,
        )

    record_login(identity, db)
    set_session_cookies(response, identity.id, identity.token_version)
    return LobbyLoginResponse(
        name=identity.name,
        email=identity.email,
        tenants=[
            LobbyTenantOption(
                tenant_id=tenant.id,
                subdomain=tenant.subdomain,
                firm_name=tenant.name,
                role=membership.role,
                is_manager=membership.is_manager,
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


@router.get("/my-tenants", response_model=list[LobbyTenantOption])
def my_tenants(identity: Identity = Depends(get_current_identity), db: Session = Depends(get_db)):
    """Every other active firm this identity works with, as a lawyer or
    client — backs the multi-firm switcher in the authenticated app shell
    (CLAUDE.md: one person can hold a lawyer/client membership at more than
    one firm). Tenant-agnostic on purpose, same shape as admin_api's own
    /auth/my-tenants.
    """
    memberships = _lawyer_client_tenants(identity, db)
    return [
        LobbyTenantOption(
            tenant_id=tenant.id,
            subdomain=tenant.subdomain,
            firm_name=tenant.name,
            role=membership.role,
            is_manager=membership.is_manager,
        )
        for membership, tenant in memberships
    ]


@router.get("/my-membership", status_code=status.HTTP_204_NO_CONTENT)
def my_membership(_membership: Membership = Depends(get_current_membership)):
    """A cheap "do I actually have access at this subdomain" check — reuses
    the exact same get_current_membership dependency every tenant-scoped
    client_api route already depends on, just with no role restriction.
    204 means yes; the dependency itself raises 403 (E.NO_ACCESS_TO_FIRM)
    otherwise. AppShell calls this once on mount to send a lawyer/client
    with no access at this subdomain to the general homepage instead of
    rendering a shell whose every real data call would 403 individually
    (CLAUDE.md's "Landing somewhere you have no access" redirect rule).
    """
    return None


@router.post("/leave-firm", status_code=status.HTTP_204_NO_CONTENT)
def leave_firm(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    membership: Membership = Depends(get_current_membership),
):
    """Self-service "leave this firm" for the lawyer/client whose session
    this is — deactivates their own membership at the current tenant
    subdomain (CLAUDE.md's Memberships note). Unlike the office_manager role
    (see admin_api's own /auth/leave-firm), there's no "last one standing"
    concern here at all: a lawyer/client leaving never strands a firm's own
    administrative capacity the way removing its last office_manager could.
    """
    membership.active = False
    db.add(
        AuditLog(
            tenant_id=tenant.id,
            user_id=membership.id,
            action="member_left_firm",
            target=f"membership:{membership.id}",
        )
    )
    db.commit()


@router.patch("/profile", response_model=IdentityResponse)
def update_my_profile(
    payload: UpdateProfileRequest,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """Self-service only — bio/photo_url/years_of_experience are global to
    the person, never a lever another party (an office_manager, CLAUDE.md's
    authority boundary) gets to pull. Whether any of it is actually shown
    publicly is the separate per-membership show_on_public_page toggle.
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.CURRENT_PASSWORD_INCORRECT)

    set_session_cookies(response, identity.id, identity.token_version)


@router.post("/forgot-password", response_model=GenericMessageResponse)
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """Always the same generic response regardless of whether the email
    matched a real account (CLAUDE.md's PasswordResetTokens note — never
    reveal which emails are registered). See admin_api's identical route.
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
    """Dev-only stand-in for real email delivery — see forgot_password above."""
    return read_dev_outbox(email)
