from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from shared.models import Case, Identity, Membership, WorkLog
from shared.models.enums import NarrativeLanguage

# In server/shared on purpose, not duplicated per app (unlike pagination.py/
# errors.py) — same reasoning as storage.py/plan_limits.py/password_reset.py:
# narrative generation/export is manager-level authority now (CLAUDE.md's
# Narratives note), and a manager-authority lawyer still only ever uses
# client/, never admin/. Both admin_api (office_manager) and client_api
# (a lawyer with Memberships.is_manager set) expose their own thin route
# to these functions, each enforcing its own side's authorization check —
# the actual PDF/text-generation logic itself must be identical either way,
# which is exactly the kind of cross-app invariant this package is for.

# Currency is always rendered as plain text, never the ₪ glyph (CLAUDE.md:
# a currency symbol is a font-rendering problem for no real benefit here).
CURRENCY_TEXT = {
    NarrativeLanguage.HE: 'ש"ח',  # ש"ח
    NarrativeLanguage.EN: "ILS",
}

_FONTS_DIR = Path(__file__).resolve().parent / "fonts"
_HEBREW_FONT_NAME = "Alef"
_HEBREW_FONT_BOLD_NAME = "Alef-Bold"
_hebrew_font_registered = False


def _ensure_hebrew_font_registered() -> None:
    """Registers the bundled Alef TTF (real Hebrew glyphs, SIL OFL licensed)
    with reportlab exactly once. Needed because reportlab's built-in fonts
    (Helvetica, etc.) have no Hebrew glyphs at all — CLAUDE.md calls this out
    explicitly as real work, not template text swapped in.
    """
    global _hebrew_font_registered
    if _hebrew_font_registered:
        return
    pdfmetrics.registerFont(TTFont(_HEBREW_FONT_NAME, str(_FONTS_DIR / "Alef-Regular.ttf")))
    pdfmetrics.registerFont(TTFont(_HEBREW_FONT_BOLD_NAME, str(_FONTS_DIR / "Alef-Bold.ttf")))
    _hebrew_font_registered = True


def get_case_work_logs_in_period(
    case_id: int, tenant_id: int, db: Session, period_start: date, period_end: date
) -> list[tuple[WorkLog, str]]:
    """WorkLogs (+ the lawyer's display name) inside [period_start,
    period_end], oldest first — the same rows both compute_case_totals sums
    and the PDF's itemized table lists, so the two can never silently drift
    apart into different underlying data.
    """
    return (
        db.query(WorkLog, Identity.name)
        .join(Membership, WorkLog.lawyer_id == Membership.id)
        .join(Identity, Membership.identity_id == Identity.id)
        .filter(
            WorkLog.tenant_id == tenant_id,
            WorkLog.case_id == case_id,
            WorkLog.date >= period_start,
            WorkLog.date <= period_end,
        )
        .order_by(WorkLog.date, WorkLog.id)
        .all()
    )


def compute_case_totals(case_id: int, tenant_id: int, db: Session, period_start: date, period_end: date) -> tuple[Decimal, Decimal]:
    """Sums only the WorkLogs falling inside [period_start, period_end] —
    real legal billing is period-by-period, not every hour ever logged on
    the case (CLAUDE.md). The fee is no longer a single flat rate: each
    WorkLog is billed at *its own lawyer's* Memberships.hourly_rate
    (CLAUDE.md's Memberships note — replaces the old platform-wide
    placeholder rate), summed across every entry in the period. A lawyer
    with no rate set yet contributes 0 for their hours rather than raising
    — an unset rate is a real, if incomplete, state to bill against, not an
    error condition.
    """
    work_logs = get_case_work_logs_in_period(case_id, tenant_id, db, period_start, period_end)
    total_hours = sum((Decimal(wl.hours) for wl, _ in work_logs), Decimal("0"))

    rate_by_membership: dict[int, Decimal] = {}
    total_fee = Decimal("0")
    for wl, _lawyer_name in work_logs:
        rate = rate_by_membership.get(wl.lawyer_id)
        if rate is None:
            membership = db.query(Membership).filter(Membership.id == wl.lawyer_id).first()
            rate = membership.hourly_rate if membership and membership.hourly_rate is not None else Decimal("0")
            rate_by_membership[wl.lawyer_id] = rate
        total_fee += Decimal(wl.hours) * rate
    total_fee = total_fee.quantize(Decimal("0.01"))
    return total_hours, total_fee


