from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class NarrativeResponse(BaseModel):
    id: int
    case_id: int
    generated_text: str
    total_hours: Decimal
    total_fee: Decimal
    created_at: datetime
