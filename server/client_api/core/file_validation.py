import zipfile
from io import BytesIO

# ~50MB per-file cap (CLAUDE.md), applied equally on every plan — separate
# from the total-storage quota (shared/plan_limits.py), which differs by plan.
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024

CONTENT_TYPE_BY_LABEL = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "jpeg": "image/jpeg",
    "png": "image/png",
}


def detect_file_type(content: bytes) -> str | None:
    """Sniff the real file type from its content/magic bytes — never trusts
    the filename extension (trivially fakeable). Returns one of "pdf" /
    "docx" / "jpeg" / "png", or None if it doesn't match any allowed type.

    Uses only the standard library (no python-magic/filetype dependency):
    the first three are plain fixed-signature checks; DOCX is a zip file, so
    a bare "PK\\x03\\x04" signature alone can't distinguish it from any other
    zip — it's confirmed by actually opening the zip and checking for the
    one entry every real .docx contains.
    """
    if content.startswith(b"%PDF-"):
        return "pdf"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if content.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if content[:4] == b"PK\x03\x04":
        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                if "word/document.xml" in archive.namelist():
                    return "docx"
        except zipfile.BadZipFile:
            return None
    return None


# Separate from detect_file_type/CONTENT_TYPE_BY_LABEL on purpose — that
# allowlist is for Documents uploads (PDF/DOCX/JPEG/PNG); a work-log Excel
# import is a different upload with its own single expected type.
MAX_IMPORT_FILE_SIZE_BYTES = 5 * 1024 * 1024


def is_xlsx_file(content: bytes) -> bool:
    """Same zip-signature + inner-file-check approach as the DOCX case
    above — a bare "PK\\x03\\x04" signature can't distinguish .xlsx from any
    other zip, so this confirms the one entry every real .xlsx contains.
    """
    if content[:4] != b"PK\x03\x04":
        return False
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            return "xl/workbook.xml" in archive.namelist()
    except zipfile.BadZipFile:
        return False
