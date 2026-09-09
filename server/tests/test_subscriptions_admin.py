from datetime import date

from conftest import auth_for, make_identity, make_membership, make_tenant
from shared.models import Subscription
from shared.models.enums import UserRole


def _seed_free_subscription(db, tenant_id):
    subscription = Subscription(tenant_id=tenant_id, plan="FREE", start_date=date.today(), active=True)
    db.add(subscription)
    db.commit()
    return subscription


def test_get_subscription_returns_plan_and_usage(admin_client, db):
    tenant = make_tenant(db, "acme")
    _seed_free_subscription(db, tenant.id)
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.get("/subscription", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "free"
    assert body["lawyer_count"] == 1
    assert body["lawyer_limit"] == 3
    assert body["storage_used_bytes"] == 0
    assert body["storage_limit_bytes"] == 1024**3


def test_subscription_defaults_to_free_with_no_active_row(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.get("/subscription", headers=headers, cookies=cookies)

    assert resp.json()["plan"] == "free"


def test_switch_plan_deactivates_old_row_and_activates_new(admin_client, db):
    tenant = make_tenant(db, "acme")
    _seed_free_subscription(db, tenant.id)
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.post("/subscription/plan", json={"plan": "pro"}, headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "pro"
    assert body["lawyer_limit"] == 15

    rows = db.query(Subscription).filter(Subscription.tenant_id == tenant.id).all()
    assert len(rows) == 2
    active_rows = [r for r in rows if r.active]
    assert len(active_rows) == 1
    assert active_rows[0].plan.value == "pro"


def test_switch_plan_rejects_same_plan(admin_client, db):
    tenant = make_tenant(db, "acme")
    _seed_free_subscription(db, tenant.id)
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.post("/subscription/plan", json={"plan": "free"}, headers=headers, cookies=cookies)

    assert resp.status_code == 400


def test_downgrade_does_not_remove_existing_lawyers(admin_client, db):
    tenant = make_tenant(db, "acme")
    subscription = Subscription(tenant_id=tenant.id, plan="PRO", start_date=date.today(), active=True)
    db.add(subscription)
    db.commit()
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    for i in range(5):
        identity = make_identity(db, f"lawyer{i}@acme.com")
        make_membership(db, identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(manager, "acme")

    resp = admin_client.post("/subscription/plan", json={"plan": "free"}, headers=headers, cookies=cookies)

    assert resp.status_code == 200
    body = resp.json()
    assert body["lawyer_count"] == 5  # all 5 kept, even though Free's limit is 3
    assert body["lawyer_limit"] == 3


def test_lawyer_cannot_view_subscription(admin_client, db):
    tenant = make_tenant(db, "acme")
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = admin_client.get("/subscription", headers=headers, cookies=cookies)

    assert resp.status_code == 403
