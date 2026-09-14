from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from client_api.core.case_access import get_assigned_case
from client_api.core.pagination import Page, PageParams, paginate
from client_api.schemas.narratives import NarrativeResponse
from shared.database import get_db
from shared.membership import require_role
from shared.models import Membership, Narrative, Tenant
from shared.models.enums import UserRole
from shared.tenant import get_current_tenant

# Read-only for lawyers — narratives are always firm-internal (CLAUDE.md),
# never client-visible directly. Generation and PDF export are
# office_manager-only now (CLAUDE.md's Narratives note, reversed once
# total_fee started depending on each lawyer's real, office_manager-set
# hourly_rate) and live in admin_api instead — a lawyer assigned to the
# case can still see what will be billed, just not create or export it.
router = APIRouter(prefix="/cases/{case_id}/narratives", tags=["narratives"])


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
