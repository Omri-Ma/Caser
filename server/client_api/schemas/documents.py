from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from shared.models.enums import DocumentFolderType


class DocumentResponse(BaseModel):
    id: int
    case_id: int
    folder_type: DocumentFolderType
    original_filename: str
    content_type: str
    file_size: int
    uploaded_by: int
    uploader_name: str
    archived_at: Optional[datetime] = None
    created_at: datetime


class ReclassifyDocumentRequest(BaseModel):
    folder_type: DocumentFolderType
