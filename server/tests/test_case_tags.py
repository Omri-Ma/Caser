from conftest import auth_for, make_case, make_identity, make_membership, make_tenant
from shared.models.enums import UserRole


def test_office_manager_sets_case_tags(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    case = make_case(db, tenant.id, "Smith v. Jones")
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.put(
        f"/cases/{case.id}/tags",
        json={"practice_areas": ["family", "traffic"]},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert set(body["practice_areas"]) == {"family", "traffic"}


def test_setting_tags_replaces_previous_set(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    case = make_case(db, tenant.id, "Smith v. Jones")
    headers, cookies = auth_for(manager, "acme")

    admin_client.put(f"/cases/{case.id}/tags", json={"practice_areas": ["family"]}, headers=headers, cookies=cookies)
    resp = admin_client.put(f"/cases/{case.id}/tags", json={"practice_areas": ["criminal"]}, headers=headers, cookies=cookies)

    assert resp.json()["practice_areas"] == ["criminal"]


def test_lawyer_cannot_set_case_tags(admin_client, db):
    tenant = make_tenant(db, "acme")
    lawyer = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer.id, tenant.id, UserRole.LAWYER)
    case = make_case(db, tenant.id, "Smith v. Jones")
    headers, cookies = auth_for(lawyer, "acme")

    resp = admin_client.put(f"/cases/{case.id}/tags", json={"practice_areas": ["family"]}, headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_cannot_set_tags_on_another_tenants_case(admin_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    manager_a = make_identity(db, "manager@acme.com")
    make_membership(db, manager_a.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    case_b = make_case(db, tenant_b.id, "Globex Case")
    headers, cookies = auth_for(manager_a, "acme")

    resp = admin_client.put(f"/cases/{case_b.id}/tags", json={"practice_areas": ["family"]}, headers=headers, cookies=cookies)

    assert resp.status_code == 404


def test_filter_cases_by_practice_area(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    tagged = make_case(db, tenant.id, "Family Case")
    make_case(db, tenant.id, "Untagged Case")
    headers, cookies = auth_for(manager, "acme")
    admin_client.put(f"/cases/{tagged.id}/tags", json={"practice_areas": ["family"]}, headers=headers, cookies=cookies)

    resp = admin_client.get("/cases", params={"practice_area": "family"}, headers=headers, cookies=cookies)

    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == tagged.id
