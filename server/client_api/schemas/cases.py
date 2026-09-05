from datetime import datetime

from pydantic import BaseModel

from shared.models.enums import CaseStatus


class CaseResponse(BaseModel):
    id: int
    tenant_id: int
    title: str
    status: CaseStatus
    created_at: datetime
