import zipfile
from io import BytesIO

# admin_api's own copy of the same xlsx magic-byte check client_api's
# file_validation.py has — this app never receives a Documents upload (per
# CLAUDE.md, that request-level handling stays client_api-only), but the
# office_manager bulk work-log import does upload a file directly to this
# app, so it needs the same detection. Small enough (and app-upload-specific
# enough) to duplicate rather than promote into server/shared — unlike the
# row-parsing/validation logic in shared/worklog_import.py, this doesn't need
# to produce byte-identical behavior across apps, it just needs "is this
# really an .xlsx file" answered the same way twice.
MAX_IMPORT_FILE_SIZE_BYTES = 5 * 1024 * 1024


def is_xlsx_file(content: bytes) -> bool:
    if content[:4] != b"PK\x03\x04":
        return False
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            return "xl/workbook.xml" in archive.namelist()
    except zipfile.BadZipFile:
        return False
