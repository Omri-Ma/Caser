from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from admin_api.core.pagination import Page, PageParams, paginate
from admin_api.schemas.documents import DocumentResponse, ReclassifyDocumentRequest
from shared.database import get_db
from shared.membership import require_role
from shared.models import AuditLog, Case, Document, Identity, Membership, Tenant
from shared.models.enums import DocumentFolderType, UserRole
from shared.scoped import get_tenant_scoped
from shared.storage import delete_file, get_file_url
from shared.tenant import get_current_tenant

router = APIRouter(prefix="/cases/{case_id}/documents", tags=["documents"])


def _get_case_document(case: Case, document_id: int, tenant: Tenant, db: Session) -> Document:
    document = get_tenant_scoped(Document, document_id, tenant.id, db, "Document not found")
    if document.case_id != case.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


def _to_response(document: Document, db: Session) -> DocumentResponse:
    identity = (
        db.query(Identity)
        .join(Membership, Membership.identity_id == Identity.id)
        .filter(Membership.id == document.uploaded_by)
        .first()
    )
    return DocumentResponse(
        id=document.id,
        case_id=document.case_id,
        folder_type=document.folder_type,
        original_filename=document.original_filename,
        content_type=document.content_type,
        file_size=document.file_size,
        uploaded_by=document.uploaded_by,
        uploader_name=identity.name if identity else "Unknown",
        archived_at=document.archived_at,
        created_at=document.created_at,
    )


@router.get("", response_model=Page[DocumentResponse])
def list_documents(
    case_id: int,
    search: Optional[str] = Query(None, description="Partial, case-insensitive match on filename"),
    folder_type: Optional[DocumentFolderType] = Query(None),
    archived: bool = Query(False),
    params: PageParams = Depends(),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """office_manager sees every case at their tenant automatically — no
    CaseAssignment check — and both folders, no client-folder restriction,
    per CLAUDE.md's oversight role.
    """
    case = get_tenant_scoped(Case, case_id, tenant.id, db, "Case not found")

    query = (
        db.query(Document, Identity)
        .join(Membership, Document.uploaded_by == Membership.id)
        .join(Identity, Membership.identity_id == Identity.id)
        .filter(Document.tenant_id == tenant.id, Document.case_id == case.id)
    )
    if search:
        query = query.filter(Document.original_filename.ilike(f"%{search}%"))
    if folder_type is not None:
        query = query.filter(Document.folder_type == folder_type)
    if archived:
        query = query.filter(Document.archived_at.isnot(None))
    else:
        query = query.filter(Document.archived_at.is_(None))
    query = query.order_by(Document.created_at.desc())

    rows, total = paginate(query, params)
    items = [
        DocumentResponse(
            id=document.id,
            case_id=document.case_id,
            folder_type=document.folder_type,
            original_filename=document.original_filename,
            content_type=document.content_type,
            file_size=document.file_size,
            uploaded_by=document.uploaded_by,
            uploader_name=identity.name,
            archived_at=document.archived_at,
            created_at=document.created_at,
        )
        for document, identity in rows
    ]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/{document_id}/download")
def download_document(
    case_id: int,
    document_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    case = get_tenant_scoped(Case, case_id, tenant.id, db, "Case not found")
    document = _get_case_document(case, document_id, tenant, db)
    path = get_file_url(document.file_url)
    return FileResponse(path, media_type=document.content_type, filename=document.original_filename)


@router.post("/{document_id}/archive", response_model=DocumentResponse)
def archive_document(
    case_id: int,
    document_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """office_manager can archive anything at their firm — the broadest of
    the three archive authorities (client: own uploads only, lawyer: any
    document on an assigned case, office_manager: anything).
    """
    case = get_tenant_scoped(Case, case_id, tenant.id, db, "Case not found")
    document = _get_case_document(case, document_id, tenant, db)

    if document.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already archived")

    document.archived_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            tenant_id=tenant.id,
            user_id=office_manager.id,
            action="document_archived",
            target=document.original_filename,
        )
    )
    db.commit()
    db.refresh(document)
    return _to_response(document, db)


@router.post("/{document_id}/restore", response_model=DocumentResponse)
def restore_document(
    case_id: int,
    document_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    case = get_tenant_scoped(Case, case_id, tenant.id, db, "Case not found")
    document = _get_case_document(case, document_id, tenant, db)

    if document.archived_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document is not archived")

    document.archived_at = None
    db.add(
        AuditLog(
            tenant_id=tenant.id,
            user_id=office_manager.id,
            action="document_restored",
            target=document.original_filename,
        )
    )
    db.commit()
    db.refresh(document)
    return _to_response(document, db)


@router.patch("/{document_id}", response_model=DocumentResponse)
def reclassify_document(
    case_id: int,
    document_id: int,
    payload: ReclassifyDocumentRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    case = get_tenant_scoped(Case, case_id, tenant.id, db, "Case not found")
    document = _get_case_document(case, document_id, tenant, db)

    document.folder_type = payload.folder_type
    db.commit()
    db.refresh(document)
    return _to_response(document, db)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def permanently_delete_document(
    case_id: int,
    document_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """The one irreversible step in the trash lifecycle — only reachable
    from inside the archive (the document must already be archived), and
    only office_manager can do it. Erases the file on disk and the row;
    only this actually frees storage quota (an archived document still
    counts against it).
    """
    case = get_tenant_scoped(Case, case_id, tenant.id, db, "Case not found")
    document = _get_case_document(case, document_id, tenant, db)

    if document.archived_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only archived documents can be permanently deleted — archive it first",
        )

    delete_file(document.file_url)
    db.add(
        AuditLog(
            tenant_id=tenant.id,
            user_id=office_manager.id,
            action="document_permanently_deleted",
            target=document.original_filename,
        )
    )
    db.delete(document)
    db.commit()
