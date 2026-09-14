from datetime import date

from conftest import auth_for, make_assignment, make_case, make_identity, make_membership, make_tenant, make_work_log
from shared.models import AuditLog, Document
from shared.models.enums import UserRole

DEFAULT_PERIOD = {"period_start": "2000-01-01", "period_end": "2100-01-01"}


def _manager(db, tenant):
    identity = make_identity(db, "manager@acme.com", "Noa Manager")
    membership = make_membership(db, identity.id, tenant.id, UserRole.OFFICE_MANAGER)
    return identity, membership


def _lawyer(db, tenant, email="lawyer@acme.com", name="Lior Lawyer", hourly_rate=None):
    identity = make_identity(db, email, name)
    membership = make_membership(db, identity.id, tenant.id, UserRole.LAWYER)
    if hourly_rate is not None:
        membership.hourly_rate = hourly_rate
        db.commit()
    return identity, membership


def test_office_manager_generates_narrative_without_case_assignment(admin_client, db):
    """office_manager sees every case at their tenant automatically (CLAUDE.md's
    oversight authority) — no CaseAssignment row needed, unlike a lawyer.
    """
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, _ = _manager(db, tenant)
    lawyer_identity, lawyer_membership = _lawyer(db, tenant, hourly_rate="450.00")
    make_work_log(db, tenant.id, case.id, lawyer_membership.id, hours="3.5")
    make_work_log(db, tenant.id, case.id, lawyer_membership.id, hours="1.5")
    headers, cookies = auth_for(manager_identity, "acme")

    resp = admin_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)

    assert resp.status_code == 201
    body = resp.json()
    assert body["total_hours"] == "5.00"
    assert body["total_fee"] == "2250.00"  # 5 hours * 450/hr


def test_narrative_fee_uses_each_lawyers_own_hourly_rate(admin_client, db):
    """CLAUDE.md's Memberships note: total_fee now depends on each lawyer's
    real, office_manager-set hourly_rate — not one flat platform-wide rate.
    Two lawyers on the same case at different rates must each be billed at
    their own rate, not averaged or defaulted to one shared number.
    """
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, _ = _manager(db, tenant)
    _, lawyer_a = _lawyer(db, tenant, email="a@acme.com", name="Lawyer A", hourly_rate="400.00")
    _, lawyer_b = _lawyer(db, tenant, email="b@acme.com", name="Lawyer B", hourly_rate="600.00")
    make_work_log(db, tenant.id, case.id, lawyer_a.id, hours="2.0")
    make_work_log(db, tenant.id, case.id, lawyer_b.id, hours="1.0")
    headers, cookies = auth_for(manager_identity, "acme")

    resp = admin_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)

    assert resp.status_code == 201
    body = resp.json()
    assert body["total_hours"] == "3.00"
    # 2h * 400 + 1h * 600 = 1400, not (400+600)/2 * 3 = 1500
    assert body["total_fee"] == "1400.00"


def test_narrative_fee_treats_unset_hourly_rate_as_zero(admin_client, db):
    """A lawyer with no rate set yet (CLAUDE.md: nullable, "no rate set yet")
    contributes 0 for their hours rather than raising an error.
    """
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, _ = _manager(db, tenant)
    _, lawyer_membership = _lawyer(db, tenant, hourly_rate=None)
    make_work_log(db, tenant.id, case.id, lawyer_membership.id, hours="5.0")
    headers, cookies = auth_for(manager_identity, "acme")

    resp = admin_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)

    assert resp.status_code == 201
    body = resp.json()
    assert body["total_hours"] == "5.00"
    assert body["total_fee"] == "0.00"


def test_lawyer_cannot_generate_narrative_via_admin_api(admin_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, lawyer_membership = _lawyer(db, tenant)
    make_assignment(db, tenant.id, case.id, lawyer_membership.id)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = admin_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_office_manager_lists_narratives_newest_first(admin_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, _ = _manager(db, tenant)
    headers, cookies = auth_for(manager_identity, "acme")

    first = admin_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)
    second = admin_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)

    listing = admin_client.get(f"/cases/{case.id}/narratives", headers=headers, cookies=cookies)
    items = listing.json()["items"]
    assert listing.json()["total"] == 2
    assert items[0]["id"] == second.json()["id"]
    assert items[1]["id"] == first.json()["id"]


