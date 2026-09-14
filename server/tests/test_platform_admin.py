from datetime import date, datetime, timedelta, timezone

from conftest import (
    auth_for,
    make_assignment,
    make_case,
    make_document,
    make_identity,
    make_membership,
    make_tenant,
)
from shared.models import PlatformAuditLog, Subscription
from shared.models.enums import Plan, UserRole


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


def test_suspend_and_reactivate_write_platform_audit_log(admin_client, db):
    super_admin = make_identity(db, "root@caser.com", is_super_admin=True)
    headers, cookies = auth_for(super_admin, "platform")
    tenant = make_tenant(db, "acme")

    admin_client.post(f"/platform/tenants/{tenant.id}/suspend", headers=headers, cookies=cookies)
    admin_client.post(f"/platform/tenants/{tenant.id}/reactivate", headers=headers, cookies=cookies)

    logs = db.query(PlatformAuditLog).filter(PlatformAuditLog.target_tenant_id == tenant.id).order_by(PlatformAuditLog.id).all()
    assert [log.action for log in logs] == ["tenant_suspended", "tenant_reactivated"]
    assert all(log.identity_id == super_admin.id for log in logs)

    resp = admin_client.get("/platform/audit-log", headers=headers, cookies=cookies)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["items"][0]["action"] == "tenant_reactivated"  # newest first
    assert body["items"][0]["target_tenant_name"] == tenant.name
    assert body["items"][0]["actor_email"] == "root@caser.com"


