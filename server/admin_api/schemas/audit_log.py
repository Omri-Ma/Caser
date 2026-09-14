from datetime import datetime

from pydantic import BaseModel


class AuditLogEntryResponse(BaseModel):
    """One AuditLog row for the office_manager's browsing screen — read-only,
    no write path here (see shared/models/audit_log.py's writers: document
    archive/restore/permanent-delete, work log edit/delete, member
    deactivate, narrative PDF export, Excel import).
    """

    id: int
    action: str
    target: str
    timestamp: datetime
    actor_name: str
    actor_email: str
