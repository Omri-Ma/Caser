from conftest import auth_for, make_identity, make_membership, make_tenant
from shared.models.enums import UserRole


def test_admin_login_records_last_login_at(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    assert manager.last_login_at is None

    resp = admin_client.post(
        "/auth/login",
        json={"email": "manager@acme.com", "password": "password123"},
        headers={"Host": "acme.lvh.me"},
    )

    assert resp.status_code == 200
    db.refresh(manager)
    assert manager.last_login_at is not None


def test_admin_lobby_login_records_last_login_at(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)

    resp = admin_client.post(
        "/auth/lobby-login",
        json={"email": "manager@acme.com", "password": "password123"},
        headers={"Host": "www.lvh.me"},
    )

    assert resp.status_code == 200
    db.refresh(manager)
    assert manager.last_login_at is not None


def test_platform_login_records_last_login_at(admin_client, db):
    super_admin = make_identity(db, "root@caser.com", is_super_admin=True)

    resp = admin_client.post(
        "/auth/platform-login",
        json={"email": "root@caser.com", "password": "password123"},
        headers={"Host": "platform.lvh.me"},
    )

    assert resp.status_code == 200
    db.refresh(super_admin)
    assert super_admin.last_login_at is not None


def test_client_login_records_last_login_at(client_client, db):
    tenant = make_tenant(db, "acme")
    lawyer = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer.id, tenant.id, UserRole.LAWYER)

    resp = client_client.post(
        "/auth/login",
        json={"email": "lawyer@acme.com", "password": "password123"},
        headers={"Host": "acme.lvh.me"},
    )

    assert resp.status_code == 200
    db.refresh(lawyer)
    assert lawyer.last_login_at is not None


def test_failed_login_does_not_record_last_login_at(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)

    resp = admin_client.post(
        "/auth/login",
        json={"email": "manager@acme.com", "password": "wrong-password"},
        headers={"Host": "acme.lvh.me"},
    )

    assert resp.status_code == 401
    db.refresh(manager)
    assert manager.last_login_at is None
