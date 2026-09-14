"""CLAUDE.md's Memberships note: office_manager can promote a lawyer to
office_manager or demote an office_manager back to lawyer (never client in
or out of this), and self-service firm-leaving is safe for every role
(including a firm's only office_manager) because promote/demote is the
escape hatch that makes stranding a non-issue.
"""

from conftest import auth_for, make_identity, make_membership, make_tenant
from shared.models import Membership
from shared.models.enums import UserRole


# --- PATCH /members/{id}/role (admin_api) ---


def test_promote_lawyer_to_office_manager(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.patch(
        f"/members/{lawyer_membership.id}/role", json={"role": "office_manager"}, headers=headers, cookies=cookies
    )

    assert resp.status_code == 200
    assert resp.json()["role"] == "office_manager"
    db.refresh(lawyer_membership)
    assert lawyer_membership.role == UserRole.OFFICE_MANAGER


def test_demote_office_manager_to_lawyer(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    other_identity = make_identity(db, "other@acme.com")
    other_membership = make_membership(db, other_identity.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.patch(
        f"/members/{other_membership.id}/role", json={"role": "lawyer"}, headers=headers, cookies=cookies
    )

    assert resp.status_code == 200
    assert resp.json()["role"] == "lawyer"


def test_can_demote_self(admin_client, db):
    """Deliberately allowed, no "last manager standing" guard — see module
    docstring; this is what makes self-service leaving safe to allow at all.
    """
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    membership = make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.patch(
        f"/members/{membership.id}/role", json={"role": "lawyer"}, headers=headers, cookies=cookies
    )

    assert resp.status_code == 200


def test_cannot_change_client_role(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    client_identity = make_identity(db, "client@acme.com")
    client_membership = make_membership(db, client_identity.id, tenant.id, UserRole.CLIENT)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.patch(
        f"/members/{client_membership.id}/role", json={"role": "office_manager"}, headers=headers, cookies=cookies
    )

    assert resp.status_code == 400


def test_cannot_set_role_to_client(admin_client, db):
    """The schema itself restricts the target role — a client value is
    rejected before it even reaches the route (422, not 400).
    """
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.patch(
        f"/members/{lawyer_membership.id}/role", json={"role": "client"}, headers=headers, cookies=cookies
    )

    assert resp.status_code == 422


def test_role_change_rejects_membership_from_another_tenant(admin_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    other_identity = make_identity(db, "lawyer@globex.com")
    other_membership = make_membership(db, other_identity.id, tenant_b.id, UserRole.LAWYER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.patch(
        f"/members/{other_membership.id}/role", json={"role": "office_manager"}, headers=headers, cookies=cookies
    )

    assert resp.status_code == 404


def test_lawyer_cannot_change_roles(admin_client, db):
    tenant = make_tenant(db, "acme")
    lawyer = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer.id, tenant.id, UserRole.LAWYER)
    other_identity = make_identity(db, "other@acme.com")
    other_membership = make_membership(db, other_identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(lawyer, "acme")

    resp = admin_client.patch(
        f"/members/{other_membership.id}/role", json={"role": "office_manager"}, headers=headers, cookies=cookies
    )

    assert resp.status_code == 403


# --- POST /auth/leave-firm ---


def test_office_manager_can_leave_firm(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    membership = make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.post("/auth/leave-firm", headers=headers, cookies=cookies)

    assert resp.status_code == 204
    db.refresh(membership)
    assert membership.active is False


def test_only_office_manager_can_leave_and_strand_no_one(admin_client, db):
    """The firm's only office_manager leaving is allowed with no guard —
    CLAUDE.md is explicit this isn't treated as a dangerous edge case.
    """
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.post("/auth/leave-firm", headers=headers, cookies=cookies)

    assert resp.status_code == 204
    remaining = db.query(Membership).filter(Membership.tenant_id == tenant.id, Membership.active.is_(True)).count()
    assert remaining == 0


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
