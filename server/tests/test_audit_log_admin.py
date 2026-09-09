from conftest import auth_for, make_identity, make_membership, make_tenant
from shared.models import AuditLog
from shared.models.enums import UserRole


def _write_audit_log(db, tenant_id, user_id, action, target):
    entry = AuditLog(tenant_id=tenant_id, user_id=user_id, action=action, target=target)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def test_list_audit_log_scoped_to_own_tenant(admin_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    manager = make_identity(db, "manager@acme.com")
    manager_membership = make_membership(db, manager.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    _write_audit_log(db, tenant_a.id, manager_membership.id, "member_deactivated", "membership:9")

    other_manager = make_identity(db, "manager@globex.com")
    other_membership = make_membership(db, other_manager.id, tenant_b.id, UserRole.OFFICE_MANAGER)
    _write_audit_log(db, tenant_b.id, other_membership.id, "member_deactivated", "membership:1")

    resp = admin_client.get("/audit-log", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    entry = body["items"][0]
    assert entry["action"] == "member_deactivated"
    assert entry["target"] == "membership:9"
    assert entry["actor_name"] == "Test User"
    assert entry["actor_email"] == "manager@acme.com"


def test_list_audit_log_filters_by_action(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    manager_membership = make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    _write_audit_log(db, tenant.id, manager_membership.id, "member_deactivated", "membership:1")
    _write_audit_log(db, tenant.id, manager_membership.id, "member_password_reset", "membership:2")

    resp = admin_client.get("/audit-log?action=member_password_reset", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["action"] == "member_password_reset"


def test_list_audit_log_newest_first(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    manager_membership = make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    _write_audit_log(db, tenant.id, manager_membership.id, "member_deactivated", "membership:1")
    _write_audit_log(db, tenant.id, manager_membership.id, "member_password_reset", "membership:2")

    resp = admin_client.get("/audit-log", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    items = resp.json()["items"]
    assert [item["action"] for item in items] == ["member_password_reset", "member_deactivated"]


def test_lawyer_cannot_view_audit_log(admin_client, db):
    tenant = make_tenant(db, "acme")
    lawyer = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(lawyer, "acme")

    resp = admin_client.get("/audit-log", headers=headers, cookies=cookies)

    assert resp.status_code == 403
