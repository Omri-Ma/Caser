from datetime import datetime
from typing import List

from pydantic import BaseModel, EmailStr, Field

from shared.models.enums import CaseStatus, PracticeArea, UserRole


class CreateCaseRequest(BaseModel):
    """office_manager creates a case — it always starts life as `open`;
    status changes go through the dedicated status endpoint below.
    """

    title: str = Field(..., min_length=1, max_length=255)


class UpdateCaseTitleRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class UpdateCaseStatusRequest(BaseModel):
    status: CaseStatus


class AssignCaseRequest(BaseModel):
    """membership_id is resolved through get_tenant_scoped, never a bare id
    lookup — see CLAUDE.md's Multi-tenancy architecture.
    """

    membership_id: int


class SetCaseTagsRequest(BaseModel):
    """office_manager-only — replaces the full set of practice-area tags on
    a case in one call (simpler than separate add/remove endpoints for a
    small, fixed-enum tag list).
    """

    practice_areas: List[PracticeArea] = Field(default_factory=list)


class CaseResponse(BaseModel):
    id: int
    tenant_id: int
    title: str
    status: CaseStatus
    created_at: datetime
    practice_areas: List[PracticeArea] = Field(default_factory=list)


class CaseAssignmentResponse(BaseModel):
    id: int
    case_id: int
    membership_id: int
    role: UserRole
    identity_name: str
    identity_email: EmailStr
