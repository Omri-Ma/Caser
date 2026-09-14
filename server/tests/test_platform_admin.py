from conftest import (
    auth_for,
    make_assignment,
    make_case,
    make_identity,
    make_membership,
    make_tenant,
)
from shared.models.enums import UserRole


def test_platform_login_requires_platform_host(admin_client, db):
    make_identity(db, "root@caser.com", is_super_admin=True)

    resp = admin_client.post(
        "/auth/platform-login",
        json={"email": "root@caser.com", "password": "password123"},
        headers={"Host": "acme.lvh.me"},
    )

    assert resp.status_code == 400


def test_platform_login_rejects_non_super_admin(admin_client, db):
    make_identity(db, "manager@acme.com")

    resp = admin_client.post(
        "/auth/platform-login",
        json={"email": "manager@acme.com", "password": "password123"},
        headers={"Host": "platform.lvh.me"},
    )

    assert resp.status_code == 401


def test_office_manager_cannot_reach_platform_routes(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.get("/platform/tenants", headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_platform_tenant_list_reports_cross_tenant_stats(admin_client, db):
    super_admin = make_identity(db, "root@caser.com", is_super_admin=True)
    headers, cookies = auth_for(super_admin, "platform")

    tenant_a = make_tenant(db, "acme", name="Acme Law")
    tenant_b = make_tenant(db, "globex", name="Globex Legal", active=False)

    lawyer = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer.id, tenant_a.id, UserRole.LAWYER)
    case = make_case(db, tenant_a.id, "Acme v. Roe")
    make_assignment(db, tenant_a.id, case.id, lawyer_membership.id)

    resp = admin_client.get("/platform/tenants", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    by_subdomain = {row["subdomain"]: row for row in body["items"]}

    assert by_subdomain["acme"]["active"] is True
    assert by_subdomain["acme"]["lawyer_count"] == 1
    assert by_subdomain["acme"]["case_count"] == 1
    assert by_subdomain["acme"]["plan"] == "free"

    # Suspended tenants still show up (a super_admin has to see them to
    # reactivate them) — the active=True filter get_current_tenant applies
    # deliberately does not apply here.
    assert by_subdomain["globex"]["active"] is False
    assert tenant_b.subdomain in by_subdomain


def test_suspend_and_reactivate_tenant(admin_client, db):
    super_admin = make_identity(db, "root@caser.com", is_super_admin=True)
    headers, cookies = auth_for(super_admin, "platform")
    tenant = make_tenant(db, "acme")

    suspend_resp = admin_client.post(f"/platform/tenants/{tenant.id}/suspend", headers=headers, cookies=cookies)
    assert suspend_resp.status_code == 200
    assert suspend_resp.json()["active"] is False

    reactivate_resp = admin_client.post(f"/platform/tenants/{tenant.id}/reactivate", headers=headers, cookies=cookies)
    assert reactivate_resp.status_code == 200
    assert reactivate_resp.json()["active"] is True


def test_suspending_tenant_locks_out_its_office_manager(admin_client, db):
    super_admin = make_identity(db, "root@caser.com", is_super_admin=True)
    platform_headers, platform_cookies = auth_for(super_admin, "platform")

    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    manager_headers, manager_cookies = auth_for(manager, "acme")

    # Works before suspension.
    ok_resp = admin_client.get("/tenant", headers=manager_headers, cookies=manager_cookies)
    assert ok_resp.status_code == 200

    admin_client.post(f"/platform/tenants/{tenant.id}/suspend", headers=platform_headers, cookies=platform_cookies)

    locked_resp = admin_client.get("/tenant", headers=manager_headers, cookies=manager_cookies)
    assert locked_resp.status_code == 404


def test_platform_stats_are_aggregate_across_tenants(admin_client, db):
    super_admin = make_identity(db, "root@caser.com", is_super_admin=True)
    headers, cookies = auth_for(super_admin, "platform")

    tenant_a = make_tenant(db, "acme")
    make_tenant(db, "globex", active=False)

    lawyer = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer.id, tenant_a.id, UserRole.LAWYER)
    make_case(db, tenant_a.id, "Case One")
    make_case(db, tenant_a.id, "Case Two")

    resp = admin_client.get("/platform/stats", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_tenants"] == 2
    assert body["active_tenants"] == 1
    assert body["total_lawyers"] == 1
    assert body["total_cases"] == 2
    assert lawyer_membership.role == UserRole.LAWYER


def test_platform_routes_never_expose_case_or_document_paths(admin_client, db):
    """super_admin gets firm-level/aggregate data only — confirm there is no
    platform-namespaced route that returns case or document content
    (CLAUDE.md's Roles boundary: "never case or document content").
    """
    openapi = admin_client.get("/openapi.json").json()
    platform_paths = [path for path in openapi["paths"] if path.startswith("/platform")]

    assert platform_paths, "expected platform routes to be registered"
    for path in platform_paths:
        assert "document" not in path.lower()
        assert "/cases" not in path.lower()
