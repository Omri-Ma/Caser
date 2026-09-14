from conftest import auth_for, make_assignment, make_case, make_identity, make_membership, make_tenant, make_work_log
from shared.models import AuditLog, Document, Narrative
from shared.models.enums import UserRole

# A wide period so a work log created with today's date (make_work_log's
# default) always falls inside it — most of these tests care about
# generation mechanics, not period filtering specifically (see
# test_narrative_period_and_language.py for that).
DEFAULT_PERIOD = {"period_start": "2000-01-01", "period_end": "2100-01-01"}


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


def test_lawyer_generates_narrative_from_work_logs(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, lawyer_membership = _lawyer_on_case(db, tenant, case)
    make_work_log(db, tenant.id, case.id, lawyer_membership.id, hours="3.5")
    make_work_log(db, tenant.id, case.id, lawyer_membership.id, hours="1.5")
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)

    assert resp.status_code == 201
    body = resp.json()
    assert body["total_hours"] == "5.00"
    assert body["total_fee"] == "2250.00"  # 5 hours * 450/hr
    assert str(case.id) in body["generated_text"] or case.title in body["generated_text"]


def test_client_cannot_generate_narrative(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    client_identity, _ = _client_on_case(db, tenant, case)
    headers, cookies = auth_for(client_identity, "acme")

    resp = client_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_generate_rejects_unassigned_lawyer(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    identity = make_identity(db, "outsider@acme.com")
    make_membership(db, identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(identity, "acme")

    resp = client_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_generating_twice_keeps_both_rows_newest_first(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, lawyer_membership = _lawyer_on_case(db, tenant, case)
    make_work_log(db, tenant.id, case.id, lawyer_membership.id, hours="2")
    headers, cookies = auth_for(lawyer_identity, "acme")

    first = client_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)
    make_work_log(db, tenant.id, case.id, lawyer_membership.id, hours="1")
    second = client_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)

    assert first.json()["total_hours"] == "2.00"
    assert second.json()["total_hours"] == "3.00"
    assert first.json()["id"] != second.json()["id"]

    listing = client_client.get(f"/cases/{case.id}/narratives", headers=headers, cookies=cookies)
    items = listing.json()["items"]
    assert listing.json()["total"] == 2
    assert items[0]["id"] == second.json()["id"]  # newest first
    assert items[1]["id"] == first.json()["id"]

    assert db.query(Narrative).count() == 2


def test_client_cannot_list_narratives(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    client_identity, _ = _client_on_case(db, tenant, case)
    headers, cookies = auth_for(client_identity, "acme")

    resp = client_client.get(f"/cases/{case.id}/narratives", headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_export_pdf_creates_internal_document_and_audit_log(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, lawyer_membership = _lawyer_on_case(db, tenant, case)
    make_work_log(db, tenant.id, case.id, lawyer_membership.id, hours="4")
    headers, cookies = auth_for(lawyer_identity, "acme")

    narrative_resp = client_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)
    narrative_id = narrative_resp.json()["id"]

    export_resp = client_client.post(
        f"/cases/{case.id}/narratives/{narrative_id}/export-pdf", headers=headers, cookies=cookies
    )

    assert export_resp.status_code == 201
    body = export_resp.json()
    assert body["folder_type"] == "internal"
    assert body["content_type"] == "application/pdf"
    assert body["original_filename"] == f"narrative-{narrative_id}.pdf"

    document = db.query(Document).filter(Document.id == body["id"]).first()
    assert document is not None
    assert document.case_id == case.id
    assert document.tenant_id == tenant.id

    log = db.query(AuditLog).filter(AuditLog.action == "narrative_pdf_exported").first()
    assert log is not None
    assert log.tenant_id == tenant.id


def test_export_pdf_rejects_narrative_from_other_case(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    other_case = make_case(db, tenant.id, title="Other Case")
    lawyer_identity, lawyer_membership = _lawyer_on_case(db, tenant, case)
    make_assignment(db, tenant.id, other_case.id, lawyer_membership.id)
    headers, cookies = auth_for(lawyer_identity, "acme")

    other_narrative = client_client.post(f"/cases/{other_case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)
    other_narrative_id = other_narrative.json()["id"]

    resp = client_client.post(
        f"/cases/{case.id}/narratives/{other_narrative_id}/export-pdf", headers=headers, cookies=cookies
    )

    assert resp.status_code == 404


def test_client_cannot_export_pdf(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, lawyer_membership = _lawyer_on_case(db, tenant, case)
    make_work_log(db, tenant.id, case.id, lawyer_membership.id, hours="1")
    client_identity, _ = _client_on_case(db, tenant, case)

    lawyer_headers, lawyer_cookies = auth_for(lawyer_identity, "acme")
    narrative_resp = client_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=lawyer_headers, cookies=lawyer_cookies)
    narrative_id = narrative_resp.json()["id"]

    client_headers, client_cookies = auth_for(client_identity, "acme")
    resp = client_client.post(
        f"/cases/{case.id}/narratives/{narrative_id}/export-pdf", headers=client_headers, cookies=client_cookies
    )

    assert resp.status_code == 403


def test_reclassifying_exported_narrative_makes_it_client_visible(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, lawyer_membership = _lawyer_on_case(db, tenant, case)
    make_work_log(db, tenant.id, case.id, lawyer_membership.id, hours="2")
    client_identity, _ = _client_on_case(db, tenant, case)
    headers, cookies = auth_for(lawyer_identity, "acme")

    narrative_resp = client_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)
    narrative_id = narrative_resp.json()["id"]
    export_resp = client_client.post(
        f"/cases/{case.id}/narratives/{narrative_id}/export-pdf", headers=headers, cookies=cookies
    )
    document_id = export_resp.json()["id"]

    client_headers, client_cookies = auth_for(client_identity, "acme")
    before = client_client.get(f"/cases/{case.id}/documents", headers=client_headers, cookies=client_cookies)
    assert before.json()["total"] == 0

    reclassify = client_client.patch(
        f"/cases/{case.id}/documents/{document_id}",
        json={"folder_type": "client"},
        headers=headers,
        cookies=cookies,
    )
    assert reclassify.status_code == 200

    after = client_client.get(f"/cases/{case.id}/documents", headers=client_headers, cookies=client_cookies)
    assert after.json()["total"] == 1
    assert after.json()["items"][0]["id"] == document_id
