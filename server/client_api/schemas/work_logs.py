from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from shared.models.enums import WorkLogSource


class CreateWorkLogRequest(BaseModel):
    date: date
    hours: Decimal = Field(..., gt=0, le=24)
    description: Optional[str] = Field(None, max_length=1000)


class UpdateWorkLogRequest(BaseModel):
    date: date
    hours: Decimal = Field(..., gt=0, le=24)
    description: Optional[str] = Field(None, max_length=1000)


class WorkLogResponse(BaseModel):
    id: int
    case_id: int
    lawyer_id: int
    lawyer_name: str
    date: date
    hours: Decimal
    description: Optional[str] = None
    source: WorkLogSource
