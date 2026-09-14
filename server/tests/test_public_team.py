from conftest import make_identity, make_membership, make_tenant
from shared.models.enums import UserRole


def _set_public(db, membership, visible=True, years=None, bio=None, photo_url=None):
    membership.show_on_public_page = visible
    identity = membership.identity
    identity.years_of_experience = years
    identity.bio = bio
    identity.photo_url = photo_url
    db.commit()


def test_public_profile_includes_visible_team_sorted(client_client, db):
    tenant = make_tenant(db, "acme", name="Acme Law")

    manager_identity = make_identity(db, "manager@acme.com", name="Manager Person")
    manager = make_membership(db, manager_identity.id, tenant.id, UserRole.OFFICE_MANAGER)
    _set_public(db, manager, visible=True, years=10)

    senior_identity = make_identity(db, "senior@acme.com", name="Senior Lawyer")
    senior = make_membership(db, senior_identity.id, tenant.id, UserRole.LAWYER)
    _set_public(db, senior, visible=True, years=20)

    junior_identity = make_identity(db, "junior@acme.com", name="Junior Lawyer")
    junior = make_membership(db, junior_identity.id, tenant.id, UserRole.LAWYER)
    _set_public(db, junior, visible=True, years=2)

    resp = client_client.get("/public/profile", headers={"Host": "acme.lvh.me"})

    assert resp.status_code == 200
    names = [member["name"] for member in resp.json()["team"]]
    # office_manager first, then lawyers most-experienced-first.
    assert names == ["Manager Person", "Senior Lawyer", "Junior Lawyer"]


def test_public_profile_excludes_clients_and_hidden_and_inactive(client_client, db):
    tenant = make_tenant(db, "acme")

    client_identity = make_identity(db, "client@acme.com", name="A Client")
    client_membership = make_membership(db, client_identity.id, tenant.id, UserRole.CLIENT)
    _set_public(db, client_membership, visible=True, years=5)

    hidden_identity = make_identity(db, "hidden@acme.com", name="Hidden Lawyer")
    hidden = make_membership(db, hidden_identity.id, tenant.id, UserRole.LAWYER)
    _set_public(db, hidden, visible=False, years=5)

    inactive_identity = make_identity(db, "inactive@acme.com", name="Inactive Lawyer")
    inactive = make_membership(db, inactive_identity.id, tenant.id, UserRole.LAWYER)
    _set_public(db, inactive, visible=True, years=5)
    inactive.active = False
    db.commit()

    resp = client_client.get("/public/profile", headers={"Host": "acme.lvh.me"})

    assert resp.json()["team"] == []


def test_public_profile_has_logo_flag_and_logo_endpoint(client_client, db):
    tenant = make_tenant(db, "acme")

    no_logo_resp = client_client.get("/public/profile", headers={"Host": "acme.lvh.me"})
    assert no_logo_resp.json()["has_logo"] is False

    logo_404 = client_client.get("/public/logo", headers={"Host": "acme.lvh.me"})
    assert logo_404.status_code == 404

    tenant.logo_url = "logos/999/doesnotmatterfortest.png"
    db.commit()
    with_logo_resp = client_client.get("/public/profile", headers={"Host": "acme.lvh.me"})
    assert with_logo_resp.json()["has_logo"] is True
