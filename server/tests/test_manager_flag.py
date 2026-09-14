"""Memberships.is_manager — the orthogonal case-oversight flag (CLAUDE.md's
Roles/Memberships/CaseAssignments/Narratives notes). This file grows with
the feature; so far it covers both of client_api's authorization paths:
full-tenant case visibility (a manager-flagged lawyer sees every case, the
same automatic visibility office_manager already has in admin_api) and
narrative generation/export authority (manager-flagged lawyers only,
sharing the exact same shared.narratives implementation admin_api's
office_manager route calls).
"""
from conftest import auth_for, make_assignment, make_case, make_identity, make_membership, make_tenant, make_work_log
from shared.models.enums import UserRole


def _manager(db, tenant):
    identity = make_identity(db, "manager@acme.com", "Noa Manager")
    membership = make_membership(db, identity.id, tenant.id, UserRole.OFFICE_MANAGER)
    return identity, membership


def _lawyer(db, tenant, email="lawyer@acme.com", name="Lior Lawyer", is_manager=False, hourly_rate=None):
    identity = make_identity(db, email, name)
    membership = make_membership(db, identity.id, tenant.id, UserRole.LAWYER)
    membership.is_manager = is_manager
    if hourly_rate is not None:
        membership.hourly_rate = hourly_rate
    db.commit()
    return identity, membership


def _client_identity(db, tenant, case):
    identity = make_identity(db, "client@acme.com", "Dana Client")
    membership = make_membership(db, identity.id, tenant.id, UserRole.CLIENT)
    make_assignment(db, tenant.id, case.id, membership.id)
    return identity, membership


# --- client_api: full case visibility ---------------------------------


