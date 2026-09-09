from conftest import auth_for, make_assignment, make_case, make_identity, make_membership, make_tenant
from shared.models.enums import CaseStatus, UserRole


def test_lawyer_lists_only_assigned_cases(client_client, db):
    tenant = make_tenant(db, "acme")
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    assigned_case = make_case(db, tenant.id, "Assigned Case")
    make_case(db, tenant.id, "Unassigned Case")
    make_assignment(db, tenant.id, assigned_case.id, lawyer_membership.id)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.get("/cases", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Assigned Case"


def test_client_lists_only_assigned_cases(client_client, db):
    tenant = make_tenant(db, "acme")
    client_identity = make_identity(db, "client@acme.com")
    client_membership = make_membership(db, client_identity.id, tenant.id, UserRole.CLIENT)
    assigned_case = make_case(db, tenant.id, "My Case")
    make_case(db, tenant.id, "Someone Else's Case")
    make_assignment(db, tenant.id, assigned_case.id, client_membership.id)
    headers, cookies = auth_for(client_identity, "acme")

    resp = client_client.get("/cases", headers=headers, cookies=cookies)

    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["title"] == "My Case"


def test_lawyer_searches_own_cases_by_title(client_client, db):
    tenant = make_tenant(db, "acme")
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    smith_case = make_case(db, tenant.id, "Smith v. Jones")
    doe_case = make_case(db, tenant.id, "Doe v. Roe")
    make_assignment(db, tenant.id, smith_case.id, lawyer_membership.id)
    make_assignment(db, tenant.id, doe_case.id, lawyer_membership.id)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.get("/cases", params={"search": "smith"}, headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Smith v. Jones"


def test_lawyer_filters_own_cases_by_status(client_client, db):
    tenant = make_tenant(db, "acme")
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    open_case = make_case(db, tenant.id, "Open Case")
    closed_case = make_case(db, tenant.id, "Closed Case", status=CaseStatus.CLOSED)
    make_assignment(db, tenant.id, open_case.id, lawyer_membership.id)
    make_assignment(db, tenant.id, closed_case.id, lawyer_membership.id)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.get("/cases", params={"status": "closed"}, headers=headers, cookies=cookies)

    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Closed Case"


def test_office_manager_gets_no_automatic_client_side_visibility(client_client, db):
    """office_manager works cases through admin_api's own Cases section, not
    client_api — a Membership with role OFFICE_MANAGER shouldn't even pass
    the role check on this side.
    """
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    resp = client_client.get("/cases", headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_lawyer_can_view_assigned_case_detail(client_client, db):
    tenant = make_tenant(db, "acme")
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    case = make_case(db, tenant.id, "Assigned Case")
    make_assignment(db, tenant.id, case.id, lawyer_membership.id)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.get(f"/cases/{case.id}", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    assert resp.json()["title"] == "Assigned Case"


def test_lawyer_cannot_view_unassigned_case_detail(client_client, db):
    tenant = make_tenant(db, "acme")
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    case = make_case(db, tenant.id, "Not My Case")
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.get(f"/cases/{case.id}", headers=headers, cookies=cookies)

    assert resp.status_code == 403
