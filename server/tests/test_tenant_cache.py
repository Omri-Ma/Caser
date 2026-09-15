"""Redis-backed tenant cache (CLAUDE.md's Tech stack / Cache section) —
get_current_tenant's first real use of Redis. Two things to prove per
CLAUDE.md: a second lookup for the same subdomain is genuinely served from
cache (not a second MySQL query), and updating/suspending a tenant is
reflected on the very next request, not after the TTL.
"""

from sqlalchemy import text

from conftest import auth_for, make_identity, make_membership, make_tenant
from shared.cache import get_cached_tenant
from shared.models.enums import UserRole


def test_first_request_populates_the_cache(admin_client, db):
    tenant = make_tenant(db, "acme", name="Acme Law")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    assert get_cached_tenant("acme") is None  # nothing cached yet

    resp = admin_client.get("/tenant", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    cached = get_cached_tenant("acme")
    assert cached is not None
    assert cached["id"] == tenant.id
    assert cached["name"] == "Acme Law"


def test_second_request_is_served_from_cache_not_the_database(admin_client, db):
    """Mutates the row directly in the database, bypassing the app (and
    therefore bypassing invalidate_tenant_cache entirely). If the second
    request still queried MySQL on every call, it would see the new name —
    the only way it can still return the old one is if it came from Redis.
    """
    tenant = make_tenant(db, "acme", name="Acme Law")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    first = admin_client.get("/tenant", headers=headers, cookies=cookies)
    assert first.json()["name"] == "Acme Law"

    db.execute(text("UPDATE tenants SET name = :name WHERE id = :id"), {"name": "Mutated Behind The Cache", "id": tenant.id})
    db.commit()

    second = admin_client.get("/tenant", headers=headers, cookies=cookies)

    assert second.status_code == 200
    assert second.json()["name"] == "Acme Law"


def test_branding_update_invalidates_cache_so_next_request_sees_it_immediately(admin_client, db):
    tenant = make_tenant(db, "acme", name="Acme Law")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    admin_client.get("/tenant", headers=headers, cookies=cookies)
    assert get_cached_tenant("acme") is not None

    update_resp = admin_client.patch(
        "/tenant",
        json={"name": "Acme & Partners", "primary_color": "#112233"},
        headers=headers,
        cookies=cookies,
    )
    assert update_resp.status_code == 200

    # Invalidated as part of the update itself, before any further request.
    assert get_cached_tenant("acme") is None

    follow_up = admin_client.get("/tenant", headers=headers, cookies=cookies)
    assert follow_up.json()["name"] == "Acme & Partners"
    # And the fresh value is what's now cached, not the stale one.
    assert get_cached_tenant("acme")["name"] == "Acme & Partners"


def test_logo_upload_invalidates_cache(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    headers, cookies = auth_for(manager, "acme")

    admin_client.get("/tenant", headers=headers, cookies=cookies)
    assert get_cached_tenant("acme") is not None

    png_bytes = b"\x89PNG\r\n\x1a\n" + b"0" * 20
    upload_resp = admin_client.post(
        "/tenant/logo",
        files={"file": ("logo.png", png_bytes, "image/png")},
        headers=headers,
        cookies=cookies,
    )
    assert upload_resp.status_code == 200

    assert get_cached_tenant("acme") is None


def test_suspend_invalidates_cache_and_locks_out_on_the_very_next_request(admin_client, db):
    tenant = make_tenant(db, "acme", name="Acme Law")
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    super_admin = make_identity(db, "root@caser.com", is_super_admin=True)
    manager_headers, manager_cookies = auth_for(manager, "acme")
    platform_headers, platform_cookies = auth_for(super_admin, "platform")

    # Warm the cache as the office manager, same as any normal request would.
    admin_client.get("/tenant", headers=manager_headers, cookies=manager_cookies)
    assert get_cached_tenant("acme") is not None

    suspend_resp = admin_client.post(
        f"/platform/tenants/{tenant.id}/suspend", headers=platform_headers, cookies=platform_cookies
    )
    assert suspend_resp.status_code == 200

    assert get_cached_tenant("acme") is None

    locked_out = admin_client.get("/tenant", headers=manager_headers, cookies=manager_cookies)
    assert locked_out.status_code == 404


def test_reactivate_invalidates_cache_and_restores_access_on_the_very_next_request(admin_client, db):
    tenant = make_tenant(db, "acme", name="Acme Law", active=False)
    manager = make_identity(db, "manager@acme.com")
    make_membership(db, manager.id, tenant.id, UserRole.OFFICE_MANAGER)
    super_admin = make_identity(db, "root@caser.com", is_super_admin=True)
    manager_headers, manager_cookies = auth_for(manager, "acme")
    platform_headers, platform_cookies = auth_for(super_admin, "platform")

    # Suspended tenants 404 straight from the database (never cached, since
    # get_current_tenant's own query never even finds them), so there's
    # nothing cached yet to prove staleness against here — the point of this
    # test is only that reactivating unlocks it immediately.
    still_locked = admin_client.get("/tenant", headers=manager_headers, cookies=manager_cookies)
    assert still_locked.status_code == 404

    reactivate_resp = admin_client.post(
        f"/platform/tenants/{tenant.id}/reactivate", headers=platform_headers, cookies=platform_cookies
    )
    assert reactivate_resp.status_code == 200

    restored = admin_client.get("/tenant", headers=manager_headers, cookies=manager_cookies)
    assert restored.status_code == 200
    assert restored.json()["name"] == "Acme Law"
