from datetime import date

from conftest import auth_for, make_assignment, make_case, make_identity, make_membership, make_tenant
from shared.models import WorkLog
from shared.models.enums import WorkLogSource, UserRole


def _lawyer_on_case(db, tenant, case):
    identity = make_identity(db, "lawyer@acme.com", "Lior Lawyer")
    membership = make_membership(db, identity.id, tenant.id, UserRole.LAWYER)
    make_assignment(db, tenant.id, case.id, membership.id)
    return identity, membership


def _work_log_on(db, tenant_id, case_id, lawyer_id, on_date, hours="2.0"):
    work_log = WorkLog(
        tenant_id=tenant_id,
        case_id=case_id,
        lawyer_id=lawyer_id,
        date=on_date,
        hours=hours,
        description="entry",
        source=WorkLogSource.MANUAL,
    )
    db.add(work_log)
    db.commit()
    return work_log


def test_narrative_only_sums_hours_inside_period(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, lawyer_membership = _lawyer_on_case(db, tenant, case)
    _work_log_on(db, tenant.id, case.id, lawyer_membership.id, date(2026, 1, 15), hours="3.0")  # inside
    _work_log_on(db, tenant.id, case.id, lawyer_membership.id, date(2026, 3, 1), hours="10.0")  # outside
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.post(
        f"/cases/{case.id}/narratives",
        json={"period_start": "2026-01-01", "period_end": "2026-01-31", "language": "he"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["total_hours"] == "3.00"
    assert body["period_start"] == "2026-01-01"
    assert body["period_end"] == "2026-01-31"


def test_narrative_rejects_period_end_before_start(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, _ = _lawyer_on_case(db, tenant, case)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.post(
        f"/cases/{case.id}/narratives",
        json={"period_start": "2026-02-01", "period_end": "2026-01-01", "language": "he"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 422


def test_hebrew_narrative_never_uses_shekel_glyph(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, lawyer_membership = _lawyer_on_case(db, tenant, case)
    _work_log_on(db, tenant.id, case.id, lawyer_membership.id, date.today(), hours="2.0")
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.post(
        f"/cases/{case.id}/narratives",
        json={"period_start": "2000-01-01", "period_end": "2100-01-01", "language": "he"},
        headers=headers,
        cookies=cookies,
    )

    body = resp.json()
    assert "₪" not in body["generated_text"]  # ₪
    assert 'ש"ח' in body["generated_text"]
    assert body["language"] == "he"


def test_english_narrative_uses_ils_not_shekel_glyph(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, lawyer_membership = _lawyer_on_case(db, tenant, case)
    _work_log_on(db, tenant.id, case.id, lawyer_membership.id, date.today(), hours="2.0")
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.post(
        f"/cases/{case.id}/narratives",
        json={"period_start": "2000-01-01", "period_end": "2100-01-01", "language": "en"},
        headers=headers,
        cookies=cookies,
    )

    body = resp.json()
    assert "₪" not in body["generated_text"]
    assert "ILS" in body["generated_text"]
    assert body["language"] == "en"


def test_export_pdf_renders_for_both_languages(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, lawyer_membership = _lawyer_on_case(db, tenant, case)
    _work_log_on(db, tenant.id, case.id, lawyer_membership.id, date.today(), hours="1.0")
    headers, cookies = auth_for(lawyer_identity, "acme")

    for language in ("he", "en"):
        narrative_resp = client_client.post(
            f"/cases/{case.id}/narratives",
            json={"period_start": "2000-01-01", "period_end": "2100-01-01", "language": language},
            headers=headers,
            cookies=cookies,
        )
        narrative_id = narrative_resp.json()["id"]

        export_resp = client_client.post(
            f"/cases/{case.id}/narratives/{narrative_id}/export-pdf", headers=headers, cookies=cookies
        )
        assert export_resp.status_code == 201
        assert export_resp.json()["content_type"] == "application/pdf"


def test_hebrew_pdf_embeds_real_hebrew_font(db):
    """Direct unit check on the PDF-building function (bypassing the API) —
    confirms the bundled Hebrew TTF is actually registered/embedded for a
    `he` narrative rather than silently falling back to Helvetica (which has
    no Hebrew glyphs at all).
    """
    from client_api.core.narratives import build_narrative_pdf
    from shared.models import Case, Narrative
    from shared.models.enums import CaseStatus, NarrativeLanguage
    from datetime import date, datetime
    from decimal import Decimal

    case = Case(id=1, tenant_id=1, title="Test Case", status=CaseStatus.OPEN)
    narrative = Narrative(
        id=1,
        tenant_id=1,
        case_id=1,
        generated_text='סיכום בעברית עם מספרים 123 ותאריך 01/02/2026.',
        total_hours=Decimal("2.00"),
        total_fee=Decimal("900.00"),
        language=NarrativeLanguage.HE,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        created_at=datetime(2026, 2, 1, 10, 0),
    )

    pdf_bytes = build_narrative_pdf(case, narrative)

    assert pdf_bytes.startswith(b"%PDF")
    assert b"Alef" in pdf_bytes  # embedded font name present in the PDF object stream