def generate_narrative_text(
    case: Case,
    total_hours: Decimal,
    total_fee: Decimal,
    language: NarrativeLanguage,
    period_start: date,
    period_end: date,
) -> str:
    """Fixed-template narrative body — no LLM call, per CLAUDE.md. Kept plain
    text (no markup) since it's stored as-is and also fed directly into the
    PDF export below. Two real templates (not just a currency swap): `en` is
    English copy, `he` is real Hebrew copy. No longer states a single flat
    hourly rate (each lawyer on the case may bill at a different
    Memberships.hourly_rate) — the itemized WorkLog table in the exported
    PDF is where the per-entry detail actually lives; this text only states
    the period totals.
    """
    currency = CURRENCY_TEXT[language]
    if language == NarrativeLanguage.HE:
        return (
            f'סיכום שכר טרחה "{case.title}" (תיק #{case.id}).\n\n'
            f"התקופה המדווחת: {period_start:%d/%m/%Y} עד {period_end:%d/%m/%Y}.\n\n"
            f"סך שעות העבודה בתקופה זו: {total_hours:.2f} שעות.\n"
            f"בחיוב לפי תעריף השעה של כל עורך/ת דין שעבד/ה על התיק בתקופה זו, "
            f"סך השכר לתקופה זו עומד על {total_fee:.2f} {currency} "
            f"(פירוט מלא בטבלת רישומי השעות המצורפת).\n\n"
            f"סיכום זה משקף את כל רשומות יומן העבודה "
            f"שנרשמו בתקופה זו. סיכום חדש יחליף את זה "
            f"אם ייוצר מחדש; רשומה זו תישאר בהיסטוריית התיק."
        )
    return (
        f'Narrative summary for case "{case.title}" (case #{case.id}).\n\n'
        f"Billing period: {period_start:%d/%m/%Y} to {period_end:%d/%m/%Y}.\n\n"
        f"Total billable hours recorded in this period: {total_hours:.2f}.\n"
        f"Billed at each assigned lawyer's own hourly rate for this period, "
        f"the total fee for this narrative is {total_fee:.2f} {currency} "
        f"(see the itemized work log table below for the full breakdown).\n\n"
        f"This narrative reflects all work log entries recorded on this case "
        f"within the period above. A new narrative supersedes this one "
        f"if generated again; this row remains in the case's narrative history."
    )