def test_platform_stats_include_clients_storage_and_plan_distribution(admin_client, db):
    super_admin = make_identity(db, "root@caser.com", is_super_admin=True)
    headers, cookies = auth_for(super_admin, "platform")

    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    db.add(Subscription(tenant_id=tenant_b.id, plan=Plan.PRO, start_date=date.today(), active=True))
    db.commit()

    client_identity = make_identity(db, "client@acme.com")
    client_membership = make_membership(db, client_identity.id, tenant_a.id, UserRole.CLIENT)
    case = make_case(db, tenant_a.id, "Case One")
    make_document(db, tenant_a.id, case.id, client_membership.id, file_size=2048)

    resp = admin_client.get("/platform/stats", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_clients"] == 1
    assert body["total_storage_bytes"] == 2048
    distribution = {entry["plan"]: entry["tenant_count"] for entry in body["plan_distribution"]}
    assert distribution["pro"] == 1
    assert distribution["free"] == 1  # tenant_a has no active Subscription row -> falls back to Free


def test_tenant_growth_counts_tenants_created_this_month(admin_client, db):
    super_admin = make_identity(db, "root@caser.com", is_super_admin=True)
    headers, cookies = auth_for(super_admin, "platform")
    make_tenant(db, "acme")
    make_tenant(db, "globex")

    resp = admin_client.get("/platform/tenant-growth", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    points = resp.json()
    assert len(points) == 6
    this_month = f"{date.today():%Y-%m}"
    current = next(p for p in points if p["month"] == this_month)
    assert current["new_tenants"] == 2


def test_platform_earnings_sums_active_subscription_prices(admin_client, db):
    super_admin = make_identity(db, "root@caser.com", is_super_admin=True)
    headers, cookies = auth_for(super_admin, "platform")
    tenant = make_tenant(db, "acme")
    db.add(Subscription(tenant_id=tenant.id, plan=Plan.PRO, start_date=date.today(), active=True))
    db.commit()

    resp = admin_client.get("/platform/earnings", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    assert body["current_month_earnings_ils"] == 99  # PLAN_PRICES_ILS[Plan.PRO]
    assert len(body["trend"]) == 6


def test_storage_overview_reports_usage_against_plan_quota(admin_client, db):
    super_admin = make_identity(db, "root@caser.com", is_super_admin=True)
    headers, cookies = auth_for(super_admin, "platform")
    tenant = make_tenant(db, "acme")
    lawyer = make_identity(db, "lawyer@acme.com")
    lawyer_membership = make_membership(db, lawyer.id, tenant.id, UserRole.LAWYER)
    case = make_case(db, tenant.id, "Case One")
    make_document(db, tenant.id, case.id, lawyer_membership.id, file_size=5_000_000)

    resp = admin_client.get("/platform/storage-overview", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    entry = next(e for e in body if e["subdomain"] == "acme")
    assert entry["storage_used_bytes"] == 5_000_000
    assert entry["storage_limit_bytes"] == 1024**3  # Free plan default


def test_platform_users_view_reports_memberships_and_last_login(admin_client, db):
    super_admin = make_identity(db, "root@caser.com", is_super_admin=True)
    headers, cookies = auth_for(super_admin, "platform")

    tenant_a = make_tenant(db, "acme", name="Acme Law")
    tenant_b = make_tenant(db, "beta", name="Beta Legal")
    lawyer = make_identity(db, "multi@acme.com", "Multi Firm Lawyer")
    make_membership(db, lawyer.id, tenant_a.id, UserRole.LAWYER)
    make_membership(db, lawyer.id, tenant_b.id, UserRole.LAWYER)

    resp = admin_client.get("/platform/users", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    row = next(u for u in body["items"] if u["email"] == "multi@acme.com")
    assert row["last_login_at"] is None
    firm_names = {m["tenant_name"] for m in row["memberships"]}
    assert firm_names == {"Acme Law", "Beta Legal"}

    # super_admin itself never shows up in this list (CLAUDE.md: never a
    # Memberships row, and this view is about firm-level accounts).
    assert not any(u["email"] == "root@caser.com" for u in body["items"])


def test_platform_users_view_search_filters_by_name_or_email(admin_client, db):
    super_admin = make_identity(db, "root@caser.com", is_super_admin=True)
    headers, cookies = auth_for(super_admin, "platform")
    tenant = make_tenant(db, "acme")
    make_identity(db, "findme@acme.com", "Findable Person")
    make_identity(db, "someoneelse@acme.com", "Someone Else")

    resp = admin_client.get("/platform/users", params={"search": "findme"}, headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "findme@acme.com"


def test_platform_tenant_list_search_filters_by_name_or_subdomain(admin_client, db):
    super_admin = make_identity(db, "root@caser.com", is_super_admin=True)
    headers, cookies = auth_for(super_admin, "platform")
    make_tenant(db, "acme", name="Acme Law")
    make_tenant(db, "globex", name="Globex Legal")

    resp = admin_client.get("/platform/tenants", params={"search": "acme"}, headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["subdomain"] == "acme"

    # Matches on subdomain too, not just the display name.
    resp = admin_client.get("/platform/tenants", params={"search": "globex"}, headers=headers, cookies=cookies)
    assert resp.json()["total"] == 1


def test_platform_users_view_sortable_by_last_login(admin_client, db):
    """CLAUDE.md's super_admin cross-tenant users view — sortable by
    last_login_at so the platform team can find the most/least recently
    active accounts. MySQL has no NULLS FIRST/LAST syntax, so this also
    guards the never-logged-in (NULL) case: they must sort to the end
    regardless of direction, not crash the query or flip to the front.
    """
    super_admin = make_identity(db, "root@caser.com", is_super_admin=True)
    headers, cookies = auth_for(super_admin, "platform")

    older = make_identity(db, "older@acme.com", "Older Login")
    newer = make_identity(db, "newer@acme.com", "Newer Login")
    never = make_identity(db, "never@acme.com", "Never Logged In")
    older.last_login_at = datetime.now(timezone.utc) - timedelta(days=10)
    newer.last_login_at = datetime.now(timezone.utc) - timedelta(days=1)
    db.commit()

    resp = admin_client.get(
        "/platform/users", params={"sort": "last_login_at", "order": "asc"}, headers=headers, cookies=cookies
    )
    assert resp.status_code == 200
    emails = [row["email"] for row in resp.json()["items"]]
    assert emails.index(older.email) < emails.index(newer.email) < emails.index(never.email)

    resp = admin_client.get(
        "/platform/users", params={"sort": "last_login_at", "order": "desc"}, headers=headers, cookies=cookies
    )
    assert resp.status_code == 200
    emails = [row["email"] for row in resp.json()["items"]]
    # Descending: most recent login first, but NULLs still trail rather than
    # jumping to the front just because the direction flipped.
    assert emails.index(newer.email) < emails.index(older.email) < emails.index(never.email)


def test_lawyer_cannot_reach_new_platform_routes(admin_client, db):
    tenant = make_tenant(db, "acme")
    lawyer = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(lawyer, "acme")

    for path in ("/platform/users", "/platform/earnings", "/platform/tenant-growth", "/platform/storage-overview", "/platform/audit-log"):
        resp = admin_client.get(path, headers=headers, cookies=cookies)
        assert resp.status_code == 403, path


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
