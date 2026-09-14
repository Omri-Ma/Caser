from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from admin_api.core.narratives import (
    build_narrative_pdf,
    compute_case_totals,
    generate_narrative_text,
    get_case_work_logs_in_period,
)
from admin_api.core.pagination import Page, PageParams, paginate
from admin_api.schemas.documents import DocumentResponse
from admin_api.schemas.narratives import ExportNarrativeRequest, GenerateNarrativeRequest, NarrativeResponse
from shared.database import get_db
from shared.membership import require_role
from shared.models import AuditLog, Case, Document, Identity, Membership, Narrative, Tenant
from shared.models.enums import DocumentFolderType, UserRole
from shared.plan_limits import check_plan_limit
from shared.scoped import get_tenant_scoped
from shared.storage import save_file
from shared.tenant import get_current_tenant
from shared import error_messages as E

# office_manager-only (CLAUDE.md's Narratives note: reversed from an
# earlier any-lawyer-assigned draft once total_fee started depending on
# each lawyer's real, office_manager-set hourly_rate — generating a
# narrative is now closer to a billing/administrative action than
# day-to-day casework, same reasoning as Case status changes). office_manager
# sees every case at their own tenant automatically, same oversight
# authority as Documents/WorkLogs — no CaseAssignment check needed.
router = APIRouter(prefix="/cases/{case_id}/narratives", tags=["narratives"])


def _get_case_narrative(case_id: int, narrative_id: int, tenant: Tenant, db: Session) -> Narrative:
    narrative = get_tenant_scoped(Narrative, narrative_id, tenant.id, db, E.NARRATIVE_NOT_FOUND)
    if narrative.case_id != case_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=E.NARRATIVE_NOT_FOUND)
    return narrative


@router.post("", response_model=NarrativeResponse, status_code=status.HTTP_201_CREATED)
def generate_narrative(
    case_id: int,
    payload: GenerateNarrativeRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Fixed-template generation (CLAUDE.md: no real AI/LLM needed). Always
    inserts a new row — never edits an existing one; the newest row for a
    case is the current/authoritative one, older rows stay as history (same
    "rows accumulate, newest wins" pattern as Subscriptions). period/language
    are chosen by office_manager at generation time and stored as a fixed
    snapshot on the row, same reasoning as total_hours/total_fee.
    """
    case = get_tenant_scoped(Case, case_id, tenant.id, db, E.CASE_NOT_FOUND)

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


@router.get("", response_model=Page[NarrativeResponse])
def list_narratives(
    case_id: int,
    params: PageParams = Depends(),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Full history, newest first — the first row returned is always the
    current/authoritative narrative for the case.
    """
    case = get_tenant_scoped(Case, case_id, tenant.id, db, E.CASE_NOT_FOUND)

    query = (
        db.query(Narrative)
        .filter(Narrative.tenant_id == tenant.id, Narrative.case_id == case.id)
        .order_by(Narrative.created_at.desc(), Narrative.id.desc())
    )
    rows, total = paginate(query, params)
    return Page(items=rows, total=total, page=params.page, page_size=params.page_size)


@router.post("/{narrative_id}/export-pdf", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def export_narrative_pdf(
    case_id: int,
    narrative_id: int,
    payload: ExportNarrativeRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    office_manager: Membership = Depends(require_role(UserRole.OFFICE_MANAGER)),
):
    """Renders the narrative to PDF — including the itemized WorkLog table
    for the narrative's own stored period (CLAUDE.md's Narratives note) —
    and files it as a real Document on the case, internal folder by
    default. This is what makes a narrative reachable by the client at
    all — sharing it afterwards is just the existing Documents
    reclassify-to-client-folder action, no separate visibility mechanism
    needed here. office_manager names the file at export time rather than
    it being auto-generated (CLAUDE.md); the .pdf extension is enforced
    here regardless of what was typed.
    """
    case = get_tenant_scoped(Case, case_id, tenant.id, db, E.CASE_NOT_FOUND)
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
        uploaded_by=office_manager.id,
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
            user_id=office_manager.id,
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
