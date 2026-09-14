"""client_api's GET /auth/my-tenants — the lawyer/client-side counterpart to
admin_api's own /auth/my-tenants, backing the multi-firm switcher dropdown
(CLAUDE.md's Identity vs. membership: one person can hold a lawyer/client
membership at more than one firm).
"""

from conftest import auth_for, make_identity, make_membership, make_tenant
from shared.models.enums import UserRole


def test_my_tenants_returns_lawyer_and_client_memberships_with_role(client_client, db):
    tenant_a = make_tenant(db, "acme", name="Acme Law")
    tenant_b = make_tenant(db, "globex", name="Globex Legal")
    identity = make_identity(db, "person@example.com")
    make_membership(db, identity.id, tenant_a.id, UserRole.LAWYER)
    make_membership(db, identity.id, tenant_b.id, UserRole.CLIENT)

    headers, cookies = auth_for(identity, "acme")
    resp = client_client.get("/auth/my-tenants", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    by_subdomain = {t["subdomain"]: t["role"] for t in resp.json()}
    assert by_subdomain == {"acme": "lawyer", "globex": "client"}


def test_my_tenants_excludes_office_manager_membership(client_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)

    headers, cookies = auth_for(manager, "acme")
    resp = client_client.get("/auth/my-tenants", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    assert resp.json() == []


def test_my_tenants_excludes_inactive_membership_and_suspended_tenant(client_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex", active=False)
    identity = make_identity(db, "person@example.com")
    membership_a = make_membership(db, identity.id, tenant_a.id, UserRole.LAWYER)
    membership_a.active = False
    make_membership(db, identity.id, tenant_b.id, UserRole.CLIENT)
    db.commit()

    headers, cookies = auth_for(identity, "acme")
    resp = client_client.get("/auth/my-tenants", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    assert resp.json() == []


def test_my_tenants_requires_login(client_client, db):
    resp = client_client.get("/auth/my-tenants", headers={"Host": "acme.lvh.me"})
    assert resp.status_code == 401
