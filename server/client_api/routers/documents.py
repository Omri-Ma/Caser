from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional

from client_api.core.case_access import get_assigned_case
from client_api.core.file_validation import CONTENT_TYPE_BY_LABEL, MAX_FILE_SIZE_BYTES, detect_file_type
from client_api.core.pagination import Page, PageParams, paginate
from client_api.schemas.documents import DocumentResponse, ReclassifyDocumentRequest
from shared.database import get_db
from shared.membership import require_role
from shared.models import AuditLog, Case, Document, Identity, Membership, Tenant
from shared.models.enums import CaseStatus, DocumentFolderType, UserRole
from shared.plan_limits import check_plan_limit
from shared.scoped import get_tenant_scoped
from shared.storage import get_file_url, save_file
from shared.tenant import get_current_tenant
from shared import error_messages as E

router = APIRouter(prefix="/cases/{case_id}/documents", tags=["documents"])


def _get_case_document(case: Case, document_id: int, tenant: Tenant, db: Session) -> Document:
    document = get_tenant_scoped(Document, document_id, tenant.id, db, E.DOCUMENT_NOT_FOUND)
    if document.case_id != case.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=E.DOCUMENT_NOT_FOUND)
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


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    case_id: int,
    file: UploadFile = File(...),
    folder_type: DocumentFolderType = Form(...),
    confirm_replace: bool = Form(False),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_role(UserRole.LAWYER, UserRole.CLIENT)),
):
    """Upload a document to a case's client or internal folder. A client can
    only ever upload to the client folder; a lawyer can upload to either. A
    closed case blocks new uploads (CLAUDE.md's Cases lifecycle rule).

    Same-filename handling: if an active document with the same name already
    exists in the target folder, this returns 409 unless confirm_replace is
    set — the frontend re-submits with confirm_replace=true after the user
    confirms, at which point the old document is archived (not deleted) and
    the new upload becomes active under that name.
    """
    case = get_assigned_case(case_id, tenant, membership, db)

    if case.status == CaseStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.CASE_CLOSED_CANNOT_ADD_DOCUMENTS)

    if membership.role == UserRole.CLIENT and folder_type != DocumentFolderType.CLIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=E.CLIENTS_UPLOAD_TO_CLIENT_FOLDER_ONLY)

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=E.document_file_exceeds_limit(MAX_FILE_SIZE_BYTES // (1024 * 1024)),
        )

    detected = detect_file_type(content)
    if detected is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=E.UNSUPPORTED_FILE_TYPE_DOCUMENT,
        )

    original_filename = file.filename or "upload"

    existing_active = (
        db.query(Document)
        .filter(
            Document.tenant_id == tenant.id,
            Document.case_id == case.id,
            Document.folder_type == folder_type,
            Document.original_filename == original_filename,
            Document.archived_at.is_(None),
        )
        .first()
    )
    if existing_active is not None and not confirm_replace:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=E.document_name_already_exists(original_filename),
        )

    check_plan_limit(tenant.id, "storage_bytes", db, additional=len(content))

    if existing_active is not None:
        existing_active.archived_at = datetime.now(timezone.utc)

    storage_key = save_file(content, tenant.id, case.id, original_filename)
    document = Document(
        tenant_id=tenant.id,
        case_id=case.id,
        uploaded_by=membership.id,
        file_url=storage_key,
        original_filename=original_filename,
        content_type=CONTENT_TYPE_BY_LABEL[detected],
        file_size=len(content),
        folder_type=folder_type,
    )
    db.add(document)
    db.add(
        AuditLog(
            tenant_id=tenant.id,
            user_id=membership.id,
            action="document_uploaded",
            target=original_filename,
        )
    )
    db.commit()
    db.refresh(document)
    return _to_response(document, db)


@router.get("", response_model=Page[DocumentResponse])
def list_documents(
    case_id: int,
    search: Optional[str] = Query(None, description="Partial, case-insensitive match on filename"),
    folder_type: Optional[DocumentFolderType] = Query(None),
    archived: bool = Query(False),
    params: PageParams = Depends(),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_role(UserRole.LAWYER, UserRole.CLIENT)),
):
    """Folder visibility per CLAUDE.md: client-folder documents are visible
    to assigned clients and lawyers alike; internal-folder documents are
    lawyer/office_manager only — a client is never shown, and never allowed
    to ask for, the internal folder. Clients can't browse the archive at
    all (once archived, it's out of their hands).
    """
    case = get_assigned_case(case_id, tenant, membership, db)

    if archived and membership.role == UserRole.CLIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=E.CLIENTS_CANNOT_BROWSE_ARCHIVE)

    query = (
        db.query(Document, Identity)
        .join(Membership, Document.uploaded_by == Membership.id)
        .join(Identity, Membership.identity_id == Identity.id)
        .filter(Document.tenant_id == tenant.id, Document.case_id == case.id)
    )

    if search:
        query = query.filter(Document.original_filename.ilike(f"%{search}%"))

    if membership.role == UserRole.CLIENT:
        if folder_type is not None and folder_type != DocumentFolderType.CLIENT:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=E.CLIENTS_SEE_CLIENT_FOLDER_ONLY)
        query = query.filter(Document.folder_type == DocumentFolderType.CLIENT)
    elif folder_type is not None:
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
    membership: Membership = Depends(require_role(UserRole.LAWYER, UserRole.CLIENT)),
):
    case = get_assigned_case(case_id, tenant, membership, db)
    document = _get_case_document(case, document_id, tenant, db)

    if membership.role == UserRole.CLIENT and (
        document.folder_type != DocumentFolderType.CLIENT or document.archived_at is not None
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=E.DOCUMENT_NOT_FOUND)

    path = get_file_url(document.file_url)
    return FileResponse(path, media_type=document.content_type, filename=document.original_filename)


@router.post("/{document_id}/archive", response_model=DocumentResponse)
def archive_document(
    case_id: int,
    document_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_role(UserRole.LAWYER, UserRole.CLIENT)),
):
    """Client: own uploads only. Lawyer: any document on this (assigned)
    case, their own or a colleague's — same broad, collaborative authority
    used elsewhere on a shared case record.
    """
    case = get_assigned_case(case_id, tenant, membership, db)
    document = _get_case_document(case, document_id, tenant, db)

    if membership.role == UserRole.CLIENT and document.uploaded_by != membership.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=E.CLIENTS_ARCHIVE_OWN_UPLOADS_ONLY)

    if document.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.ALREADY_ARCHIVED)

    document.archived_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            tenant_id=tenant.id,
            user_id=membership.id,
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
    membership: Membership = Depends(require_role(UserRole.LAWYER)),
):
    """Lawyer-only — clients can't restore anything, even their own, same
    asymmetry as everywhere else (they'd ask a lawyer).
    """
    case = get_assigned_case(case_id, tenant, membership, db)
    document = _get_case_document(case, document_id, tenant, db)

    if document.archived_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.DOCUMENT_NOT_ARCHIVED)

    document.archived_at = None
    db.add(
        AuditLog(
            tenant_id=tenant.id,
            user_id=membership.id,
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
    membership: Membership = Depends(require_role(UserRole.LAWYER)),
):
    """Lawyer-only, never client — moving your own upload into internal
    would just make it invisible to yourself, so it's meaningless as a
    client action anyway.
    """
    case = get_assigned_case(case_id, tenant, membership, db)
    document = _get_case_document(case, document_id, tenant, db)

    document.folder_type = payload.folder_type
    db.commit()
    db.refresh(document)
    return _to_response(document, db)
