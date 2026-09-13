"""Self-service password change and the real forgot-password flow —
CLAUDE.md's office_manager authority boundary (password is never another
party's lever) and its PasswordResetTokens spec. Exercised against both
admin_api and client_api since shared/password_reset.py backs identical
routes in each.
"""
from shared.models import PasswordResetToken

from tests.conftest import auth_for, make_identity, make_membership, make_tenant
from shared.models.enums import UserRole


def test_change_password_requires_correct_current_password(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.post(
        "/auth/change-password",
        json={"current_password": "wrong-password", "new_password": "BrandNewPass123"},
        headers=headers,
        cookies=cookies,
    )
    # 400, not 401 — a wrong current-password value is a form error on an
    # already-authenticated request, not a session/auth failure. A 401 here
    # collides with the frontend's generic 401-means-"session expired"
    # handling and silently redirects to login instead of showing an error.
    assert resp.status_code == 400


def test_change_password_succeeds_and_invalidates_other_sessions(client_client, db):
    tenant = make_tenant(db, "acme")
    lawyer = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer.id, tenant.id, UserRole.LAWYER)
    old_headers, old_cookies = auth_for(lawyer, "acme")  # a second, older session

    resp = client_client.post(
        "/auth/change-password",
        json={"current_password": "password123", "new_password": "BrandNewPass123"},
        headers=old_headers,
        cookies=old_cookies,
    )
    assert resp.status_code == 204

    # Old password no longer works.
    login_resp = client_client.post(
        "/auth/login",
        json={"email": "lawyer@acme.com", "password": "password123"},
        headers={"Host": "acme.lvh.me"},
    )
    assert login_resp.status_code == 401

    # New password works.
    login_resp = client_client.post(
        "/auth/login",
        json={"email": "lawyer@acme.com", "password": "BrandNewPass123"},
        headers={"Host": "acme.lvh.me"},
    )
    assert login_resp.status_code == 200

    # A session token minted before the change (old_cookies) is now invalid —
    # token_version was bumped, so it fails the identity resolution check.
    me_resp = client_client.get("/auth/me", headers=old_headers, cookies=old_cookies)
    assert me_resp.status_code == 401


def test_forgot_password_always_returns_generic_response(client_client, db):
    make_identity(db, "real@acme.com")

    real_resp = client_client.post("/auth/forgot-password", json={"email": "real@acme.com"})
    fake_resp = client_client.post("/auth/forgot-password", json={"email": "nobody@nowhere.com"})

    assert real_resp.status_code == 200
    assert fake_resp.status_code == 200
    assert real_resp.json() == fake_resp.json()


def test_forgot_password_writes_a_token_and_dev_outbox_entry_only_for_real_email(client_client, db):
    identity = make_identity(db, "real@acme.com")

    client_client.post(
        "/auth/forgot-password",
        json={"email": "real@acme.com"},
        headers={"Origin": "http://www.lvh.me:5173"},
    )
    client_client.post("/auth/forgot-password", json={"email": "nobody@nowhere.com"})

    tokens = db.query(PasswordResetToken).all()
    assert len(tokens) == 1
    assert tokens[0].identity_id == identity.id

    outbox = client_client.get("/auth/dev-outbox", params={"email": "real@acme.com"}).json()
    assert len(outbox) == 1
    assert "reset-password?token=" in outbox[0]["link"]
    assert outbox[0]["link"].startswith("http://www.lvh.me:5173")

    outbox_fake = client_client.get("/auth/dev-outbox", params={"email": "nobody@nowhere.com"}).json()
    assert outbox_fake == []


def test_reset_password_with_valid_token_updates_password_and_invalidates_sessions(client_client, db):
    identity = make_identity(db, "real@acme.com")
    tenant = make_tenant(db, "acme")
    make_membership(db, identity.id, tenant.id, UserRole.CLIENT)
    old_headers, old_cookies = auth_for(identity, "acme")

    client_client.post("/auth/forgot-password", json={"email": "real@acme.com"})
    outbox = client_client.get("/auth/dev-outbox", params={"email": "real@acme.com"}).json()
    token = outbox[0]["link"].split("token=")[1]

    resp = client_client.post("/auth/reset-password", json={"token": token, "new_password": "BrandNewPass123"})
    assert resp.status_code == 200

    login_resp = client_client.post(
        "/auth/login",
        json={"email": "real@acme.com", "password": "BrandNewPass123"},
        headers={"Host": "acme.lvh.me"},
    )
    assert login_resp.status_code == 200

    me_resp = client_client.get("/auth/me", headers=old_headers, cookies=old_cookies)
    assert me_resp.status_code == 401


def test_reset_password_token_is_single_use(client_client, db):
    make_identity(db, "real@acme.com")
    client_client.post("/auth/forgot-password", json={"email": "real@acme.com"})
    outbox = client_client.get("/auth/dev-outbox", params={"email": "real@acme.com"}).json()
    token = outbox[0]["link"].split("token=")[1]

    first = client_client.post("/auth/reset-password", json={"token": token, "new_password": "FirstPass1234"})
    assert first.status_code == 200

    second = client_client.post("/auth/reset-password", json={"token": token, "new_password": "SecondPass1234"})
    assert second.status_code == 400


def test_reset_password_rejects_unknown_token(client_client, db):
    resp = client_client.post("/auth/reset-password", json={"token": "not-a-real-token", "new_password": "BrandNewPass123"})
    assert resp.status_code == 400


def test_admin_api_exposes_the_same_self_service_routes(admin_client, db):
    """Confirms admin_api has its own thin routes on top of the same shared
    logic — not client_api-only.
    """
    identity = make_identity(db, "manager@acme.com")

    resp = admin_client.post("/auth/forgot-password", json={"email": "manager@acme.com"})
    assert resp.status_code == 200

    outbox = admin_client.get("/auth/dev-outbox", params={"email": "manager@acme.com"}).json()
    assert len(outbox) == 1
    token = outbox[0]["link"].split("token=")[1]

    reset_resp = admin_client.post("/auth/reset-password", json={"token": token, "new_password": "BrandNewPass123"})
    assert reset_resp.status_code == 200
