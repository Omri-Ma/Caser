from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from shared.models.enums import CaseStatus, PracticeArea


class CaseResponse(BaseModel):
    id: int
    tenant_id: int
    title: str
    status: CaseStatus
    created_at: datetime
    practice_areas: List[PracticeArea] = Field(default_factory=list)