def test_manager_lawyer_sees_every_case_in_list(client_client, db):
    tenant = make_tenant(db, "acme")
    assigned_case = make_case(db, tenant.id, title="Assigned Case")
    other_case = make_case(db, tenant.id, title="Not Assigned Case")
    manager_identity, manager_membership = _lawyer(db, tenant, is_manager=True)
    make_assignment(db, tenant.id, assigned_case.id, manager_membership.id)
    headers, cookies = auth_for(manager_identity, "acme")

    resp = client_client.get("/cases", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    titles = {item["title"] for item in body["items"]}
    assert body["total"] == 2
    assert {"Assigned Case", "Not Assigned Case"} == titles


def test_plain_lawyer_sees_only_assigned_cases_in_list(client_client, db):
    tenant = make_tenant(db, "acme")
    assigned_case = make_case(db, tenant.id, title="Assigned Case")
    make_case(db, tenant.id, title="Not Assigned Case")
    lawyer_identity, lawyer_membership = _lawyer(db, tenant, is_manager=False)
    make_assignment(db, tenant.id, assigned_case.id, lawyer_membership.id)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.get("/cases", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Assigned Case"


def test_manager_lawyer_can_fetch_unassigned_case_directly(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, _ = _lawyer(db, tenant, is_manager=True)
    headers, cookies = auth_for(manager_identity, "acme")

    resp = client_client.get(f"/cases/{case.id}", headers=headers, cookies=cookies)

    assert resp.status_code == 200


def test_plain_lawyer_cannot_fetch_unassigned_case_directly(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, _ = _lawyer(db, tenant, is_manager=False)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.get(f"/cases/{case.id}", headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_manager_lawyer_can_see_unassigned_case_documents_and_work_logs(client_client, db):
    """is_manager's full visibility isn't scoped to the cases router alone
    — it flows through get_assigned_case, so documents.py/work_logs.py
    (which share that same helper) pick it up automatically too.
    """
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, manager_membership = _lawyer(db, tenant, is_manager=True)
    make_work_log(db, tenant.id, case.id, manager_membership.id, hours="1.0")
    headers, cookies = auth_for(manager_identity, "acme")

    docs_resp = client_client.get(f"/cases/{case.id}/documents", headers=headers, cookies=cookies)
    hours_resp = client_client.get(f"/cases/{case.id}/work-logs", headers=headers, cookies=cookies)

    assert docs_resp.status_code == 200
    assert hours_resp.status_code == 200


def test_client_role_never_gets_full_visibility_even_if_flag_somehow_set(client_client, db):
    """is_manager is documented as lawyer-only/meaningless on a client row
    — confirm has_full_case_visibility's role check actually enforces
    that, not just that the admin_api endpoint refuses to set it on one.
    """
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    client_identity = make_identity(db, "client2@acme.com", "Client Two")
    client_membership = make_membership(db, client_identity.id, tenant.id, UserRole.CLIENT)
    client_membership.is_manager = True  # directly on the row, bypassing the endpoint's own guard
    db.commit()
    headers, cookies = auth_for(client_identity, "acme")

    resp = client_client.get(f"/cases/{case.id}", headers=headers, cookies=cookies)

    assert resp.status_code == 403


# --- client_api: narrative generation/export authority -----------------

DEFAULT_PERIOD = {"period_start": "2000-01-01", "period_end": "2100-01-01"}


def test_manager_lawyer_can_generate_and_export_narrative(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, manager_membership = _lawyer(db, tenant, is_manager=True, hourly_rate="450.00")
    make_work_log(db, tenant.id, case.id, manager_membership.id, hours="2.0")
    headers, cookies = auth_for(manager_identity, "acme")

    generate_resp = client_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)
    assert generate_resp.status_code == 201
    body = generate_resp.json()
    assert body["total_hours"] == "2.00"
    assert body["total_fee"] == "900.00"

    export_resp = client_client.post(
        f"/cases/{case.id}/narratives/{body['id']}/export-pdf",
        json={"filename": "manager-export-test"},
        headers=headers,
        cookies=cookies,
    )
    assert export_resp.status_code == 201
    assert export_resp.json()["original_filename"] == "manager-export-test.pdf"


def test_plain_lawyer_cannot_generate_narrative_even_if_assigned(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, lawyer_membership = _lawyer(db, tenant, is_manager=False)
    make_assignment(db, tenant.id, case.id, lawyer_membership.id)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_client_cannot_generate_narrative(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    client_identity, _ = _client_identity(db, tenant, case)
    headers, cookies = auth_for(client_identity, "acme")

    resp = client_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_manager_lawyer_narrative_matches_admin_api_narrative_generation(client_client, admin_client, db):
    """Both sides call the exact same shared.narratives functions — a
    manager-authority lawyer generating via client_api and an
    office_manager generating via admin_api for identical inputs must
    produce identical totals, proving the two thin routes really do share
    one implementation rather than two copies that could drift.
    """
    tenant = make_tenant(db, "acme")
    case_a = make_case(db, tenant.id, title="Case A")
    case_b = make_case(db, tenant.id, title="Case B")
    manager_identity, manager_membership = _lawyer(db, tenant, is_manager=True, hourly_rate="500.00")
    admin_identity, _ = _manager(db, tenant)
    make_work_log(db, tenant.id, case_a.id, manager_membership.id, hours="4.0")
    make_work_log(db, tenant.id, case_b.id, manager_membership.id, hours="4.0")

    manager_headers, manager_cookies = auth_for(manager_identity, "acme")
    admin_headers, admin_cookies = auth_for(admin_identity, "acme")

    client_resp = client_client.post(
        f"/cases/{case_a.id}/narratives", json=DEFAULT_PERIOD, headers=manager_headers, cookies=manager_cookies
    )
    admin_resp = admin_client.post(
        f"/cases/{case_b.id}/narratives", json=DEFAULT_PERIOD, headers=admin_headers, cookies=admin_cookies
    )

    assert client_resp.status_code == 201
    assert admin_resp.status_code == 201
    assert client_resp.json()["total_hours"] == admin_resp.json()["total_hours"] == "4.00"
    assert client_resp.json()["total_fee"] == admin_resp.json()["total_fee"] == "2000.00"
