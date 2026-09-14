from conftest import auth_for, make_identity, make_membership, make_tenant
from shared.models.enums import UserRole


def test_office_manager_can_toggle_lawyer_visibility(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.patch(
        f"/members/{lawyer_membership.id}/public-visibility",
        json={"show_on_public_page": True},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 200
    assert resp.json()["show_on_public_page"] is True


def test_client_membership_cannot_be_made_public(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    client_identity = make_identity(db, "client@acme.com")
    client_membership = make_membership(db, client_identity.id, tenant.id, UserRole.CLIENT)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.patch(
        f"/members/{client_membership.id}/public-visibility",
        json={"show_on_public_page": True},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 400


def test_inactive_membership_cannot_be_made_public(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    lawyer_membership.active = False
    db.commit()
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.patch(
        f"/members/{lawyer_membership.id}/public-visibility",
        json={"show_on_public_page": True},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 400


def test_lawyer_cannot_toggle_own_visibility(admin_client, db):
    tenant = make_tenant(db, "acme")
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = admin_client.patch(
        f"/members/{lawyer_membership.id}/public-visibility",
        json={"show_on_public_page": True},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 403


# --- GET/PATCH /auth/my-public-visibility (office_manager's own toggle) ---
#
# The only reachable lever for this now that the Admins page is gone
# (CLAUDE.md's single-office_manager reversal) — self-targeting, no
# membership_id in the URL at all.


def test_office_manager_can_read_own_visibility(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager_identity = make_identity(db, "manager@acme.com")
    membership = make_membership(db, manager_identity.id, tenant.id, UserRole.OFFICE_MANAGER)
    membership.show_on_public_page = True
    db.commit()
    headers, cookies = auth_for(manager_identity, "acme")

    resp = admin_client.get("/auth/my-public-visibility", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    assert resp.json()["show_on_public_page"] is True


def test_office_manager_can_toggle_own_visibility(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager_identity = make_identity(db, "manager@acme.com")
    membership = make_membership(db, manager_identity.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager_identity, "acme")

    resp = admin_client.patch(
        "/auth/my-public-visibility", json={"show_on_public_page": True}, headers=headers, cookies=cookies
    )

    assert resp.status_code == 200
    assert resp.json()["show_on_public_page"] is True
    db.refresh(membership)
    assert membership.show_on_public_page is True


def test_lawyer_cannot_use_own_public_visibility_route(admin_client, db):
    tenant = make_tenant(db, "acme")
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = admin_client.patch(
        "/auth/my-public-visibility", json={"show_on_public_page": True}, headers=headers, cookies=cookies
    )

    assert resp.status_code == 403
