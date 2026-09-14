"""Centralized Hebrew error-message catalog (CLAUDE.md's Architecture rules:
"one consistent mechanism", not per-message patches). Every user-facing
error string raised by either backend — HTTPException.detail, an Excel
import row error, a Pydantic model_validator's ValueError — should come
from here rather than a hand-typed literal at the raise site. This is what
keeps the same logical error worded identically everywhere it's raised
(e.g. "not found" appears from a dozen different routers) and gives a
wording fix exactly one place to happen.

Internal/programmer-only errors that can never actually reach a real HTTP
client from user input (e.g. plan_limits.py's "unknown resource_type" on a
hardcoded call-site literal) are deliberately left out of this catalog and
stay in English — they're not "backend error messages" in the CLAUDE.md
sense, they're assertions against our own code.
"""

# --- Not found ---
CASE_NOT_FOUND = "התיק לא נמצא"
MEMBERSHIP_NOT_FOUND = "החברות לא נמצאה"
MEMBER_NOT_FOUND = "איש/אשת הצוות לא נמצא/ה"
ASSIGNMENT_NOT_FOUND = "השיוך לתיק לא נמצא"
DOCUMENT_NOT_FOUND = "המסמך לא נמצא"
NARRATIVE_NOT_FOUND = "הסיכום לא נמצא"
WORK_LOG_NOT_FOUND = "רישום שעות העבודה לא נמצא"
TENANT_NOT_FOUND = "המשרד לא נמצא"
INVITE_NOT_FOUND = "ההזמנה לא נמצאה"
NO_LOGO_UPLOADED = "לא הועלה לוגו"

# --- Auth / session ---
NOT_LOGGED_IN = "לא מחובר/ת למערכת"
INVALID_OR_EXPIRED_SESSION = "החיבור אינו תקף או שפג תוקפו"
INVALID_SESSION_TOKEN = "אסימון החיבור אינו תקין"
INVALID_TOKEN_TYPE = "סוג האסימון אינו תקין"
ACCOUNT_NO_LONGER_EXISTS = "החשבון כבר לא קיים"
SESSION_INVALIDATED = "החיבור בוטל — יש להתחבר מחדש"
INVALID_EMAIL_OR_PASSWORD = "אימייל או סיסמה שגויים"
NO_ACCESS_TO_FIRM = "אין לך גישה למשרד זה"
CURRENT_PASSWORD_INCORRECT = "הסיסמה הנוכחית שגויה"
RESET_LINK_INVALID_OR_EXPIRED = "קישור האיפוס אינו תקין או שפג תוקפו"
EMAIL_ALREADY_REGISTERED = "כתובת האימייל כבר רשומה במערכת"
SUBDOMAIN_RESERVED = "כתובת המשנה (subdomain) הזו שמורה למערכת"
SUBDOMAIN_TAKEN = "כתובת המשנה (subdomain) הזו כבר תפוסה"
NOT_ALLOWED_FOR_ROLE = "הפעולה אינה מותרת עבור התפקיד שלך"
PLATFORM_STAFF_ONLY = "הגישה מוגבלת לצוות הפלטפורמה בלבד"
NO_OFFICE_MANAGER_ACCOUNT_FOUND = "לא נמצא חשבון מנהל/ת משרד עבור אימייל זה, באף משרד"
NO_LAWYER_OR_CLIENT_ACCOUNT_FOUND = "לא נמצא חשבון עורך/ת דין או לקוח/ה עבור אימייל זה, באף משרד"
EMAIL_EXISTS_LOGIN_TO_FOUND_FIRM = "קיים כבר חשבון עם אימייל זה — יש להתחבר עם הסיסמה הקיימת כדי לייסד משרד חדש"

# --- Tenant resolution ---
REQUEST_MUST_BE_TO_TENANT_SUBDOMAIN = "הבקשה חייבת להתבצע דרך כתובת משנה (subdomain) של משרד, למשל acme.lvh.me"

# --- Cases / assignments ---
CASE_HAS_CONTENT_CANNOT_DELETE = "לתיק זה יש שעות עבודה או מסמכים מקושרים ולא ניתן למחוק אותו — יש לסגור את התיק במקום זאת"
ONLY_LAWYERS_CLIENTS_CAN_BE_ASSIGNED = "ניתן לשייך לתיק רק עורכי דין ולקוחות — מנהל/ת משרד כבר בעל/ת גישה לכל תיק"
ALREADY_ASSIGNED_TO_CASE = "השיוך לתיק זה כבר קיים"
NOT_ASSIGNED_TO_CASE = "אינך משויך/ת לתיק זה"

