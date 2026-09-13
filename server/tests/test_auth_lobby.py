"""Lobby login (www.<BASE_DOMAIN>) — CLAUDE.md's Multi-tenancy architecture.
No subdomain is known yet, so /auth/lobby-login resolves every matching
active Membership for the identity instead of checking one tenant, and the
frontend redirects (one match), shows a picker (more than one), or shows a
clear error (zero) based on how many come back.
"""

from conftest import make_identity, make_membership, make_tenant
from shared.models.enums import UserRole


# --- admin_api: office_manager only ---


def test_admin_lobby_login_wrong_password(admin_client, db):
    make_identity(db, "manager@acme.com")

    resp = admin_client.post(
        "/auth/lobby-login",
        json={"email": "manager@acme.com", "password": "wrong-password"},
    )

    assert resp.status_code == 401


def test_admin_lobby_login_unknown_email(admin_client, db):
    resp = admin_client.post(
        "/auth/lobby-login",
        json={"email": "nobody@example.com", "password": "password123"},
    )

    assert resp.status_code == 401


def test_admin_lobby_login_zero_matches_for_lawyer_only_identity(admin_client, db):
    """A lawyer with no office_manager membership anywhere gets a clear 403,
    not silently logged in — this is the "lawyer landing on admin/'s lobby by
    mistake" case CLAUDE.md calls out.
    """
    tenant = make_tenant(db, "acme")
    lawyer = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer.id, tenant.id, UserRole.LAWYER)

    resp = admin_client.post(
        "/auth/lobby-login",
        json={"email": "lawyer@acme.com", "password": "password123"},
    )

    assert resp.status_code == 403


def test_admin_lobby_login_single_match_redirects(admin_client, db):
    tenant = make_tenant(db, "acme", name="Acme Law")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)

    resp = admin_client.post(
        "/auth/lobby-login",
        json={"email": "manager@acme.com", "password": "password123"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["tenants"]) == 1
    assert body["tenants"][0]["subdomain"] == "acme"
    assert body["tenants"][0]["firm_name"] == "Acme Law"
    # The session cookie is set on a successful lobby login the same as any
    # other login — this is what makes the frontend's follow-up hard
    # redirect to the tenant subdomain work with no second login. Checked
    # via the raw Set-Cookie header, not resp.cookies: the cookie is scoped
    # to COOKIE_DOMAIN (.lvh.me), which the test client's "testserver" host
    # doesn't match, so httpx's cookie jar wouldn't store it either way.
    set_cookie_headers = resp.headers.get_list("set-cookie")
    assert any("caser_access=" in header for header in set_cookie_headers)


def test_admin_lobby_login_multiple_matches_returns_all_for_picker(admin_client, db):
    tenant_a = make_tenant(db, "acme", name="Acme Law")
    tenant_b = make_tenant(db, "globex", name="Globex Legal")
    manager = make_identity(db, "manager@shared.com")
    make_membership(db, manager.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    make_membership(db, manager.id, tenant_b.id, UserRole.OFFICE_MANAGER)

    resp = admin_client.post(
        "/auth/lobby-login",
        json={"email": "manager@shared.com", "password": "password123"},
    )

    assert resp.status_code == 200
    subdomains = {t["subdomain"] for t in resp.json()["tenants"]}
    assert subdomains == {"acme", "globex"}


def test_admin_lobby_login_excludes_inactive_membership(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    membership = make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    membership.active = False
    db.commit()

    resp = admin_client.post(
        "/auth/lobby-login",
        json={"email": "manager@acme.com", "password": "password123"},
    )

    assert resp.status_code == 403


def test_admin_lobby_login_excludes_suspended_tenant(admin_client, db):
    """A suspended tenant (Tenants.active = False) is a full lockout for
    everyone at that firm, including its own office_manager — lobby login
    must not offer it as a destination.
    """
    tenant = make_tenant(db, "acme", active=False)
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)

    resp = admin_client.post(
        "/auth/lobby-login",
        json={"email": "manager@acme.com", "password": "password123"},
    )

    assert resp.status_code == 403


# --- client_api: lawyer/client only ---


def test_client_lobby_login_zero_matches_for_office_manager_only_identity(client_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)

    resp = client_client.post(
        "/auth/lobby-login",
        json={"email": "manager@acme.com", "password": "password123"},
    )

    assert resp.status_code == 403


def test_client_lobby_login_single_match_includes_role(client_client, db):
    tenant = make_tenant(db, "acme", name="Acme Law")
    lawyer = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer.id, tenant.id, UserRole.LAWYER)

    resp = client_client.post(
        "/auth/lobby-login",
        json={"email": "lawyer@acme.com", "password": "password123"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["tenants"]) == 1
    assert body["tenants"][0]["subdomain"] == "acme"
    # role travels in the response since client/'s nav differs by role and
    # the redirect lands on a different origin that can't read it any other
    # way (see client/src/App.jsx's role-param bootstrap).
    assert body["tenants"][0]["role"] == "lawyer"


def test_client_lobby_login_multiple_matches_mixes_lawyer_and_client_roles(client_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    identity = make_identity(db, "person@example.com")
    make_membership(db, identity.id, tenant_a.id, UserRole.LAWYER)
    make_membership(db, identity.id, tenant_b.id, UserRole.CLIENT)

    resp = client_client.post(
        "/auth/lobby-login",
        json={"email": "person@example.com", "password": "password123"},
    )

    assert resp.status_code == 200
    roles_by_subdomain = {t["subdomain"]: t["role"] for t in resp.json()["tenants"]}
    assert roles_by_subdomain == {"acme": "lawyer", "globex": "client"}


def test_client_lobby_login_wrong_password(client_client, db):
    tenant = make_tenant(db, "acme")
    client_identity = make_identity(db, "client@acme.com")
    make_membership(db, client_identity.id, tenant.id, UserRole.CLIENT)

    resp = client_client.post(
        "/auth/lobby-login",
        json={"email": "client@acme.com", "password": "wrong-password"},
    )

    assert resp.status_code == 401
