"""CLAUDE.md's "Landing somewhere you have no access" redirect rule — the
backend-side lookups the frontend uses to decide where to actually send a
logged-in identity that hits a subdomain it has no membership at:
admin_api's GET /auth/my-tenants (office_manager's own firms) and
client_api's GET /auth/my-membership (a cheap yes/no access check).
"""

from conftest import auth_for, make_identity, make_membership, make_tenant
from shared.models.enums import UserRole


# --- admin_api: GET /auth/my-tenants ---


def test_my_tenants_returns_own_office_manager_firms(admin_client, db):
    tenant_a = make_tenant(db, "acme", name="Acme Law")
    tenant_b = make_tenant(db, "globex", name="Globex Legal")
    other_tenant = make_tenant(db, "other", name="Other Firm")
    manager = make_identity(db, "manager@shared.com")
    make_membership(db, manager.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    make_membership(db, manager.id, tenant_b.id, UserRole.OFFICE_MANAGER)

    # Logged in on a subdomain they have no membership at at all.
    headers, cookies = auth_for(manager, "other")
    resp = admin_client.get("/auth/my-tenants", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    subdomains = {t["subdomain"] for t in resp.json()}
    assert subdomains == {"acme", "globex"}
    assert "other" not in subdomains


def test_my_tenants_excludes_lawyer_only_membership(admin_client, db):
    tenant = make_tenant(db, "acme")
    lawyer = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer.id, tenant.id, UserRole.LAWYER)

    headers, cookies = auth_for(lawyer, "acme")
    resp = admin_client.get("/auth/my-tenants", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    assert resp.json() == []


def test_my_tenants_requires_login(admin_client, db):
    resp = admin_client.get("/auth/my-tenants", headers={"Host": "acme.lvh.me"})
    assert resp.status_code == 401


# --- client_api: GET /auth/my-membership ---


def test_my_membership_204_when_member_of_this_tenant(client_client, db):
    tenant = make_tenant(db, "acme")
    lawyer = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer.id, tenant.id, UserRole.LAWYER)

    headers, cookies = auth_for(lawyer, "acme")
    resp = client_client.get("/auth/my-membership", headers=headers, cookies=cookies)

    assert resp.status_code == 204


def test_my_membership_403_when_no_membership_at_this_tenant(client_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    lawyer = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer.id, tenant_a.id, UserRole.LAWYER)

    # Logged in, but on a *different* tenant's subdomain.
    headers, cookies = auth_for(lawyer, "globex")
    resp = client_client.get("/auth/my-membership", headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_my_membership_403_when_membership_deactivated(client_client, db):
    tenant = make_tenant(db, "acme")
    client_identity = make_identity(db, "client@acme.com")
    membership = make_membership(db, client_identity.id, tenant.id, UserRole.CLIENT)
    membership.active = False
    db.commit()

    headers, cookies = auth_for(client_identity, "acme")
    resp = client_client.get("/auth/my-membership", headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_my_membership_403_for_office_manager_at_own_firm(client_client, db):
    """A real bug this route used to have: an office_manager visiting their
    OWN firm's client/ subdomain has a genuine active Membership row there
    (just the wrong role for this app) — used to pass this check, landing
    them on a blank/no-data client/ shell instead of being redirected as a
    real no-access case (CLAUDE.md: office_manager never uses client/).
    """
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)

    headers, cookies = auth_for(manager, "acme")
    resp = client_client.get("/auth/my-membership", headers=headers, cookies=cookies)

    assert resp.status_code == 403
