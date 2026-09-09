from pydantic import BaseModel


class ImportRowErrorSchema(BaseModel):
    row: int
    message: str


class WorkLogImportResponse(BaseModel):
    imported_count: int


class WorkLogImportErrorResponse(BaseModel):
    error: str
    field: str = "file"
    row_errors: list[ImportRowErrorSchema]
