from conftest import auth_for, make_assignment, make_case, make_document, make_identity, make_membership, make_tenant
from shared.models.enums import CaseStatus, DocumentFolderType, UserRole

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< >>\nendobj\n%%EOF"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
NOT_A_REAL_FILE = b"just some plain text, not a real document"


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


def test_lawyer_uploads_to_internal_folder(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, _ = _lawyer_on_case(db, tenant, case)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.post(
        f"/cases/{case.id}/documents",
        files={"file": ("memo.pdf", PDF_BYTES, "application/pdf")},
        data={"folder_type": "internal"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["folder_type"] == "internal"
    assert body["original_filename"] == "memo.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["archived_at"] is None


def test_client_cannot_upload_to_internal_folder(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    client_identity, _ = _client_on_case(db, tenant, case)
    headers, cookies = auth_for(client_identity, "acme")

    resp = client_client.post(
        f"/cases/{case.id}/documents",
        files={"file": ("scan.png", PNG_BYTES, "image/png")},
        data={"folder_type": "internal"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 403


def test_client_uploads_to_client_folder(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    client_identity, _ = _client_on_case(db, tenant, case)
    headers, cookies = auth_for(client_identity, "acme")

    resp = client_client.post(
        f"/cases/{case.id}/documents",
        files={"file": ("scan.png", PNG_BYTES, "image/png")},
        data={"folder_type": "client"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 201
    assert resp.json()["folder_type"] == "client"


def test_upload_rejects_disguised_file_type(client_client, db):
    """A .pdf filename whose actual bytes aren't a PDF must be rejected —
    the whole point of checking magic bytes instead of the extension.
    """
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, _ = _lawyer_on_case(db, tenant, case)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.post(
        f"/cases/{case.id}/documents",
        files={"file": ("totally-a.pdf", NOT_A_REAL_FILE, "application/pdf")},
        data={"folder_type": "internal"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 400


def test_upload_blocked_on_closed_case(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id, status=CaseStatus.CLOSED)
    lawyer_identity, _ = _lawyer_on_case(db, tenant, case)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.post(
        f"/cases/{case.id}/documents",
        files={"file": ("memo.pdf", PDF_BYTES, "application/pdf")},
        data={"folder_type": "internal"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 400


def test_upload_rejects_unassigned_lawyer(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    identity = make_identity(db, "outsider@acme.com")
    make_membership(db, identity.id, tenant.id, UserRole.LAWYER)  # not assigned to this case
    headers, cookies = auth_for(identity, "acme")

    resp = client_client.post(
        f"/cases/{case.id}/documents",
        files={"file": ("memo.pdf", PDF_BYTES, "application/pdf")},
        data={"folder_type": "internal"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 403


def test_same_filename_upload_requires_confirm_then_archives_old(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, _ = _lawyer_on_case(db, tenant, case)
    headers, cookies = auth_for(lawyer_identity, "acme")

    first = client_client.post(
        f"/cases/{case.id}/documents",
        files={"file": ("memo.pdf", PDF_BYTES, "application/pdf")},
        data={"folder_type": "internal"},
        headers=headers,
        cookies=cookies,
    )
    assert first.status_code == 201
    first_id = first.json()["id"]

    # Re-uploading the same filename without confirm_replace is a conflict.
    conflict = client_client.post(
        f"/cases/{case.id}/documents",
        files={"file": ("memo.pdf", PDF_BYTES, "application/pdf")},
        data={"folder_type": "internal"},
        headers=headers,
        cookies=cookies,
    )
    assert conflict.status_code == 409

    replaced = client_client.post(
        f"/cases/{case.id}/documents",
        files={"file": ("memo.pdf", PDF_BYTES, "application/pdf")},
        data={"folder_type": "internal", "confirm_replace": "true"},
        headers=headers,
        cookies=cookies,
    )
    assert replaced.status_code == 201
    assert replaced.json()["id"] != first_id

    active = client_client.get(f"/cases/{case.id}/documents", params={"folder_type": "internal"}, headers=headers, cookies=cookies)
    assert active.json()["total"] == 1
    assert active.json()["items"][0]["id"] == replaced.json()["id"]

    archive = client_client.get(
        f"/cases/{case.id}/documents", params={"folder_type": "internal", "archived": "true"}, headers=headers, cookies=cookies
    )
    assert archive.json()["total"] == 1
    assert archive.json()["items"][0]["id"] == first_id


def test_upload_over_storage_quota_rejected(client_client, db, monkeypatch):
    import shared.plan_limits as plan_limits

    monkeypatch.setitem(plan_limits.PLAN_STORAGE_LIMIT_BYTES, plan_limits.Plan.FREE, 10)

    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, _ = _lawyer_on_case(db, tenant, case)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.post(
        f"/cases/{case.id}/documents",
        files={"file": ("memo.pdf", PDF_BYTES, "application/pdf")},
        data={"folder_type": "internal"},
        headers=headers,
        cookies=cookies,
    )

    assert resp.status_code == 400
    assert "quota" in resp.json()["error"].lower()


def test_client_never_sees_internal_folder(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    client_identity, client_membership = _client_on_case(db, tenant, case)
    make_document(db, tenant.id, case.id, client_membership.id, folder_type=DocumentFolderType.INTERNAL)
    make_document(db, tenant.id, case.id, client_membership.id, folder_type=DocumentFolderType.CLIENT)
    headers, cookies = auth_for(client_identity, "acme")

    resp = client_client.get(f"/cases/{case.id}/documents", headers=headers, cookies=cookies)
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["folder_type"] == "client"

    explicit = client_client.get(
        f"/cases/{case.id}/documents", params={"folder_type": "internal"}, headers=headers, cookies=cookies
    )
    assert explicit.status_code == 403


def test_client_cannot_browse_archive(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    client_identity, client_membership = _client_on_case(db, tenant, case)
    headers, cookies = auth_for(client_identity, "acme")

    resp = client_client.get(f"/cases/{case.id}/documents", params={"archived": "true"}, headers=headers, cookies=cookies)
    assert resp.status_code == 403


def test_co_clients_share_the_same_client_folder_view(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    client_a_identity, client_a_membership = _client_on_case(db, tenant, case)
    client_b_identity = make_identity(db, "client-b@acme.com", "Second Client")
    client_b_membership = make_membership(db, client_b_identity.id, tenant.id, UserRole.CLIENT)
    make_assignment(db, tenant.id, case.id, client_b_membership.id)
    make_document(db, tenant.id, case.id, client_a_membership.id, folder_type=DocumentFolderType.CLIENT)
    headers, cookies = auth_for(client_b_identity, "acme")

    resp = client_client.get(f"/cases/{case.id}/documents", headers=headers, cookies=cookies)
    assert resp.json()["total"] == 1


def test_download_respects_client_visibility(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    client_identity, client_membership = _client_on_case(db, tenant, case)
    internal_doc = make_document(db, tenant.id, case.id, client_membership.id, folder_type=DocumentFolderType.INTERNAL)
    headers, cookies = auth_for(client_identity, "acme")

    resp = client_client.get(f"/cases/{case.id}/documents/{internal_doc.id}/download", headers=headers, cookies=cookies)
    assert resp.status_code == 404


def test_client_archives_own_upload_only(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    client_identity, client_membership = _client_on_case(db, tenant, case)
    other_identity = make_identity(db, "other-client@acme.com")
    other_membership = make_membership(db, other_identity.id, tenant.id, UserRole.CLIENT)
    make_assignment(db, tenant.id, case.id, other_membership.id)
    own_doc = make_document(db, tenant.id, case.id, client_membership.id, folder_type=DocumentFolderType.CLIENT)
    others_doc = make_document(db, tenant.id, case.id, other_membership.id, folder_type=DocumentFolderType.CLIENT)
    headers, cookies = auth_for(client_identity, "acme")

    own = client_client.post(f"/cases/{case.id}/documents/{own_doc.id}/archive", headers=headers, cookies=cookies)
    assert own.status_code == 200

    others = client_client.post(f"/cases/{case.id}/documents/{others_doc.id}/archive", headers=headers, cookies=cookies)
    assert others.status_code == 403


def test_lawyer_archives_any_document_on_assigned_case(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, lawyer_membership = _lawyer_on_case(db, tenant, case)
    other_lawyer_identity = make_identity(db, "colleague@acme.com")
    other_lawyer_membership = make_membership(db, other_lawyer_identity.id, tenant.id, UserRole.LAWYER)
    make_assignment(db, tenant.id, case.id, other_lawyer_membership.id)
    colleagues_doc = make_document(db, tenant.id, case.id, other_lawyer_membership.id, folder_type=DocumentFolderType.INTERNAL)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.post(f"/cases/{case.id}/documents/{colleagues_doc.id}/archive", headers=headers, cookies=cookies)
    assert resp.status_code == 200


def test_client_cannot_restore(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    client_identity, client_membership = _client_on_case(db, tenant, case)
    from datetime import datetime, timezone

    archived_doc = make_document(
        db, tenant.id, case.id, client_membership.id, folder_type=DocumentFolderType.CLIENT, archived_at=datetime.now(timezone.utc)
    )
    headers, cookies = auth_for(client_identity, "acme")

    resp = client_client.post(f"/cases/{case.id}/documents/{archived_doc.id}/restore", headers=headers, cookies=cookies)
    assert resp.status_code == 403


def test_lawyer_restores_archived_document(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, lawyer_membership = _lawyer_on_case(db, tenant, case)
    from datetime import datetime, timezone

    archived_doc = make_document(
        db, tenant.id, case.id, lawyer_membership.id, folder_type=DocumentFolderType.INTERNAL, archived_at=datetime.now(timezone.utc)
    )
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.post(f"/cases/{case.id}/documents/{archived_doc.id}/restore", headers=headers, cookies=cookies)
    assert resp.status_code == 200
    assert resp.json()["archived_at"] is None


def test_client_cannot_reclassify(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    client_identity, client_membership = _client_on_case(db, tenant, case)
    doc = make_document(db, tenant.id, case.id, client_membership.id, folder_type=DocumentFolderType.CLIENT)
    headers, cookies = auth_for(client_identity, "acme")

    resp = client_client.patch(
        f"/cases/{case.id}/documents/{doc.id}", json={"folder_type": "internal"}, headers=headers, cookies=cookies
    )
    assert resp.status_code == 403


def test_lawyer_reclassifies_document(client_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity, lawyer_membership = _lawyer_on_case(db, tenant, case)
    doc = make_document(db, tenant.id, case.id, lawyer_membership.id, folder_type=DocumentFolderType.INTERNAL)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = client_client.patch(
        f"/cases/{case.id}/documents/{doc.id}", json={"folder_type": "client"}, headers=headers, cookies=cookies
    )
    assert resp.status_code == 200
    assert resp.json()["folder_type"] == "client"
