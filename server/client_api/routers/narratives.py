from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from client_api.core.case_access import get_assigned_case, require_manager_lawyer
from client_api.core.pagination import Page, PageParams, paginate
from client_api.schemas.documents import DocumentResponse
from client_api.schemas.narratives import ExportNarrativeRequest, GenerateNarrativeRequest, NarrativeResponse
from shared.database import get_db
from shared.membership import require_role
from shared.models import AuditLog, Document, Identity, Membership, Narrative, Tenant
from shared.models.enums import DocumentFolderType, UserRole
from shared.narratives import build_narrative_pdf, compute_case_totals, generate_narrative_text, get_case_work_logs_in_period
from shared.plan_limits import check_plan_limit
from shared.scoped import get_tenant_scoped
from shared.storage import save_file
from shared.tenant import get_current_tenant
from shared import error_messages as E

# list: read-only for any assigned lawyer — narratives are always
# firm-internal (CLAUDE.md), never client-visible directly. generate/
# export-pdf: manager-level authority only (require_manager_lawyer — a
# lawyer with Memberships.is_manager set, CLAUDE.md's Narratives note),
# the client_api-side mirror of admin_api's office_manager-gated routes.
# The actual generation/PDF logic lives in shared.narratives so both sides
# stay byte-for-byte identical; only the authorization check differs.
router = APIRouter(prefix="/cases/{case_id}/narratives", tags=["narratives"])


def _get_case_narrative(case_id: int, narrative_id: int, tenant: Tenant, db: Session) -> Narrative:
    narrative = get_tenant_scoped(Narrative, narrative_id, tenant.id, db, E.NARRATIVE_NOT_FOUND)
    if narrative.case_id != case_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=E.NARRATIVE_NOT_FOUND)
    return narrative


@router.get("", response_model=Page[NarrativeResponse])
def list_narratives(
    case_id: int,
    params: PageParams = Depends(),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_role(UserRole.LAWYER)),
):
    """Full history, newest first — the first row returned is always the
    current/authoritative narrative for the case.
    """
    case = get_assigned_case(case_id, tenant, membership, db)

    query = (
        db.query(Narrative)
        .filter(Narrative.tenant_id == tenant.id, Narrative.case_id == case.id)
        .order_by(Narrative.created_at.desc(), Narrative.id.desc())
    )
    rows, total = paginate(query, params)
    return Page(items=rows, total=total, page=params.page, page_size=params.page_size)


@router.post("", response_model=NarrativeResponse, status_code=status.HTTP_201_CREATED)
def generate_narrative(
    case_id: int,
    payload: GenerateNarrativeRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_manager_lawyer),
):
    """Manager-authority lawyer only (CLAUDE.md's Narratives note) — same
    fixed-template generation as admin_api's office_manager route, sharing
    the exact same underlying logic (shared.narratives) so the two can
    never silently drift apart. get_assigned_case succeeds here without an
    explicit CaseAssignment since require_manager_lawyer already implies
    has_full_case_visibility.
    """
    case = get_assigned_case(case_id, tenant, membership, db)

    total_hours, total_fee = compute_case_totals(case.id, tenant.id, db, payload.period_start, payload.period_end)
    narrative = Narrative(
        tenant_id=tenant.id,
        case_id=case.id,
        generated_text="",
        total_hours=total_hours,
        total_fee=total_fee,
        language=payload.language,
        period_start=payload.period_start,
        period_end=payload.period_end,
    )
    narrative.generated_text = generate_narrative_text(
        case, total_hours, total_fee, payload.language, payload.period_start, payload.period_end
    )
    db.add(narrative)
    db.commit()
    db.refresh(narrative)
    return narrative


@router.post("/{narrative_id}/export-pdf", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def export_narrative_pdf(
    case_id: int,
    narrative_id: int,
    payload: ExportNarrativeRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_manager_lawyer),
):
    """Renders the narrative to PDF — including the itemized WorkLog table
    for the narrative's own stored period — and files it as a real
    Document on the case, internal folder by default (CLAUDE.md). The
    manager-authority lawyer names the file at export time, same as
    office_manager's equivalent admin_api route.
    """
    case = get_assigned_case(case_id, tenant, membership, db)
    narrative = _get_case_narrative(case_id, narrative_id, tenant, db)

    work_log_rows = get_case_work_logs_in_period(case.id, tenant.id, db, narrative.period_start, narrative.period_end)
    pdf_bytes = build_narrative_pdf(case, narrative, work_log_rows)

    filename = payload.filename.strip()
    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"

    check_plan_limit(tenant.id, "storage_bytes", db, additional=len(pdf_bytes))

    storage_key = save_file(pdf_bytes, tenant.id, case.id, filename)
    document = Document(
        tenant_id=tenant.id,
        case_id=case.id,
        uploaded_by=membership.id,
        file_url=storage_key,
        original_filename=filename,
        content_type="application/pdf",
        file_size=len(pdf_bytes),
        folder_type=DocumentFolderType.INTERNAL,
    )
    db.add(document)
    db.add(
        AuditLog(
            tenant_id=tenant.id,
            user_id=membership.id,
            action="narrative_pdf_exported",
            target=filename,
        )
    )
    db.commit()
    db.refresh(document)

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