def test_export_pdf_uses_office_manager_chosen_filename(admin_client, db):
    """CLAUDE.md's Narratives note: office_manager names the exported file
    at export time, rather than it being auto-generated. The .pdf extension
    is enforced regardless of what was typed.
    """
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, _ = _manager(db, tenant)
    _, lawyer_membership = _lawyer(db, tenant, hourly_rate="450.00")
    make_work_log(db, tenant.id, case.id, lawyer_membership.id, hours="4")
    headers, cookies = auth_for(manager_identity, "acme")

    narrative_resp = admin_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)
    narrative_id = narrative_resp.json()["id"]

    export_resp = admin_client.post(
        f"/cases/{case.id}/narratives/{narrative_id}/export-pdf",
        json={"filename": "Client Invoice March"},
        headers=headers,
        cookies=cookies,
    )

    assert export_resp.status_code == 201
    body = export_resp.json()
    assert body["folder_type"] == "internal"
    assert body["content_type"] == "application/pdf"
    assert body["original_filename"] == "Client Invoice March.pdf"

    document = db.query(Document).filter(Document.id == body["id"]).first()
    assert document is not None
    assert document.case_id == case.id

    log = db.query(AuditLog).filter(AuditLog.action == "narrative_pdf_exported").first()
    assert log is not None
    assert log.target == "Client Invoice March.pdf"


def test_export_pdf_filename_already_ending_in_pdf_not_doubled(admin_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, _ = _manager(db, tenant)
    headers, cookies = auth_for(manager_identity, "acme")

    narrative_resp = admin_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)
    narrative_id = narrative_resp.json()["id"]

    export_resp = admin_client.post(
        f"/cases/{case.id}/narratives/{narrative_id}/export-pdf",
        json={"filename": "report.pdf"},
        headers=headers,
        cookies=cookies,
    )

    assert export_resp.json()["original_filename"] == "report.pdf"


def test_export_pdf_includes_itemized_work_log_table(admin_client, db):
    """CLAUDE.md's Narratives note: the PDF export includes an itemized
    table of every WorkLog in the chosen period, not just summary totals.
    Checks the raw PDF bytes contain the work log's description text.
    """
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, _ = _manager(db, tenant)
    _, lawyer_membership = _lawyer(db, tenant, hourly_rate="450.00")
    make_work_log(db, tenant.id, case.id, lawyer_membership.id, hours="4")
    headers, cookies = auth_for(manager_identity, "acme")

    narrative_resp = admin_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)
    narrative_id = narrative_resp.json()["id"]

    export_resp = admin_client.post(
        f"/cases/{case.id}/narratives/{narrative_id}/export-pdf",
        json={"filename": "itemized-test"},
        headers=headers,
        cookies=cookies,
    )
    assert export_resp.status_code == 201

    document = db.query(Document).filter(Document.id == export_resp.json()["id"]).first()
    import pymupdf

    from shared.storage import get_file_url

    pdf_doc = pymupdf.open(get_file_url(document.file_url))
    full_text = "".join(page.get_text() for page in pdf_doc)
    # WorkLog's default description ("Test entry", per conftest.make_work_log)
    # must appear somewhere in the rendered PDF text — this is the itemized
    # table, not just the summary totals already covered above. Reportlab
    # compresses PDF content streams by default, so this has to actually
    # extract text rather than grep the raw bytes.
    assert "Test entry" in full_text


