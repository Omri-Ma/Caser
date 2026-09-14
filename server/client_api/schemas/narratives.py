from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from shared.models.enums import NarrativeLanguage


class NarrativeResponse(BaseModel):
    id: int
    case_id: int
    generated_text: str
    total_hours: Decimal
    total_fee: Decimal
    language: NarrativeLanguage
    period_start: date
    period_end: date
    created_at: datetime
