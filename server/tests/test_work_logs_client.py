from conftest import auth_for, make_assignment, make_case, make_identity, make_membership, make_tenant, make_work_log
from shared.models import AuditLog
from shared.models.enums import CaseStatus, UserRole


def _lawyer_on_case(db, tenant, case):
    identity = make_identity(db, "lawyer@acme.com", "Lior Lawyer")
    membership = make_membership(db, identity.id, tenant.id, UserRole.LAWYER)
    make_assignment(db, tenant.id, case.id, membership.id)
    return identity, membership


def _client_on_case(db, tenant, case):
    identity = make_identity(db, "client@acme.com", "Dana Client")
    membership = make_membership(db, identity.id, tenant.id, UserRole.CLIENT)
    make_assignment(db, tenant.id, case.id, membership.id)
    return identity, membership


def test_lawyer_creates_work_log(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, _ = _lawyer_on_case(db, tenant, case)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.post(
        f"/cases/{case.id}/work-logs",
        json={"date": "2026-09-01", "hours": "3.5", "description": "Drafted motion"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["hours"] == "3.50"
    assert body["source"] == "manual"
    assert body["lawyer_name"] == "Lior Lawyer"


def test_client_cannot_create_work_log(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    client_identity, _ = _client_on_case(db, tenant, case)
    headers, cookies = auth_for(client_identity, "acme")

    resp = client_client.post(
        f"/cases/{case.id}/work-logs",
        json={"date": "2026-09-01", "hours": "2", "description": "n/a"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 403


def test_client_cannot_list_work_logs(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    client_identity, client_membership = _client_on_case(db, tenant, case)
    make_work_log(db, tenant.id, case.id, client_membership.id)
    headers, cookies = auth_for(client_identity, "acme")

    resp = client_client.get(f"/cases/{case.id}/work-logs", headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_create_rejects_unassigned_lawyer(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    identity = make_identity(db, "outsider@acme.com")
    make_membership(db, identity.id, tenant.id, UserRole.LAWYER)  # not assigned to this case
    headers, cookies = auth_for(identity, "acme")

    resp = client_client.post(
        f"/cases/{case.id}/work-logs",
        json={"date": "2026-09-01", "hours": "2", "description": "n/a"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 403


def test_create_blocked_on_closed_case(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id, status=CaseStatus.CLOSED)
    lawyer_identity, _ = _lawyer_on_case(db, tenant, case)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.post(
        f"/cases/{case.id}/work-logs",
        json={"date": "2026-09-01", "hours": "2", "description": "n/a"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 400


def test_create_rejects_non_positive_hours(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, _ = _lawyer_on_case(db, tenant, case)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.post(
        f"/cases/{case.id}/work-logs",
        json={"date": "2026-09-01", "hours": "0", "description": "n/a"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 422


def test_lawyer_edits_colleagues_entry(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, _ = _lawyer_on_case(db, tenant, case)
    colleague_identity = make_identity(db, "colleague@acme.com")
    colleague_membership = make_membership(db, colleague_identity.id, tenant.id, UserRole.LAWYER)
    make_assignment(db, tenant.id, case.id, colleague_membership.id)
    entry = make_work_log(db, tenant.id, case.id, colleague_membership.id)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.patch(
        f"/cases/{case.id}/work-logs/{entry.id}",
        json={"date": "2026-09-02", "hours": "4", "description": "Updated"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 200
    assert resp.json()["hours"] == "4.00"

    log = db.query(AuditLog).filter(AuditLog.action == "work_log_edited").first()
    assert log is not None
    assert log.tenant_id == tenant.id


def test_edit_blocked_on_closed_case(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, lawyer_membership = _lawyer_on_case(db, tenant, case)
    entry = make_work_log(db, tenant.id, case.id, lawyer_membership.id)
    case.status = CaseStatus.CLOSED
    db.commit()
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.patch(
        f"/cases/{case.id}/work-logs/{entry.id}",
        json={"date": "2026-09-02", "hours": "4", "description": "Updated"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 400


def test_lawyer_deletes_colleagues_entry_and_it_is_audited(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, _ = _lawyer_on_case(db, tenant, case)
    colleague_identity = make_identity(db, "colleague@acme.com")
    colleague_membership = make_membership(db, colleague_identity.id, tenant.id, UserRole.LAWYER)
    make_assignment(db, tenant.id, case.id, colleague_membership.id)
    entry = make_work_log(db, tenant.id, case.id, colleague_membership.id)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.delete(f"/cases/{case.id}/work-logs/{entry.id}", headers=headers, cookies=cookies)

    assert resp.status_code == 204
    log = db.query(AuditLog).filter(AuditLog.action == "work_log_deleted").first()
    assert log is not None

    listing = client_client.get(f"/cases/{case.id}/work-logs", headers=headers, cookies=cookies)
    assert listing.json()["total"] == 0


def test_delete_blocked_on_closed_case(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, lawyer_membership = _lawyer_on_case(db, tenant, case)
    entry = make_work_log(db, tenant.id, case.id, lawyer_membership.id)
    case.status = CaseStatus.CLOSED
    db.commit()
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.delete(f"/cases/{case.id}/work-logs/{entry.id}", headers=headers, cookies=cookies)

    assert resp.status_code == 400
