from conftest import auth_for, make_assignment, make_case, make_identity, make_membership, make_tenant
from shared.models.enums import UserRole


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
