from conftest import auth_for, make_case, make_identity, make_membership, make_tenant
from shared.models.enums import CaseStatus, UserRole


def test_office_manager_creates_case(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.post("/cases", json={"title": "Smith v. Jones"}, headers=headers, cookies=cookies)

    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Smith v. Jones"
    assert body["status"] == "open"
    assert body["tenant_id"] == tenant.id


def test_lawyer_cannot_create_case(admin_client, db):
    tenant = make_tenant(db, "acme")
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = admin_client.post("/cases", json={"title": "Nope"}, headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_office_manager_sees_every_case_without_assignment(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    make_case(db, tenant.id, "Case One")
    make_case(db, tenant.id, "Case Two")
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.get("/cases", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert {c["title"] for c in body["items"]} == {"Case One", "Case Two"}


def test_list_cases_is_paginated(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    for i in range(3):
        make_case(db, tenant.id, f"Case {i}")
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.get("/cases", params={"page": 1, "page_size": 2}, headers=headers, cookies=cookies)

    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["page_size"] == 2


def test_office_manager_edits_case_title(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    case = make_case(db, tenant.id, "Old Title")
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.patch(f"/cases/{case.id}", json={"title": "New Title"}, headers=headers, cookies=cookies)

    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"


def test_office_manager_can_reopen_closed_case(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    case = make_case(db, tenant.id, "Case", status=CaseStatus.CLOSED)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.patch(f"/cases/{case.id}/status", json={"status": "open"}, headers=headers, cookies=cookies)

    assert resp.status_code == 200
    assert resp.json()["status"] == "open"


def test_lawyer_cannot_change_case_status(admin_client, db):
    tenant = make_tenant(db, "acme")
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    case = make_case(db, tenant.id, "Case")
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = admin_client.patch(f"/cases/{case.id}/status", json={"status": "closed"}, headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_assign_lawyer_to_case(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    case = make_case(db, tenant.id)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.post(
        f"/cases/{case.id}/assignments",
        json={"membership_id": lawyer_membership.id},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["membership_id"] == lawyer_membership.id
    assert body["role"] == "lawyer"
    assert body["identity_email"] == "lawyer@acme.com"


def test_cannot_assign_office_manager_membership_to_case(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    manager_membership = make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    case = make_case(db, tenant.id)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.post(
        f"/cases/{case.id}/assignments",
        json={"membership_id": manager_membership.id},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 400


def test_duplicate_assignment_rejected(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    case = make_case(db, tenant.id)
    headers, cookies = auth_for(manager, "acme")

    admin_client.post(
        f"/cases/{case.id}/assignments", json={"membership_id": lawyer_membership.id}, headers=headers, cookies=cookies
    )
    resp = admin_client.post(
        f"/cases/{case.id}/assignments", json={"membership_id": lawyer_membership.id}, headers=headers, cookies=cookies
    )

    assert resp.status_code == 400


def test_unassign_from_case(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    case = make_case(db, tenant.id)
    headers, cookies = auth_for(manager, "acme")

    create_resp = admin_client.post(
        f"/cases/{case.id}/assignments", json={"membership_id": lawyer_membership.id}, headers=headers, cookies=cookies
    )
    assignment_id = create_resp.json()["id"]

    del_resp = admin_client.delete(f"/cases/{case.id}/assignments/{assignment_id}", headers=headers, cookies=cookies)
    assert del_resp.status_code == 204

    list_resp = admin_client.get(f"/cases/{case.id}/assignments", headers=headers, cookies=cookies)
    assert list_resp.json()["total"] == 0
