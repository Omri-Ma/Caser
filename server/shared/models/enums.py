import enum


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    OFFICE_MANAGER = "office_manager"
    LAWYER = "lawyer"
    CLIENT = "client"


class Plan(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class DocumentFolderType(str, enum.Enum):
    CLIENT = "client"
    INTERNAL = "internal"


class WorkLogSource(str, enum.Enum):
    MANUAL = "manual"
    EXCEL_IMPORT = "excel_import"


class CaseStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    CLOSED = "closed"
