from datetime import date

from conftest import auth_for, make_assignment, make_case, make_identity, make_membership, make_tenant, make_work_log
from shared.models import Narrative
from shared.models.enums import NarrativeLanguage, UserRole


def _lawyer_on_case(db, tenant, case):
    identity = make_identity(db, "lawyer@acme.com", "Lior Lawyer")
    membership = make_membership(db, identity.id, tenant.id, UserRole.LAWYER)
    make_assignment(db, tenant.id, case.id, membership.id)
    return identity, membership


def _client_on_case(db, tenant, case):
    identity = make_identity(db, "client@acme.com", "Dana Client")
    membership = make_membership(db, identity.id, tenant.id, UserRole.CLIENT)
    make_assignment(db, tenant.id, case.id, membership.id)
    return identity, membership


def test_assigned_lawyer_can_list_narratives(client_client, db):
    """Read-only from client/'s side now (CLAUDE.md's Narratives note:
    generation/export moved to office_manager-only in admin_api) — an
    assigned lawyer can still see what will be billed for their own logged
    hours, just not create or export a narrative.
    """
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, lawyer_membership = _lawyer_on_case(db, tenant, case)
    make_work_log(db, tenant.id, case.id, lawyer_membership.id, hours="3.0")
    db.add(
        Narrative(
            tenant_id=tenant.id,
            case_id=case.id,
            generated_text="A narrative",
            total_hours="3.00",
            total_fee="1350.00",
            language=NarrativeLanguage.HE,
            period_start=date(2000, 1, 1),
            period_end=date(2100, 1, 1),
        )
    )
    db.commit()
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.get(f"/cases/{case.id}/narratives", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_unassigned_lawyer_cannot_list_narratives(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    identity = make_identity(db, "outsider@acme.com")
    make_membership(db, identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(identity, "acme")

    resp = client_client.get(f"/cases/{case.id}/narratives", headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_client_cannot_list_narratives(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    client_identity, _ = _client_on_case(db, tenant, case)
    headers, cookies = auth_for(client_identity, "acme")

    resp = client_client.get(f"/cases/{case.id}/narratives", headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_lawyer_can_no_longer_generate_narrative(client_client, db):
    """Generation moved to admin_api entirely — client_api's narratives
    router only registers GET on this path now, so a POST 405s (the path
    itself still exists for GET, just not this method).
    """
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, _ = _lawyer_on_case(db, tenant, case)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.post(
        f"/cases/{case.id}/narratives",
        json={"period_start": "2000-01-01", "period_end": "2100-01-01"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 405


def test_lawyer_can_no_longer_export_narrative_pdf(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, _ = _lawyer_on_case(db, tenant, case)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.post(f"/cases/{case.id}/narratives/1/export-pdf", headers=headers, cookies=cookies)

    assert resp.status_code == 404