def build_narrative_pdf(case: Case, narrative, work_log_rows: list[tuple[WorkLog, str]]) -> bytes:
    """Renders one Narrative row into a PDF: header facts, the narrative
    text, then an itemized table of every WorkLog in the period (date,
    lawyer, description, hours) — the underlying detail a client or auditor
    would actually want to check against the fee figure (CLAUDE.md's
    Narratives note).

    `language` only changes which template sentences were used (CLAUDE.md)
    — it does NOT mean the whole document is guaranteed to be one script.
    Real domain data embedded in either version (case title, WorkLog
    descriptions, a lawyer/client's name) is typed in Hebrew regardless of
    narrative language, since that's how it was entered everywhere else in
    the app. So the Hebrew-glyph embedded font is used for BOTH languages
    (an earlier version of this only registered/used it for `he`, which
    produced missing-glyph boxes wherever Hebrew data appeared inside an
    otherwise-English `en` document) — only paragraph alignment (right for
    `he`, left for `en`) actually depends on the chosen language. Every
    line, in both languages, is passed through python-bidi's get_display
    (given an explicit base direction matching the paragraph alignment)
    before drawing — reportlab has no automatic RTL shaping the way a
    browser does, and a line can carry a Hebrew name inside an English
    sentence (or vice versa) either way.
    """
    is_hebrew = narrative.language == NarrativeLanguage.HE
    _ensure_hebrew_font_registered()
    font, font_bold = _HEBREW_FONT_NAME, _HEBREW_FONT_BOLD_NAME
    base_dir = "R" if is_hebrew else "L"

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 2 * cm
    right_edge = width - margin
    max_width = width - 2 * margin

    def draw_line(text: str, y: float, use_font: str = font, size: int = 10) -> None:
        pdf.setFont(use_font, size)
        rendered = get_display(text, base_dir=base_dir)
        if is_hebrew:
            pdf.drawRightString(right_edge, y, rendered)
        else:
            pdf.drawString(margin, y, rendered)

    def new_page_if_needed(y: float) -> float:
        if y < margin:
            pdf.showPage()
            return height - margin
        return y

    y = height - margin
    draw_line("סיכום שכר טרחה" if is_hebrew else "Case Narrative", y, font_bold, 16)
    y -= 1 * cm

    header_lines = (
        [
            f'תיק: {case.title} (#{case.id})',
            f"סיכום מס' {narrative.id} — הופק בתאריך {narrative.created_at:%d/%m/%Y %H:%M}",
            f"תקופה: {narrative.period_start:%d/%m/%Y} עד {narrative.period_end:%d/%m/%Y}",
            f'סה"כ שעות: {narrative.total_hours:.2f}',
            f'סה"כ שכר טרחה: {narrative.total_fee:.2f} {CURRENCY_TEXT[NarrativeLanguage.HE]}',
        ]
        if is_hebrew
        else [
            f"Case: {case.title} (#{case.id})",
            f"Narrative #{narrative.id} — generated {narrative.created_at:%Y-%m-%d %H:%M}",
            f"Period: {narrative.period_start:%Y-%m-%d} to {narrative.period_end:%Y-%m-%d}",
            f"Total hours: {narrative.total_hours:.2f}",
            f"Total fee: {narrative.total_fee:.2f} {CURRENCY_TEXT[NarrativeLanguage.EN]}",
        ]
    )
    for line in header_lines:
        draw_line(line, y)
        y -= 0.6 * cm
    y -= 0.4 * cm

    for paragraph in narrative.generated_text.split("\n\n"):
        for line in _wrap_text(pdf, paragraph, font, 10, max_width, base_dir):
            y = new_page_if_needed(y)
            draw_line(line, y)
            y -= 0.5 * cm
        y -= 0.3 * cm

    # Itemized WorkLog table — the detail underneath the summary totals
    # above, so the fee figure can actually be checked against real entries.
    y -= 0.4 * cm
    y = new_page_if_needed(y)
    draw_line("פירוט רישומי שעות" if is_hebrew else "Itemized work log", y, font_bold, 12)
    y -= 0.7 * cm

    # Real columns (fixed x positions per column), not one bidi-joined
    # "date | lawyer | description | hours" string — joining mixed-script,
    # mixed-direction fields into a single line and running the whole thing
    # through get_display reorders the *pipe-separated fields themselves*
    # relative to each other (confirmed visually: a rendered PDF showed
    # "Lawyer | Description | Hours | Date" under a "Date | Lawyer |
    # Description | Hours" header), since the bidi algorithm is meant for
    # natural-language text, not tabular data. Each cell is bidi-processed
    # and drawn independently at its own column position instead, so column
    # N always lines up under column N's header regardless of language.
    column_widths = [w * max_width for w in (0.15, 0.20, 0.50, 0.15)]

    def draw_row(cells: list[str], row_y: float, use_font: str, size: int) -> None:
        pdf.setFont(use_font, size)
        x = right_edge if is_hebrew else margin
        for cell_text, col_width in zip(cells, column_widths):
            truncated = _truncate_to_width(pdf, cell_text, use_font, size, col_width, base_dir)
            rendered = get_display(truncated, base_dir=base_dir)
            if is_hebrew:
                pdf.drawRightString(x, row_y, rendered)
                x -= col_width
            else:
                pdf.drawString(x, row_y, rendered)
                x += col_width

    if not work_log_rows:
        y = new_page_if_needed(y)
        draw_line("אין רישומי שעות בתקופה זו." if is_hebrew else "No work log entries in this period.", y)
        y -= 0.5 * cm
    else:
        column_header = (
            ["תאריך", "עורך/ת דין", "תיאור", "שעות"] if is_hebrew else ["Date", "Lawyer", "Description", "Hours"]
        )
        y = new_page_if_needed(y)
        draw_row(column_header, y, font_bold, 9)
        y -= 0.5 * cm
        for work_log, lawyer_name in work_log_rows:
            date_text = f"{work_log.date:%d/%m/%Y}" if is_hebrew else f"{work_log.date:%Y-%m-%d}"
            y = new_page_if_needed(y)
            draw_row([date_text, lawyer_name, work_log.description, f"{work_log.hours:.2f}"], y, font, 9)
            y -= 0.45 * cm

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _truncate_to_width(pdf: canvas.Canvas, text: str, font: str, size: int, max_width: float, base_dir: str) -> str:
    """Single-line truncation with an ellipsis for a table cell — the
    itemized table's rows stay one line each (unlike the narrative body's
    full paragraph wrapping) so columns stay vertically aligned across rows.
    """
    if pdf.stringWidth(get_display(text, base_dir=base_dir), font, size) <= max_width:
        return text
    ellipsis = "…"
    truncated = text
    while truncated and pdf.stringWidth(get_display(truncated + ellipsis, base_dir=base_dir), font, size) > max_width:
        truncated = truncated[:-1]
    return truncated + ellipsis if truncated else ellipsis


def _wrap_text(pdf: canvas.Canvas, text: str, font: str, size: int, max_width: float, base_dir: str) -> list[str]:
    """Word-wraps on the *logical* string (before bidi reordering) — bidi
    reordering happens per finished line, right before drawing, not here.
    Measures the *displayed* (post-bidi) width, same as draw_line renders,
    since a Hebrew run's reordering doesn't change its rendered width but
    keeps this consistent with what's actually drawn either way.
    """
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        display_width = pdf.stringWidth(get_display(candidate, base_dir=base_dir), font, size)
        if display_width <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]
