from conftest import auth_for, make_identity, make_membership, make_tenant
from shared.models.enums import UserRole


def test_get_tenant_returns_branding_fields(admin_client, db):
    tenant = make_tenant(db, "acme", name="Acme Law")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.get("/tenant", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Acme Law"
    assert body["subdomain"] == "acme"


def test_update_tenant_branding(admin_client, db):
    tenant = make_tenant(db, "acme", name="Acme Law")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.patch(
        "/tenant",
        json={"name": "Acme & Partners", "logo_url": "https://example.com/logo.png", "primary_color": "#112233"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Acme & Partners"
    assert body["logo_url"] == "https://example.com/logo.png"
    assert body["primary_color"] == "#112233"


def test_update_tenant_rejects_invalid_color(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.patch(
        "/tenant",
        json={"name": "Acme Law", "primary_color": "blue"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 422


def test_lawyer_cannot_update_tenant_branding(admin_client, db):
    tenant = make_tenant(db, "acme")
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = admin_client.patch("/tenant", json={"name": "Hijacked"}, headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_tenant_branding_is_tenant_isolated(admin_client, db):
    tenant_a = make_tenant(db, "acme", name="Acme Law")
    make_tenant(db, "globex", name="Globex Legal")
    manager_a = make_identity(db, "manager@acme.com")
    make_membership(db, manager_a.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager_a, "acme")

    resp = admin_client.get("/tenant", headers=headers, cookies=cookies)

    assert resp.json()["name"] == "Acme Law"
