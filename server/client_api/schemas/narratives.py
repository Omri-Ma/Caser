from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, model_validator

from shared.models.enums import NarrativeLanguage
from shared import error_messages as E


class GenerateNarrativeRequest(BaseModel):
    """period_start/period_end are chosen by the lawyer at generation time —
    real legal billing is period-by-period, not every hour ever logged on
    the case (CLAUDE.md). No overlap-prevention against other narratives on
    the same case: re-covering a period already billed is a legitimate
    correction, not an error.
    """

    period_start: date
    period_end: date
    language: NarrativeLanguage = NarrativeLanguage.HE

    @model_validator(mode="after")
    def _check_period(self):
        if self.period_end < self.period_start:
            raise ValueError(E.PERIOD_END_BEFORE_START)
        return self


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
