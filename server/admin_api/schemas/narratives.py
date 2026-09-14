from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from shared.models.enums import NarrativeLanguage
from shared import error_messages as E


class GenerateNarrativeRequest(BaseModel):
    """period_start/period_end are chosen by office_manager at generation
    time — real legal billing is period-by-period, not every hour ever
    logged on the case (CLAUDE.md). No overlap-prevention against other
    narratives on the same case: re-covering a period already billed is a
    legitimate correction, not an error.
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


class ExportNarrativeRequest(BaseModel):
    """office_manager names the exported file at export time, rather than
    it being auto-generated (CLAUDE.md's Narratives note) — same "person
    doing the export controls the presentation" reasoning already used for
    choosing the narrative's language. The .pdf extension is enforced
    server-side regardless of what's typed, since the file is always a PDF.
    """

    filename: str = Field(..., min_length=1, max_length=200)
