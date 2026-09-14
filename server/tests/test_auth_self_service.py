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


def test_update_my_profile(client_client, db):
    identity = make_identity(db, "lawyer@acme.com")
    tenant = make_tenant(db, "acme")
    make_membership(db, identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(identity, "acme")

    resp = client_client.patch(
        "/auth/profile",
        json={"bio": "Ten years of litigation experience.", "photo_url": "https://example.com/me.jpg", "years_of_experience": 10},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["bio"] == "Ten years of litigation experience."
    assert body["photo_url"] == "https://example.com/me.jpg"
    assert body["years_of_experience"] == 10


def test_admin_api_exposes_the_same_profile_route(admin_client, db):
    identity = make_identity(db, "manager@acme.com")
    tenant = make_tenant(db, "acme")
    make_membership(db, identity.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(identity, "acme")

    resp = admin_client.patch(
        "/auth/profile",
        json={"bio": "Managing partner.", "photo_url": None, "years_of_experience": 15},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 200
    assert resp.json()["years_of_experience"] == 15


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


def test_second_forgot_password_request_invalidates_the_first_token(client_client, db):
    """A new "forgot password" request supersedes any earlier outstanding
    one - only the newest link is ever valid, so requesting twice (e.g. the
    first email felt lost) can't leave two independently-redeemable links
    outstanding.
    """
    make_identity(db, "real@acme.com")

    client_client.post("/auth/forgot-password", json={"email": "real@acme.com"})
    first_outbox = client_client.get("/auth/dev-outbox", params={"email": "real@acme.com"}).json()
    first_token = first_outbox[0]["link"].split("token=")[1]

    client_client.post("/auth/forgot-password", json={"email": "real@acme.com"})
    second_outbox = client_client.get("/auth/dev-outbox", params={"email": "real@acme.com"}).json()
    # read_dev_outbox returns newest-first, so index 0 is the just-written one.
    second_token = second_outbox[0]["link"].split("token=")[1]

    assert first_token != second_token

    # The first (now-superseded) token no longer redeems...
    stale_resp = client_client.post(
        "/auth/reset-password", json={"token": first_token, "new_password": "StalePass1234"}
    )
    assert stale_resp.status_code == 400

    # ...but the second (newest) one still does.
    fresh_resp = client_client.post(
        "/auth/reset-password", json={"token": second_token, "new_password": "FreshPass1234"}
    )
    assert fresh_resp.status_code == 200


def test_two_pending_tokens_only_the_newest_counted_used_once(client_client, db):
    """Direct check on the actual row state, not just behavior through the
    API: requesting twice marks the earlier row used_at (not deleted) and
    leaves exactly one still-genuinely-pending row.
    """
    make_identity(db, "real@acme.com")

    client_client.post("/auth/forgot-password", json={"email": "real@acme.com"})
    client_client.post("/auth/forgot-password", json={"email": "real@acme.com"})

    tokens = db.query(PasswordResetToken).order_by(PasswordResetToken.id).all()
    assert len(tokens) == 2
    assert tokens[0].used_at is not None  # superseded, not deleted
    assert tokens[1].used_at is None  # the current, genuinely pending one


def test_super_admin_is_excluded_from_forgot_password(admin_client, db):
    """CLAUDE.md's Multi-tenancy architecture: super_admin is manually
    -provisioned and excluded from self-service reset entirely - the
    generic response is unchanged (never reveal *why* it "didn't work"),
    but no token/outbox entry is actually created.
    """
    make_identity(db, "root@platform.internal", is_super_admin=True)

    resp = admin_client.post("/auth/forgot-password", json={"email": "root@platform.internal"})

    assert resp.status_code == 200
    assert db.query(PasswordResetToken).count() == 0
    outbox = admin_client.get("/auth/dev-outbox", params={"email": "root@platform.internal"}).json()
    assert outbox == []


def test_super_admin_excluded_from_forgot_password_on_client_api_too(client_client, db):
    make_identity(db, "root@platform.internal", is_super_admin=True)

    resp = client_client.post("/auth/forgot-password", json={"email": "root@platform.internal"})

    assert resp.status_code == 200
    assert db.query(PasswordResetToken).count() == 0


def test_concurrent_forgot_password_requests_still_leave_only_one_valid_token(db):
    """Regression test for a real race: two nearly-simultaneous requests
    (a double-click, two open tabs) each used to read "no unused tokens
    yet" before either had committed its INSERT, leaving both new tokens
    simultaneously valid. The two sequential tests above (same behavior,
    called one after another) don't exercise this — they never overlap in
    time, so they passed even with the race present. This test drives two
    real, independent DB sessions from separate threads so their
    transactions genuinely overlap, the same way two browser tabs would.
    """
    import threading

    from tests.conftest import TestingSessionLocal
    from shared.password_reset import create_reset_token

    identity = make_identity(db, "concurrent@acme.com")
    identity_id = identity.id
    db.commit()

    barrier = threading.Barrier(5)
    errors = []

    def worker():
        session = TestingSessionLocal()
        try:
            barrier.wait(timeout=5)  # maximize actual overlap between threads
            create_reset_token(identity_id, session)
        except Exception as exc:  # pragma: no cover - surfaced via `errors`
            errors.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors, errors

    db.expire_all()
    tokens = db.query(PasswordResetToken).filter(PasswordResetToken.identity_id == identity_id).all()
    assert len(tokens) == 5
    unused = [t for t in tokens if t.used_at is None]
    # Exactly one survivor — every concurrent request must still see (and
    # invalidate) every token issued before it, even though each one had to
    # wait on the identity-row lock to get there.
    assert len(unused) == 1
