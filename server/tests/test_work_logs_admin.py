from conftest import auth_for, make_case, make_identity, make_membership, make_tenant, make_work_log
from shared.models import AuditLog
from shared.models.enums import CaseStatus, UserRole


def _manager(db, tenant):
    identity = make_identity(db, "manager@acme.com", "Noa Manager")
    membership = make_membership(db, identity.id, tenant.id, UserRole.OFFICE_MANAGER)
    return identity, membership


def test_office_manager_lists_work_logs_without_assignment(admin_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, manager_membership = _manager(db, tenant)
    make_work_log(db, tenant.id, case.id, manager_membership.id)
    headers, cookies = auth_for(manager_identity, "acme")

    resp = admin_client.get(f"/cases/{case.id}/work-logs", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_lawyer_cannot_use_admin_work_logs_route(admin_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = admin_client.get(f"/cases/{case.id}/work-logs", headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_office_manager_edits_any_entry(admin_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, manager_membership = _manager(db, tenant)
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    entry = make_work_log(db, tenant.id, case.id, lawyer_membership.id)
    headers, cookies = auth_for(manager_identity, "acme")

    resp = admin_client.patch(
        f"/cases/{case.id}/work-logs/{entry.id}",
        json={"date": "2026-09-02", "hours": "6", "description": "Corrected"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 200
    assert resp.json()["hours"] == "6.00"
    log = db.query(AuditLog).filter(AuditLog.action == "work_log_edited").first()
    assert log is not None
    assert log.user_id == manager_membership.id


def test_office_manager_deletes_any_entry(admin_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, manager_membership = _manager(db, tenant)
    entry = make_work_log(db, tenant.id, case.id, manager_membership.id)
    headers, cookies = auth_for(manager_identity, "acme")

    resp = admin_client.delete(f"/cases/{case.id}/work-logs/{entry.id}", headers=headers, cookies=cookies)

    assert resp.status_code == 204
    log = db.query(AuditLog).filter(AuditLog.action == "work_log_deleted").first()
    assert log is not None


def test_office_manager_edit_blocked_on_closed_case(admin_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, manager_membership = _manager(db, tenant)
    entry = make_work_log(db, tenant.id, case.id, manager_membership.id)
    case.status = CaseStatus.CLOSED
    db.commit()
    headers, cookies = auth_for(manager_identity, "acme")

    resp = admin_client.patch(
        f"/cases/{case.id}/work-logs/{entry.id}",
        json={"date": "2026-09-02", "hours": "6", "description": "Corrected"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 400