def test_client_cannot_export_pdf_via_admin_api(admin_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, _ = _manager(db, tenant)
    headers, cookies = auth_for(manager_identity, "acme")
    narrative_resp = admin_client.post(f"/cases/{case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)
    narrative_id = narrative_resp.json()["id"]

    client_identity = make_identity(db, "client@acme.com", "Dana Client")
    make_membership(db, client_identity.id, tenant.id, UserRole.CLIENT)
    client_headers, client_cookies = auth_for(client_identity, "acme")

    resp = admin_client.post(
        f"/cases/{case.id}/narratives/{narrative_id}/export-pdf",
        json={"filename": "x"},
        headers=client_headers,
        cookies=client_cookies,
    )

    assert resp.status_code == 403


def test_export_pdf_rejects_narrative_from_other_case(admin_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    other_case = make_case(db, tenant.id, title="Other Case")
    manager_identity, _ = _manager(db, tenant)
    headers, cookies = auth_for(manager_identity, "acme")

    other_narrative = admin_client.post(f"/cases/{other_case.id}/narratives", json=DEFAULT_PERIOD, headers=headers, cookies=cookies)
    other_narrative_id = other_narrative.json()["id"]

    resp = admin_client.post(
        f"/cases/{case.id}/narratives/{other_narrative_id}/export-pdf",
        json={"filename": "x"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 404


def test_hourly_rate_settable_only_for_lawyers(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager_identity, _ = _manager(db, tenant)
    headers, cookies = auth_for(manager_identity, "acme")

    lawyer_identity, lawyer_membership = _lawyer(db, tenant)
    resp = admin_client.patch(
        f"/members/{lawyer_membership.id}/hourly-rate", json={"hourly_rate": "500.00"}, headers=headers, cookies=cookies
    )
    assert resp.status_code == 200
    assert resp.json()["hourly_rate"] == "500.00"

    client_identity = make_identity(db, "client2@acme.com", "Client Two")
    client_membership = make_membership(db, client_identity.id, tenant.id, UserRole.CLIENT)
    resp = admin_client.patch(
        f"/members/{client_membership.id}/hourly-rate", json={"hourly_rate": "500.00"}, headers=headers, cookies=cookies
    )
    assert resp.status_code == 400


def test_hourly_rate_rejects_non_positive_value(admin_client, db):
    tenant = make_tenant(db, "acme")
    manager_identity, _ = _manager(db, tenant)
    headers, cookies = auth_for(manager_identity, "acme")
    _, lawyer_membership = _lawyer(db, tenant)

    resp = admin_client.patch(
        f"/members/{lawyer_membership.id}/hourly-rate", json={"hourly_rate": "0"}, headers=headers, cookies=cookies
    )
    assert resp.status_code == 422


def test_rate_check_flags_unset_and_zero_rate_lawyers_only(admin_client, db):
    """The rate-check endpoint (backs the generate form's warning banner)
    lists only lawyers with a null/zero rate who actually logged hours in
    the chosen period — not every lawyer on the firm, and not a lawyer
    who's properly rated.
    """
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, _ = _manager(db, tenant)
    _, rated = _lawyer(db, tenant, email="rated@acme.com", name="Rated Lawyer", hourly_rate="400.00")
    _, unset = _lawyer(db, tenant, email="unset@acme.com", name="Unset Lawyer", hourly_rate=None)
    _, zero = _lawyer(db, tenant, email="zero@acme.com", name="Zero Lawyer", hourly_rate="0")
    make_work_log(db, tenant.id, case.id, rated.id, hours="1.0")
    make_work_log(db, tenant.id, case.id, unset.id, hours="1.0")
    make_work_log(db, tenant.id, case.id, zero.id, hours="1.0")
    headers, cookies = auth_for(manager_identity, "acme")

    resp = admin_client.get(
        f"/cases/{case.id}/narratives/rate-check",
        params=DEFAULT_PERIOD,
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 200
    names = {row["name"] for row in resp.json()}
    assert names == {"Unset Lawyer", "Zero Lawyer"}


def test_rate_check_includes_removed_lawyers_who_logged_hours(admin_client, db):
    """A lawyer removed from the firm after logging hours still contributes
    those hours (and a fee) to a narrative covering that period — the
    warning has to surface them too, since the normal Lawyers page (active
    members only) no longer would.
    """
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, _ = _manager(db, tenant)
    _, removed = _lawyer(db, tenant, email="removed@acme.com", name="Removed Lawyer", hourly_rate=None)
    make_work_log(db, tenant.id, case.id, removed.id, hours="2.0")
    headers, cookies = auth_for(manager_identity, "acme")
    admin_client.post(f"/members/{removed.id}/deactivate", headers=headers, cookies=cookies)

    resp = admin_client.get(
        f"/cases/{case.id}/narratives/rate-check",
        params=DEFAULT_PERIOD,
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["name"] == "Removed Lawyer"
    assert rows[0]["active"] is False


def test_hourly_rate_settable_for_a_removed_lawyer(admin_client, db):
    """Regression test: the hourly-rate endpoint used to reject inactive
    memberships outright, leaving a removed lawyer's rate permanently
    stuck once they were removed — even though their already-logged hours
    still feed into a narrative's total_fee. office_manager must be able
    to correct it from the rate-check warning even after removal.
    """
    tenant = make_tenant(db, "acme")
    manager_identity, _ = _manager(db, tenant)
    _, lawyer_membership = _lawyer(db, tenant)
    headers, cookies = auth_for(manager_identity, "acme")
    admin_client.post(f"/members/{lawyer_membership.id}/deactivate", headers=headers, cookies=cookies)

    resp = admin_client.patch(
        f"/members/{lawyer_membership.id}/hourly-rate", json={"hourly_rate": "350.00"}, headers=headers, cookies=cookies
    )

    assert resp.status_code == 200
    assert resp.json()["hourly_rate"] == "350.00"
    assert resp.json()["active"] is False
