from conftest import auth_for, make_identity, make_membership, make_tenant
from shared.models.enums import UserRole


def test_list_members_returns_lawyers_and_clients(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    lawyer_identity = make_identity(db, "lawyer@acme.com", name="Lawyer One")
    make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    client_identity = make_identity(db, "client@acme.com", name="Client One")
    make_membership(db, client_identity.id, tenant.id, UserRole.CLIENT)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.get("/members", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    emails = {m["identity_email"] for m in body["items"]}
    assert emails == {"manager@acme.com", "lawyer@acme.com", "client@acme.com"}


def test_list_members_filters_by_role(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    lawyer_identity = make_identity(db, "lawyer@acme.com", name="Lawyer One")
    make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    client_identity = make_identity(db, "client@acme.com", name="Client One")
    make_membership(db, client_identity.id, tenant.id, UserRole.CLIENT)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.get("/members", params={"role": "lawyer"}, headers=headers, cookies=cookies)

    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["identity_email"] == "lawyer@acme.com"


def test_list_members_excludes_inactive(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    inactive_membership = make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    inactive_membership.active = False
    db.commit()
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.get("/members", params={"role": "lawyer"}, headers=headers, cookies=cookies)

    assert resp.json()["total"] == 0


def test_lawyer_cannot_list_members(admin_client, db):
    tenant = make_tenant(db, "acme")
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = admin_client.get("/members", headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_list_members_is_tenant_isolated(admin_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    manager_a = make_identity(db, "manager@acme.com")
    make_membership(db, manager_a.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    other_lawyer = make_identity(db, "lawyer@globex.com")
    make_membership(db, other_lawyer.id, tenant_b.id, UserRole.LAWYER)
    headers, cookies = auth_for(manager_a, "acme")

    resp = admin_client.get("/members", headers=headers, cookies=cookies)

    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["identity_email"] == "manager@acme.com"


def test_deactivate_member_excludes_from_default_list(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.post(f"/members/{lawyer_membership.id}/deactivate", headers=headers, cookies=cookies)
    assert resp.status_code == 200
    assert resp.json()["active"] is False

    listed = admin_client.get("/members", headers=headers, cookies=cookies).json()
    assert listed["total"] == 1  # just the manager

    listed_all = admin_client.get("/members", params={"include_inactive": "true"}, headers=headers, cookies=cookies).json()
    assert listed_all["total"] == 2


def test_office_manager_cannot_deactivate_self(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    manager_membership = make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.post(f"/members/{manager_membership.id}/deactivate", headers=headers, cookies=cookies)

    assert resp.status_code == 400


def test_deactivated_member_loses_access(admin_client, client_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(manager, "acme")
    admin_client.post(f"/members/{lawyer_membership.id}/deactivate", headers=headers, cookies=cookies)

    lawyer_headers, lawyer_cookies = auth_for(lawyer_identity, "acme")
    resp = client_client.get("/cases", headers=lawyer_headers, cookies=lawyer_cookies)

    assert resp.status_code == 403


def test_readding_deactivated_member_reactivates_existing_row(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(manager, "acme")
    admin_client.post(f"/members/{lawyer_membership.id}/deactivate", headers=headers, cookies=cookies)

    resp = admin_client.post(
        "/members", json={"email": "lawyer@acme.com", "role": "client"}, headers=headers, cookies=cookies
    )

    assert resp.status_code == 201
    assert resp.json()["id"] == lawyer_membership.id  # same row reactivated, not a new insert
    assert resp.json()["role"] == "client"

    listed = admin_client.get("/members", headers=headers, cookies=cookies).json()
    assert listed["total"] == 2


def test_add_member_rejects_lawyer_over_plan_limit(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    # Free plan's hardcoded limit is 3 lawyers (shared/plan_limits.py).
    for i in range(3):
        identity = make_identity(db, f"lawyer{i}@acme.com")
        admin_client.post("/members", json={"email": identity.email, "role": "lawyer"}, headers=headers, cookies=cookies)

    fourth = make_identity(db, "lawyer4@acme.com")
    resp = admin_client.post("/members", json={"email": fourth.email, "role": "lawyer"}, headers=headers, cookies=cookies)

    assert resp.status_code == 400


def test_reset_member_password_lets_them_log_in_with_new_password(admin_client, client_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.post(
        f"/members/{lawyer_membership.id}/reset-password",
        json={"new_password": "BrandNewPass123"},
        headers=headers,
        cookies=cookies,
    )
    assert resp.status_code == 204

    login_resp = client_client.post(
        "/auth/login",
        json={"email": "lawyer@acme.com", "password": "BrandNewPass123"},
        headers={"Host": "acme.lvh.me"},
    )
    assert login_resp.status_code == 200

    old_password_resp = client_client.post(
        "/auth/login",
        json={"email": "lawyer@acme.com", "password": "password123"},
        headers={"Host": "acme.lvh.me"},
    )
    assert old_password_resp.status_code == 401