# --- Documents ---
ALREADY_ARCHIVED = "המסמך כבר נמצא בארכיון"
DOCUMENT_NOT_ARCHIVED = "המסמך אינו נמצא בארכיון"
ONLY_ARCHIVED_CAN_BE_PERMANENTLY_DELETED = "ניתן למחוק לצמיתות רק מסמכים שבארכיון — יש להעביר לארכיון תחילה"
CASE_CLOSED_CANNOT_ADD_DOCUMENTS = "התיק סגור — לא ניתן להוסיף מסמכים חדשים"
CLIENTS_UPLOAD_TO_CLIENT_FOLDER_ONLY = "לקוחות יכולים להעלות מסמכים לתיקיית הלקוח בלבד"
UNSUPPORTED_FILE_TYPE_DOCUMENT = "סוג קובץ לא נתמך — סוגים מותרים: PDF, DOCX, JPEG, PNG"
CLIENTS_CANNOT_BROWSE_ARCHIVE = "ללקוחות אין גישה לצפייה בארכיון"
CLIENTS_SEE_CLIENT_FOLDER_ONLY = "לקוחות יכולים לצפות רק בתיקיית הלקוח"
CLIENTS_ARCHIVE_OWN_UPLOADS_ONLY = "לקוחות יכולים להעביר לארכיון רק קבצים שהם עצמם העלו"

# --- Work logs ---
CASE_CLOSED_CANNOT_ADD_WORK_LOGS = "התיק סגור — לא ניתן להוסיף רישומי שעות חדשים"
CASE_CLOSED_CANNOT_EDIT_WORK_LOGS = "התיק סגור — לא ניתן לערוך רישומי שעות"
CASE_CLOSED_CANNOT_DELETE_WORK_LOGS = "התיק סגור — לא ניתן למחוק רישומי שעות"

# --- Members / invites ---
CANNOT_DEACTIVATE_OWN_MEMBERSHIP = "לא ניתן להסיר את החברות של עצמך"
ONLY_MANAGERS_LAWYERS_ON_PUBLIC_PAGE = "רק מנהלי משרד ועורכי דין יכולים להופיע בעמוד הציבורי"
MEMBERSHIP_NOT_ACTIVE = "החברות הזו אינה פעילה"
ONLY_LAWYER_CLIENT_INVITES_SUPPORTED = "ניתן להזמין רק עורכי דין או לקוחות"
ALREADY_MEMBER_OF_FIRM = "האדם הזה כבר חבר/ה במשרד שלך"
INVITE_ALREADY_PENDING = "כבר קיימת הזמנה ממתינה עבור אימייל זה"
ROLE_CHANGE_ONLY_FOR_LAWYER_OR_MANAGER = "ניתן להחליף תפקיד רק בין עורך/ת דין למנהל/ת משרד"
INVITE_NOT_PENDING = "ניתן לבטל רק הזמנות שממתינות למענה"
HOURLY_RATE_ONLY_FOR_LAWYERS = "ניתן להגדיר תעריף שעתי רק לעורכי דין"
MANAGER_STATUS_ONLY_FOR_LAWYERS = "ניתן להעניק סטטוס מנהל/ת רק לעורכי דין"

# --- Subscriptions ---
ALREADY_ON_THIS_PLAN = "המשרד כבר נמצא בתוכנית הזו"

# --- Narratives ---
PERIOD_END_BEFORE_START = "תאריך הסיום אינו יכול להיות לפני תאריך ההתחלה"

# --- Branding / logo ---
ONLY_JPEG_PNG_LOGOS_ALLOWED = "עבור לוגו ניתן להעלות רק תמונות מסוג JPEG או PNG"

# --- Excel import ---
FILE_TOO_LARGE = "הקובץ גדול מדי"
UNSUPPORTED_FILE_TYPE_XLSX = "סוג קובץ לא נתמך — יש להעלות את תבנית ה-xlsx"


def account_logs_in_through_other_portal(other_portal_name: str) -> str:
    return f"חשבון זה מתחבר דרך {other_portal_name}, לא דרך הפורטל הנוכחי"


def platform_login_must_be_made_to(host: str) -> str:
    return f"התחברות לפלטפורמה חייבת להתבצע בכתובת {host}"


def logo_file_exceeds_limit(max_mb: int) -> str:
    return f"קובץ הלוגו חורג מהמגבלה של {max_mb}MB"


def document_file_exceeds_limit(max_mb: int) -> str:
    return f"הקובץ חורג מהמגבלה של {max_mb}MB"


def document_name_already_exists(filename: str) -> str:
    return f'מסמך בשם "{filename}" כבר קיים בתיקייה זו — יש להעלות שוב כדי להחליף אותו'


def storage_quota_exceeded(limit_gb: int) -> str:
    return f"מכסת האחסון של התוכנית ({limit_gb}GB) נוצלה במלואה — יש לפנות מקום או לשדרג תוכנית"


def lawyer_limit_reached(limit: int) -> str:
    return f"הגעתם למגבלת עורכי הדין של התוכנית ({limit}) — יש להסיר עורך/ת דין או לשדרג תוכנית"


# --- Excel import row-level errors (shared/worklog_import.py) ---
def import_could_not_read_file() -> str:
    return "לא ניתן לקרוא את הקובץ — האם זהו קובץ xlsx תקין?"


