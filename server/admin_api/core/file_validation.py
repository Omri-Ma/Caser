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


# admin_api's own copy of client_api's image-only subset of detect_file_type
# — needed for the tenant logo upload (a firm's branding, edited from
# admin/'s BrandingPage). Same duplication reasoning as is_xlsx_file above:
# this app never receives a Documents upload, but it does receive this one
# directly, so it needs its own magic-byte check rather than trusting the
# filename extension.
MAX_LOGO_FILE_SIZE_BYTES = 5 * 1024 * 1024


def detect_image_type(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if content.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    return None
