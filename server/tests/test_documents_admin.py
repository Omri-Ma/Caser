from datetime import datetime, timezone

from conftest import auth_for, make_case, make_document, make_identity, make_membership, make_tenant
from shared.models import AuditLog
from shared.models.enums import DocumentFolderType, UserRole


def _manager(db, tenant):
    identity = make_identity(db, "manager@acme.com", "Noa Manager")
    membership = make_membership(db, identity.id, tenant.id, UserRole.OFFICE_MANAGER)
    return identity, membership


def test_office_manager_sees_both_folders_without_assignment(admin_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, manager_membership = _manager(db, tenant)
    make_document(db, tenant.id, case.id, manager_membership.id, folder_type=DocumentFolderType.INTERNAL)
    make_document(db, tenant.id, case.id, manager_membership.id, folder_type=DocumentFolderType.CLIENT)
    headers, cookies = auth_for(manager_identity, "acme")

    resp = admin_client.get(f"/cases/{case.id}/documents", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_lawyer_cannot_use_admin_documents_route(admin_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    lawyer_identity = make_identity(db, "lawyer@acme.com")
    make_membership(db, lawyer_identity.id, tenant.id, UserRole.LAWYER)
    headers, cookies = auth_for(lawyer_identity, "acme")

    resp = admin_client.get(f"/cases/{case.id}/documents", headers=headers, cookies=cookies)

    assert resp.status_code == 403


def test_office_manager_archives_and_restores_any_document(admin_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, manager_membership = _manager(db, tenant)
    other_identity = make_identity(db, "lawyer@acme.com")
    other_membership = make_membership(db, other_identity.id, tenant.id, UserRole.LAWYER)
    doc = make_document(db, tenant.id, case.id, other_membership.id, folder_type=DocumentFolderType.INTERNAL)
    headers, cookies = auth_for(manager_identity, "acme")

    archived = admin_client.post(f"/cases/{case.id}/documents/{doc.id}/archive", headers=headers, cookies=cookies)
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None

    log = db.query(AuditLog).filter(AuditLog.action == "document_archived").first()
    assert log is not None
    assert log.user_id == manager_membership.id

    restored = admin_client.post(f"/cases/{case.id}/documents/{doc.id}/restore", headers=headers, cookies=cookies)
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None


def test_permanent_delete_requires_archived_first(admin_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, manager_membership = _manager(db, tenant)
    doc = make_document(db, tenant.id, case.id, manager_membership.id, folder_type=DocumentFolderType.INTERNAL)
    headers, cookies = auth_for(manager_identity, "acme")

    resp = admin_client.delete(f"/cases/{case.id}/documents/{doc.id}", headers=headers, cookies=cookies)

    assert resp.status_code == 400


def test_permanent_delete_succeeds_from_archive(admin_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, manager_membership = _manager(db, tenant)
    doc = make_document(
        db,
        tenant.id,
        case.id,
        manager_membership.id,
        folder_type=DocumentFolderType.INTERNAL,
        archived_at=datetime.now(timezone.utc),
    )
    doc_id = doc.id
    headers, cookies = auth_for(manager_identity, "acme")

    resp = admin_client.delete(f"/cases/{case.id}/documents/{doc_id}", headers=headers, cookies=cookies)

    assert resp.status_code == 204
    still_there = admin_client.get(
        f"/cases/{case.id}/documents", params={"archived": "true"}, headers=headers, cookies=cookies
    )
    assert still_there.json()["total"] == 0

    log = db.query(AuditLog).filter(AuditLog.action == "document_permanently_deleted").first()
    assert log is not None


def test_office_manager_reclassifies_document(admin_client, db):
    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, manager_membership = _manager(db, tenant)
    doc = make_document(db, tenant.id, case.id, manager_membership.id, folder_type=DocumentFolderType.CLIENT)
    headers, cookies = auth_for(manager_identity, "acme")

    resp = admin_client.patch(
        f"/cases/{case.id}/documents/{doc.id}", json={"folder_type": "internal"}, headers=headers, cookies=cookies
    )
    assert resp.status_code == 200
    assert resp.json()["folder_type"] == "internal"


def test_office_manager_downloads_any_document(admin_client, db):
    import shared.storage as storage

    tenant = make_tenant(db, "acme")
    case = make_case(db, tenant.id)
    manager_identity, manager_membership = _manager(db, tenant)
    storage_key = storage.save_file(b"%PDF-1.4 test", tenant.id, case.id, "memo.pdf")
    doc = make_document(db, tenant.id, case.id, manager_membership.id, folder_type=DocumentFolderType.INTERNAL)
    doc.file_url = storage_key
    db.commit()
    headers, cookies = auth_for(manager_identity, "acme")

    resp = admin_client.get(f"/cases/{case.id}/documents/{doc.id}/download", headers=headers, cookies=cookies)

    assert resp.status_code == 200
    assert resp.content == b"%PDF-1.4 test"