def import_file_is_empty() -> str:
    return "הקובץ ריק"


def import_expected_columns(expected_headers: str) -> str:
    return f"עמודות צפויות: {expected_headers} — יש להשתמש בתבנית שהורדתם"


def import_no_data_rows() -> str:
    return "הקובץ אינו מכיל שורות נתונים"


def import_too_many_rows(max_rows: int) -> str:
    return f"יותר מדי שורות — מקסימום {max_rows} בייבוא אחד"


def import_lawyer_email_required() -> str:
    return "יש להזין אימייל של עורך/ת דין"


def import_no_active_lawyer(email: str) -> str:
    return f"לא נמצא/ה עורך/ת דין פעיל/ה במשרד זה עם האימייל '{email}'"


def import_case_required() -> str:
    return "יש לבחור תיק מהרשימה הנפתחת"


def import_invalid_date() -> str:
    return "התאריך אינו תקין (הפורמט הנדרש: DD/MM/YYYY)"


def import_invalid_hours(max_hours) -> str:
    return f"מספר השעות חייב להיות חיובי ועד {max_hours}"


def import_case_not_found(case_id: int) -> str:
    return f"תיק מספר {case_id} לא נמצא במשרד זה"


def import_case_closed(case_id: int, case_title: str) -> str:
    return f'תיק מספר {case_id} ("{case_title}") סגור'


def import_lawyer_not_assigned(case_id: int) -> str:
    return f"עורך/ת הדין אינו/ה משויך/ת לתיק מספר {case_id}"


def import_duplicate_within_file(other_row: int) -> str:
    return f"שורה כפולה — זהה לשורה {other_row} בקובץ זה"


def import_duplicate_of_existing() -> str:
    return "רישום זהה כבר קיים ביומן השעות"


def import_failed_summary(error_count: int) -> str:
    return f"הייבוא נכשל — {error_count} שורות הכילו שגיאות, דבר לא יובא"


# --- Pydantic auto-generated validation messages, translated by stable
# error `type` code (see shared/errors.py's validation_exception_handler).
# Deliberately covers only the constraint kinds actually used by this
# codebase's schemas today (see server/*/schemas/*.py) rather than every
# possible Pydantic error type — a reasonable, documented scope boundary
# for a project this size, not an oversight.
def _string_too_short(ctx):
    return f"יש להזין לפחות {ctx.get('min_length')} תווים"


def _string_too_long(ctx):
    return f"ניתן להזין עד {ctx.get('max_length')} תווים"


def _string_pattern_mismatch(ctx):
    return "הערך אינו תואם לפורמט הנדרש"


def _greater_than(ctx):
    return f"הערך חייב להיות גדול מ-{ctx.get('gt')}"


def _greater_than_equal(ctx):
    return f"הערך חייב להיות גדול או שווה ל-{ctx.get('ge')}"


def _less_than_equal(ctx):
    return f"הערך חייב להיות קטן או שווה ל-{ctx.get('le')}"


def _missing(ctx):
    return "שדה חובה חסר"


def _enum(ctx):
    return "ערך לא חוקי עבור שדה זה"


def _contains_hebrew(text: str) -> bool:
    return any("֐" <= ch <= "׿" for ch in text)


def _value_error(ctx, raw_msg):
    # Pydantic wraps a custom model_validator's raised ValueError as
    # "Value error, <our message>" — our own validators (e.g. narratives'
    # period check) already raise a Hebrew message via this catalog, so
    # passing it through unchanged is correct. Only a *library*-generated
    # value_error (e.g. EmailStr's own English "value is not a valid email
    # address") actually needs translating here.
    if _contains_hebrew(raw_msg):
        return raw_msg.removeprefix("Value error, ")
    return "כתובת אימייל אינה תקינה" if "email" in raw_msg.lower() else "ערך לא תקין"


PYDANTIC_TYPE_TRANSLATORS = {
    "string_too_short": _string_too_short,
    "string_too_long": _string_too_long,
    "string_pattern_mismatch": _string_pattern_mismatch,
    "greater_than": _greater_than,
    "greater_than_equal": _greater_than_equal,
    "less_than_equal": _less_than_equal,
    "missing": _missing,
    "enum": _enum,
}


def translate_pydantic_error(error: dict) -> str:
    """Best-effort Hebrew translation of one Pydantic error dict (from
    RequestValidationError.errors()), keyed by its stable `type` code.
    Falls back to the library's own English message for a type this
    catalog doesn't cover — better an occasional English message than a
    broken/blank one, and it's a visible gap to close later rather than a
    silent one.
    """
    error_type = error.get("type", "")
    if error_type == "value_error":
        return _value_error(error.get("ctx", {}), error.get("msg", ""))
    translator = PYDANTIC_TYPE_TRANSLATORS.get(error_type)
    if translator is not None:
        return translator(error.get("ctx", {}))
    return error.get("msg", "קלט לא תקין")
