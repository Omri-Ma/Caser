"""Phase 1's required tenant-isolation test (CLAUDE.md's Multi-tenancy
architecture): a request resolved to tenant A's subdomain must never be able
to retrieve, list, or otherwise touch tenant B's Case data — on either
backend, under any role. Written against the real Case endpoints, since
that's the first slice to actually land tenant-scoped resources beyond auth.
"""

from conftest import auth_for, make_assignment, make_case, make_identity, make_membership, make_tenant
from shared.models.enums import UserRole


def test_office_manager_cannot_get_another_tenants_case(admin_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    manager_a = make_identity(db, "manager@acme.com")
    make_membership(db, manager_a.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    case_b = make_case(db, tenant_b.id, "Globex Secret Case")
    headers, cookies = auth_for(manager_a, "acme")

    resp = admin_client.get(f"/cases/{case_b.id}", headers=headers, cookies=cookies)

    assert resp.status_code == 404


def test_office_manager_list_never_includes_another_tenants_cases(admin_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    manager_a = make_identity(db, "manager@acme.com")
    make_membership(db, manager_a.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    make_case(db, tenant_a.id, "Acme Case")
    make_case(db, tenant_b.id, "Globex Case")
    headers, cookies = auth_for(manager_a, "acme")

    resp = admin_client.get("/cases", headers=headers, cookies=cookies)

    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Acme Case"


def test_office_manager_cannot_edit_another_tenants_case_title(admin_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    manager_a = make_identity(db, "manager@acme.com")
    make_membership(db, manager_a.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    case_b = make_case(db, tenant_b.id, "Globex Case")
    headers, cookies = auth_for(manager_a, "acme")

    resp = admin_client.patch(f"/cases/{case_b.id}", json={"title": "Hijacked"}, headers=headers, cookies=cookies)

    assert resp.status_code == 404
    db.refresh(case_b)
    assert case_b.title == "Globex Case"


def test_office_manager_cannot_change_another_tenants_case_status(admin_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    manager_a = make_identity(db, "manager@acme.com")
    make_membership(db, manager_a.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    case_b = make_case(db, tenant_b.id, "Globex Case")
    headers, cookies = auth_for(manager_a, "acme")

    resp = admin_client.patch(
        f"/cases/{case_b.id}/status", json={"status": "closed"}, headers=headers, cookies=cookies
    )

    assert resp.status_code == 404


def test_office_manager_cannot_assign_across_tenants_via_case_id(admin_client, db):
    """The case_id in the URL belongs to tenant B; even though the office
    manager and the target membership are both tenant A, get_tenant_scoped
    on the case must reject it before assignment logic ever runs.
    """
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    manager_a = make_identity(db, "manager@acme.com")
    make_membership(db, manager_a.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    lawyer_a_identity = make_identity(db, "lawyer@acme.com")
    lawyer_a_membership = make_membership(db, lawyer_a_identity.id, tenant_a.id, UserRole.LAWYER)
    case_b = make_case(db, tenant_b.id, "Globex Case")
    headers, cookies = auth_for(manager_a, "acme")

    resp = admin_client.post(
        f"/cases/{case_b.id}/assignments",
        json={"membership_id": lawyer_a_membership.id},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 404


def test_office_manager_cannot_assign_another_tenants_membership_via_get_tenant_scoped(admin_client, db):
    """The inverse: case is tenant A's own, but the membership_id in the
    request body belongs to tenant B. get_tenant_scoped on the membership_id
    must reject this — a bare `.filter(Membership.id == ...)` would have let
    it through since the row exists, just not at this tenant.
    """
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    manager_a = make_identity(db, "manager@acme.com")
    make_membership(db, manager_a.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    lawyer_b_identity = make_identity(db, "lawyer@globex.com")
    lawyer_b_membership = make_membership(db, lawyer_b_identity.id, tenant_b.id, UserRole.LAWYER)
    case_a = make_case(db, tenant_a.id, "Acme Case")
    headers, cookies = auth_for(manager_a, "acme")

    resp = admin_client.post(
        f"/cases/{case_a.id}/assignments",
        json={"membership_id": lawyer_b_membership.id},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 404


def test_office_manager_cannot_unassign_another_tenants_assignment(admin_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    manager_a = make_identity(db, "manager@acme.com")
    make_membership(db, manager_a.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    lawyer_b_identity = make_identity(db, "lawyer@globex.com")
    lawyer_b_membership = make_membership(db, lawyer_b_identity.id, tenant_b.id, UserRole.LAWYER)
    case_b = make_case(db, tenant_b.id, "Globex Case")
    assignment_b = make_assignment(db, tenant_b.id, case_b.id, lawyer_b_membership.id)
    headers, cookies = auth_for(manager_a, "acme")

    resp = admin_client.delete(
        f"/cases/{case_b.id}/assignments/{assignment_b.id}", headers=headers, cookies=cookies
    )

    assert resp.status_code == 404


def test_lawyer_cannot_list_another_tenants_cases_even_if_assigned_elsewhere(client_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    # Same identity happens to be a lawyer at both firms — CLAUDE.md's "one
    # login, many firms" model. Their tenant B membership/assignment must
    # never surface when they're operating on tenant A's subdomain.
    lawyer_identity = make_identity(db, "lawyer@multi.com")
    make_membership(db, lawyer_identity.id, tenant_a.id, UserRole.LAWYER)
    lawyer_b_membership = make_membership(db, lawyer_identity.id, tenant_b.id, UserRole.LAWYER)
    case_b = make_case(db, tenant_b.id, "Globex Case")
    make_assignment(db, tenant_b.id, case_b.id, lawyer_b_membership.id)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.get("/cases", headers=headers, cookies=cookies)

    assert resp.json()["total"] == 0


def test_lawyer_cannot_view_another_tenants_case_detail(client_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    lawyer_identity = make_identity(db, "lawyer@multi.com")
    make_membership(db, lawyer_identity.id, tenant_a.id, UserRole.LAWYER)
    lawyer_b_membership = make_membership(db, lawyer_identity.id, tenant_b.id, UserRole.LAWYER)
    case_b = make_case(db, tenant_b.id, "Globex Case")
    make_assignment(db, tenant_b.id, case_b.id, lawyer_b_membership.id)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.get(f"/cases/{case_b.id}", headers=headers, cookies=cookies)

    assert resp.status_code == 404


def test_client_cannot_view_another_tenants_case_detail(client_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    client_identity = make_identity(db, "client@multi.com")
    make_membership(db, client_identity.id, tenant_a.id, UserRole.CLIENT)
    client_b_membership = make_membership(db, client_identity.id, tenant_b.id, UserRole.CLIENT)
    case_b = make_case(db, tenant_b.id, "Globex Case")
    make_assignment(db, tenant_b.id, case_b.id, client_b_membership.id)
    headers, cookies = auth_for(client_identity, "acme")

    resp = client_client.get(f"/cases/{case_b.id}", headers=headers, cookies=cookies)

    assert resp.status_code == 404
