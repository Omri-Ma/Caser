from conftest import auth_for, make_identity, make_invite, make_membership, make_tenant
from shared.models.enums import InviteStatus, UserRole


def test_invite_lawyer_creates_pending_invite(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.post(
        "/invites", json={"email": "newlawyer@acme.com", "role": "lawyer"}, headers=headers, cookies=cookies
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "newlawyer@acme.com"
    assert body["role"] == "lawyer"
    assert body["status"] == "pending"
    assert body["invited_by_name"] == manager.name


def test_revoke_pending_invite(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    manager_membership = make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    invite = make_invite(db, tenant.id, "invitee@example.com", UserRole.LAWYER, manager_membership.id)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.post(f"/invites/{invite.id}/revoke", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    assert resp.json()["status"] == "revoked"
    db.refresh(invite)
    assert invite.status == InviteStatus.REVOKED


def test_revoke_frees_up_the_lawyer_limit(admin_client, db):
    """The actual point of revoking: it un-blocks new invites/lawyers,
    unlike a declined or never-answered invite which CLAUDE.md is explicit
    should NOT free up a seat on its own.
    """
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    manager_membership = make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    for i in range(3):
        make_invite(db, tenant.id, f"pending{i}@acme.com", UserRole.LAWYER, manager_membership.id)
    headers, cookies = auth_for(manager, "acme")

    # Free plan caps at 3 lawyers - already at capacity via pending invites alone.
    blocked = admin_client.post(
        "/invites", json={"email": "one-more@acme.com", "role": "lawyer"}, headers=headers, cookies=cookies
    )
    assert blocked.status_code == 400

    pending = admin_client.get("/invites", headers=headers, cookies=cookies).json()["items"]
    admin_client.post(f"/invites/{pending[0]['id']}/revoke", headers=headers, cookies=cookies)

    allowed = admin_client.post(
        "/invites", json={"email": "one-more@acme.com", "role": "lawyer"}, headers=headers, cookies=cookies
    )
    assert allowed.status_code == 201


def test_cannot_revoke_already_accepted_invite(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    manager_membership = make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    invite = make_invite(
        db, tenant.id, "invitee@example.com", UserRole.LAWYER, manager_membership.id, InviteStatus.ACCEPTED
    )
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.post(f"/invites/{invite.id}/revoke", headers=headers, cookies=cookies)

    assert resp.status_code == 400


def test_revoke_rejects_invite_from_another_tenant(admin_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    other_manager = make_identity(db, "manager@globex.com")
    other_membership = make_membership(db, other_manager.id, tenant_b.id, UserRole.OFFICE_MANAGER)
    invite = make_invite(db, tenant_b.id, "invitee@example.com", UserRole.LAWYER, other_membership.id)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.post(f"/invites/{invite.id}/revoke", headers=headers, cookies=cookies)

    assert resp.status_code == 404


def test_invite_writes_dev_outbox_only_for_unregistered_email(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    existing = make_identity(db, "already-here@example.com")
    headers, cookies = auth_for(manager, "acme")

    # Unregistered email -> gets a dev-outbox entry (nowhere else to see it).
    admin_client.post("/invites", json={"email": "brand-new@example.com", "role": "client"}, headers=headers, cookies=cookies)
    outbox_new = admin_client.get("/auth/dev-outbox", params={"email": "brand-new@example.com"}).json()
    assert len(outbox_new) == 1
    assert "/register?email=brand-new@example.com" in outbox_new[0]["link"]
    assert "acme.lvh.me" in outbox_new[0]["link"]

    # Already-registered email -> no outbox entry, they see it at next login.
    admin_client.post("/invites", json={"email": existing.email, "role": "client"}, headers=headers, cookies=cookies)
    outbox_existing = admin_client.get("/auth/dev-outbox", params={"email": existing.email}).json()
    assert outbox_existing == []


def test_invite_rejects_office_manager_role(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.post(
        "/invites", json={"email": "colleague@acme.com", "role": "office_manager"}, headers=headers, cookies=cookies
    )

    assert resp.status_code == 400


def test_invite_rejects_duplicate_pending_invite(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    manager_membership = make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    make_invite(db, tenant.id, "lawyer@acme.com", UserRole.LAWYER, manager_membership.id)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.post(
        "/invites", json={"email": "lawyer@acme.com", "role": "lawyer"}, headers=headers, cookies=cookies
    )

    assert resp.status_code == 400


def test_invite_rejects_already_active_member(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.post(
        "/invites", json={"email": "lawyer@acme.com", "role": "lawyer"}, headers=headers, cookies=cookies
    )

    assert resp.status_code == 400


def test_invite_counts_pending_invites_against_plan_limit(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    manager_membership = make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    # Free plan's hardcoded limit is 3 lawyers (shared/plan_limits.py) — fill
    # it with pending invites, not active memberships, to prove the check
    # counts both.
    for i in range(3):
        make_invite(db, tenant.id, f"lawyer{i}@acme.com", UserRole.LAWYER, manager_membership.id)

    resp = admin_client.post(
        "/invites", json={"email": "lawyer4@acme.com", "role": "lawyer"}, headers=headers, cookies=cookies
    )

    assert resp.status_code == 400


def test_declined_invite_does_not_permanently_consume_a_seat(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    manager_membership = make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    for i in range(3):
        make_invite(
            db,
            tenant.id,
            f"lawyer{i}@acme.com",
            UserRole.LAWYER,
            manager_membership.id,
            invite_status=InviteStatus.DECLINED,
        )

    resp = admin_client.post(
        "/invites", json={"email": "lawyer4@acme.com", "role": "lawyer"}, headers=headers, cookies=cookies
    )

    assert resp.status_code == 201


def test_lawyer_cannot_create_or_list_invites(admin_client, db):
    tenant = make_tenant(db, "acme")
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(lawyer_identity, "acme")

    create_resp = admin_client.post(
        "/invites", json={"email": "someone@acme.com", "role": "client"}, headers=headers, cookies=cookies
    )
    list_resp = admin_client.get("/invites", headers=headers, cookies=cookies)

    assert create_resp.status_code == 403
    assert list_resp.status_code == 403


def test_list_invites_filters_by_role_and_tenant(admin_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    manager_a = make_identity(db, "manager@acme.com")
    manager_a_membership = make_membership(db, manager_a.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    manager_b = make_identity(db, "manager@globex.com")
    manager_b_membership = make_membership(db, manager_b.id, tenant_b.id, UserRole.OFFICE_MANAGER)

    make_invite(db, tenant_a.id, "lawyer@acme.com", UserRole.LAWYER, manager_a_membership.id)
    make_invite(db, tenant_a.id, "client@acme.com", UserRole.CLIENT, manager_a_membership.id)
    make_invite(db, tenant_b.id, "lawyer@globex.com", UserRole.LAWYER, manager_b_membership.id)

    headers, cookies = auth_for(manager_a, "acme")
    resp = admin_client.get("/invites", params={"role": "lawyer"}, headers=headers, cookies=cookies)

    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "lawyer@acme.com"
