from conftest import auth_for, make_identity, make_invite, make_membership, make_tenant
from shared.models import Membership
from shared.models.enums import InviteStatus, UserRole


def test_list_my_invites_returns_pending_invites_across_tenants(client_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    manager_a = make_identity(db, "manager@acme.com")
    manager_a_membership = make_membership(db, manager_a.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    manager_b = make_identity(db, "manager@globex.com")
    manager_b_membership = make_membership(db, manager_b.id, tenant_b.id, UserRole.OFFICE_MANAGER)

    invitee = make_identity(db, "invitee@example.com")
    make_invite(db, tenant_a.id, invitee.email, UserRole.LAWYER, manager_a_membership.id)
    make_invite(db, tenant_b.id, invitee.email, UserRole.CLIENT, manager_b_membership.id)

    headers, cookies = auth_for(invitee, "acme")
    resp = client_client.get("/invites", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    firms = {item["firm_name"] for item in resp.json()}
    assert firms == {tenant_a.name, tenant_b.name}


def test_accept_invite_creates_membership(client_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    manager_membership = make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    invitee = make_identity(db, "invitee@example.com")
    invite = make_invite(db, tenant.id, invitee.email, UserRole.LAWYER, manager_membership.id)
    headers, cookies = auth_for(invitee, "acme")

    resp = client_client.post(f"/invites/{invite.id}/accept", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    assert body["subdomain"] == "acme"
    assert body["role"] == "lawyer"

    membership = (
        db.query(Membership).filter(Membership.identity_id == invitee.id, Membership.tenant_id == tenant.id).first()
    )
    assert membership is not None
    assert membership.active is True
    assert membership.role == UserRole.LAWYER

    db.refresh(invite)
    assert invite.status == InviteStatus.ACCEPTED
    assert invite.responded_at is not None


def test_decline_invite_creates_no_membership(client_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    manager_membership = make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    invitee = make_identity(db, "invitee@example.com")
    invite = make_invite(db, tenant.id, invitee.email, UserRole.CLIENT, manager_membership.id)
    headers, cookies = auth_for(invitee, "acme")

    resp = client_client.post(f"/invites/{invite.id}/decline", headers=headers, cookies=cookies)

    assert resp.status_code == 204
    membership = (
        db.query(Membership).filter(Membership.identity_id == invitee.id, Membership.tenant_id == tenant.id).first()
    )
    assert membership is None

    db.refresh(invite)
    assert invite.status == InviteStatus.DECLINED


def test_cannot_accept_someone_elses_invite(client_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    manager_membership = make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    invitee = make_identity(db, "invitee@example.com")
    invite = make_invite(db, tenant.id, invitee.email, UserRole.LAWYER, manager_membership.id)

    someone_else = make_identity(db, "someone-else@example.com")
    headers, cookies = auth_for(someone_else, "acme")

    resp = client_client.post(f"/invites/{invite.id}/accept", headers=headers, cookies=cookies)

    assert resp.status_code == 404


def test_cannot_re_accept_already_resolved_invite(client_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    manager_membership = make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    invitee = make_identity(db, "invitee@example.com")
    invite = make_invite(db, tenant.id, invitee.email, UserRole.LAWYER, manager_membership.id)
    headers, cookies = auth_for(invitee, "acme")

    client_client.post(f"/invites/{invite.id}/accept", headers=headers, cookies=cookies)
    resp = client_client.post(f"/invites/{invite.id}/accept", headers=headers, cookies=cookies)

    assert resp.status_code == 404


def test_registering_auto_accepts_matching_pending_invites(client_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    manager_a = make_identity(db, "manager@acme.com")
    manager_a_membership = make_membership(db, manager_a.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    manager_b = make_identity(db, "manager@globex.com")
    manager_b_membership = make_membership(db, manager_b.id, tenant_b.id, UserRole.OFFICE_MANAGER)

    make_invite(db, tenant_a.id, "newperson@example.com", UserRole.LAWYER, manager_a_membership.id)
    make_invite(db, tenant_b.id, "newperson@example.com", UserRole.CLIENT, manager_b_membership.id)

    resp = client_client.post(
        "/auth/register",
        json={"name": "New Person", "email": "newperson@example.com", "password": "BrandNewPass123"},
    )
    assert resp.status_code == 201
    identity_id = resp.json()["id"]

    memberships = db.query(Membership).filter(Membership.identity_id == identity_id).all()
    assert {(m.tenant_id, m.role) for m in memberships} == {(tenant_a.id, UserRole.LAWYER), (tenant_b.id, UserRole.CLIENT)}


def test_lobby_login_surfaces_pending_invites(client_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    manager_membership = make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    invitee = make_identity(db, "invitee@example.com")
    make_invite(db, tenant.id, invitee.email, UserRole.LAWYER, manager_membership.id)

    resp = client_client.post("/auth/lobby-login", json={"email": invitee.email, "password": "password123"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["tenants"] == []
    assert len(body["pending_invites"]) == 1
    assert body["pending_invites"][0]["firm_name"] == tenant.name
    assert body["pending_invites"][0]["role"] == "lawyer"
