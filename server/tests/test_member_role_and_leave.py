"""CLAUDE.md's Memberships note: a firm has exactly one office_manager,
fixed at founding, never more — there is no promote/demote path between
office_manager and lawyer at all. Self-service firm-leaving is safe for
lawyer/client, but the sole office_manager can never leave/deactivate their
own membership; that's a hard block, not a discouraged-but-allowed edge case.
"""

from conftest import auth_for, make_identity, make_membership, make_tenant
from shared.models.enums import UserRole


# --- POST /auth/leave-firm ---


def test_office_manager_cannot_leave_firm(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    membership = make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.post("/auth/leave-firm", headers=headers, cookies=cookies)

    assert resp.status_code == 400
    db.refresh(membership)
    assert membership.active is True


def test_lawyer_can_leave_firm_via_client_api(client_client, db):
    tenant = make_tenant(db, "acme")
    lawyer = make_identity(db, "lawyer@acme.com")
    membership = make_membership(db, lawyer.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(lawyer, "acme")

    resp = client_client.post("/auth/leave-firm", headers=headers, cookies=cookies)

    assert resp.status_code == 204
    db.refresh(membership)
    assert membership.active is False


def test_client_can_leave_firm_via_client_api(client_client, db):
    tenant = make_tenant(db, "acme")
    client_identity = make_identity(db, "client@acme.com")
    membership = make_membership(db, client_identity.id, tenant.id, UserRole.CLIENT)
    headers, cookies = auth_for(client_identity, "acme")

    resp = client_client.post("/auth/leave-firm", headers=headers, cookies=cookies)

    assert resp.status_code == 204
    db.refresh(membership)
    assert membership.active is False


def test_leave_firm_requires_membership_here(admin_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "globex")

    resp = admin_client.post("/auth/leave-firm", headers=headers, cookies=cookies)

    assert resp.status_code == 403


# --- PATCH /members/{id}/role no longer exists ---


def test_role_route_removed(admin_client, db):
    """The promote/demote-to-office_manager route was removed entirely
    (CLAUDE.md reversal) — confirm it's gone, not just blocked.
    """
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.patch(
        f"/members/{lawyer_membership.id}/role", json={"role": "office_manager"}, headers=headers, cookies=cookies
    )

    assert resp.status_code == 404
