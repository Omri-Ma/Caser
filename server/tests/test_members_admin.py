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
