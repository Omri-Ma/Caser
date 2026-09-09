import csv
import io
from datetime import date

from conftest import auth_for, make_case, make_document, make_identity, make_membership, make_tenant
from shared.models import Subscription
from shared.models.enums import CaseStatus, UserRole


def test_dashboard_stats_scoped_to_own_tenant(admin_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    make_case(db, tenant_a.id, "Acme Case One", status=CaseStatus.OPEN)
    make_case(db, tenant_a.id, "Acme Case Two", status=CaseStatus.CLOSED)
    lawyer = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer.id, tenant_a.id, UserRole.LAWYER)
    client_identity = make_identity(db, "client@acme.com")
    make_membership(db, client_identity.id, tenant_a.id, UserRole.CLIENT)

    # Other tenant's data must never leak into acme's numbers.
    make_case(db, tenant_b.id, "Globex Case", status=CaseStatus.OPEN)
    other_lawyer = make_identity(db, "lawyer@globex.com")
    make_membership(db, other_lawyer.id, tenant_b.id, UserRole.LAWYER)

    resp = admin_client.get("/dashboard/stats", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_case_count"] == 2
    assert body["closed_case_count"] == 1
    assert body["active_case_count"] == 1
    assert body["lawyer_count"] == 1
    assert body["client_count"] == 1
    assert body["plan"] == "free"
    assert len(body["monthly_case_activity"]) == 6
    current_month = date.today().strftime("%Y-%m")
    current_point = next(p for p in body["monthly_case_activity"] if p["month"] == current_month)
    assert current_point["new_cases"] == 2


def test_dashboard_stats_reflects_storage_usage(admin_client, db):
    tenant = make_tenant(db, "acme")
    subscription = Subscription(tenant_id=tenant.id, plan="FREE", start_date=date.today(), active=True)
    db.add(subscription)
    db.commit()
    manager = make_identity(db, "manager@acme.com")
    manager_membership = make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    case = make_case(db, tenant.id, "Case One")
    make_document(db, tenant.id, case.id, manager_membership.id, file_size=2048)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.get("/dashboard/stats", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    assert body["storage_used_bytes"] == 2048
    assert body["storage_limit_bytes"] == 1024**3


def test_lawyer_cannot_view_dashboard_stats(admin_client, db):
    tenant = make_tenant(db, "acme")
    lawyer = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(lawyer, "acme")

    resp = admin_client.get("/dashboard/stats", headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_export_cases_returns_csv_scoped_to_own_tenant(admin_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    make_case(db, tenant_a.id, "Acme Case", status=CaseStatus.OPEN)
    make_case(db, tenant_b.id, "Globex Case", status=CaseStatus.OPEN)

    resp = admin_client.get("/dashboard/export?resource=cases", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "acme-cases.csv" in resp.headers["content-disposition"]

    rows = list(csv.reader(io.StringIO(resp.text)))
    assert rows[0] == ["id", "title", "status", "created_at"]
    titles = [row[1] for row in rows[1:]]
    assert titles == ["Acme Case"]


def test_export_members_returns_csv_scoped_to_own_tenant(admin_client, db):
    tenant_a = make_tenant(db, "acme")
    tenant_b = make_tenant(db, "globex")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant_a.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    lawyer = make_identity(db, "lawyer@acme.com", name="Acme Lawyer")
    make_membership(db, lawyer.id, tenant_a.id, UserRole.LAWYER)
    other_lawyer = make_identity(db, "lawyer@globex.com", name="Globex Lawyer")
    make_membership(db, other_lawyer.id, tenant_b.id, UserRole.LAWYER)

    resp = admin_client.get("/dashboard/export?resource=members", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    rows = list(csv.reader(io.StringIO(resp.text)))
    assert rows[0] == ["id", "name", "email", "role", "active"]
    names = {row[1] for row in rows[1:]}
    assert names == {"Test User", "Acme Lawyer"}


def test_export_rejects_unknown_resource(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.get("/dashboard/export?resource=documents", headers=headers, cookies=cookies)

    assert resp.status_code == 422


def test_lawyer_cannot_export_data(admin_client, db):
    tenant = make_tenant(db, "acme")
    lawyer = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(lawyer, "acme")

    resp = admin_client.get("/dashboard/export?resource=cases", headers=headers, cookies=cookies)

    assert resp.status_code == 403
