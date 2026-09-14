from conftest import make_tenant


def test_public_directory_lists_active_tenants_name_and_subdomain(client_client, db):
    make_tenant(db, "acme", name="Acme Law")
    make_tenant(db, "beta", name="Beta Legal")

    resp = client_client.get("/public/directory")

    assert resp.status_code == 200
    body = resp.json()
    subdomains = {item["subdomain"] for item in body["items"]}
    assert subdomains == {"acme", "beta"}
    # Whitelisted fields only — no sensitive tenant data leaks through.
    for item in body["items"]:
        assert set(item.keys()) == {"name", "subdomain", "has_logo"}


def test_public_directory_excludes_inactive_tenants(client_client, db):
    make_tenant(db, "acme", name="Acme Law", active=True)
    make_tenant(db, "suspended", name="Suspended Firm", active=False)

    resp = client_client.get("/public/directory")

    subdomains = {item["subdomain"] for item in resp.json()["items"]}
    assert subdomains == {"acme"}


def test_public_directory_is_paginated(client_client, db):
    for i in range(3):
        make_tenant(db, f"firm{i}", name=f"Firm {i}")

    resp = client_client.get("/public/directory?page=1&page_size=2")
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["page_size"] == 2


def test_public_directory_has_logo_flag(client_client, db):
    tenant = make_tenant(db, "acme", name="Acme Law")
    resp = client_client.get("/public/directory")
    assert resp.json()["items"][0]["has_logo"] is False

    tenant.logo_url = "logos/999/x.png"
    db.commit()
    resp = client_client.get("/public/directory")
    assert resp.json()["items"][0]["has_logo"] is True


def test_public_directory_works_from_lobby_host(client_client, db):
    """The whole point of this route: reachable from www (the lobby), which
    has no tenant of its own to resolve — unlike every other public/* route.
    """
    make_tenant(db, "acme", name="Acme Law")
    resp = client_client.get("/public/directory", headers={"Host": "www.lvh.me"})
    assert resp.status_code == 200
