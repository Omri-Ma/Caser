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

from shared.models import Case, WorkLog
from shared.models.enums import NarrativeLanguage

# Fixed-template version per CLAUDE.md's Phase 3 scope ("no real AI/LLM
# needed, this is intentionally simple") — a flat hourly rate stands in for
# whatever a real billing engine would derive per-lawyer/per-matter-type.
HOURLY_RATE = Decimal("450.00")

# Currency is always rendered as plain text, never the ₪ glyph (CLAUDE.md:
# a currency symbol is a font-rendering problem for no real benefit here).
CURRENCY_TEXT = {
    NarrativeLanguage.HE: 'ש"ח',  # ש"ח
    NarrativeLanguage.EN: "ILS",
}

_FONTS_DIR = Path(__file__).resolve().parents[2] / "shared" / "fonts"
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


def compute_case_totals(case_id: int, tenant_id: int, db, period_start: date, period_end: date) -> tuple[Decimal, Decimal]:
    """Sums only the WorkLogs falling inside [period_start, period_end] —
    real legal billing is period-by-period, not every hour ever logged on
    the case (CLAUDE.md). Returns (total_hours, total_fee) as Decimals ready
    to store on a new Narrative row.
    """
    hours = [
        wl.hours
        for wl in db.query(WorkLog.hours).filter(
            WorkLog.tenant_id == tenant_id,
            WorkLog.case_id == case_id,
            WorkLog.date >= period_start,
            WorkLog.date <= period_end,
        )
    ]
    total_hours = sum((Decimal(h) for h in hours), Decimal("0"))
    total_fee = (total_hours * HOURLY_RATE).quantize(Decimal("0.01"))
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
    English copy, `he` is real Hebrew copy — CLAUDE.md is explicit that `en`
    is "the easy case" while `he` is "real work, not just template text
    swapped in", and that extends to the wording itself, not only the font.
    """
    currency = CURRENCY_TEXT[language]
    if language == NarrativeLanguage.HE:
        return (
            f'סיכום שכר טרחה "{case.title}" (תיק #{case.id}).\n\n'
            f"התקופה המדווחת: {period_start:%d/%m/%Y} עד {period_end:%d/%m/%Y}.\n\n"
            f"סך שעות העבודה בתקופה זו: {total_hours:.2f} שעות.\n"
            f"בחיוב לפי תעריף קבוע של {HOURLY_RATE:.2f} {currency} לשעה, "
            f"סך השכר לתקופה זו עומד על {total_fee:.2f} {currency}.\n\n"
            f"סיכום זה משקף את כל רשומות יומן העבודה "
            f"שנרשמו בתקופה זו. סיכום חדש יחליף את זה "
            f"אם ייוצר מחדש; רשומה זו תישאר בהיסטוריית התיק."
        )
    return (
        f'Narrative summary for case "{case.title}" (case #{case.id}).\n\n'
        f"Billing period: {period_start:%d/%m/%Y} to {period_end:%d/%m/%Y}.\n\n"
        f"Total billable hours recorded in this period: {total_hours:.2f}.\n"
        f"Billed at a flat rate of {HOURLY_RATE:.2f} {currency} per hour, "
        f"the total fee for this narrative is {total_fee:.2f} {currency}.\n\n"
        f"This narrative reflects all work log entries recorded on this case "
        f"within the period above. A new narrative supersedes this one "
        f"if generated again; this row remains in the case's narrative history."
    )


def build_narrative_pdf(case: Case, narrative) -> bytes:
    """Renders one Narrative row into a simple single-page PDF. `language`
    only changes which template sentences were used (CLAUDE.md) — it does
    NOT mean the whole document is guaranteed to be one script. Real domain
    data embedded in either version (case title, WorkLog descriptions, a
    lawyer/client's name) is typed in Hebrew regardless of narrative
    language, since that's how it was entered everywhere else in the app.
    So the Hebrew-glyph embedded font is used for BOTH languages (an
    earlier version of this only registered/used it for `he`, which
    produced missing-glyph boxes wherever Hebrew data appeared inside an
    otherwise-English `en` document) — only paragraph alignment (right for
    `he`, left for `en`) actually depends on the chosen language. Every
    line, in both languages, is passed through python-bidi's get_display
    (the Unicode Bidi Algorithm, given an explicit base direction matching
    the paragraph alignment) before drawing — reportlab has no automatic
    RTL shaping the way a browser does, and a line can carry a Hebrew name
    inside an English sentence (or vice versa) either way.
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

    def draw_line(text: str, y: float) -> None:
        rendered = get_display(text, base_dir=base_dir)
        if is_hebrew:
            pdf.drawRightString(right_edge, y, rendered)
        else:
            pdf.drawString(margin, y, rendered)

    y = height - margin
    pdf.setFont(font_bold, 16)
    draw_line("סיכום שכר טרחה" if is_hebrew else "Case Narrative", y)
    y -= 1 * cm

    pdf.setFont(font, 11)
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

    pdf.setFont(font, 10)
    for paragraph in narrative.generated_text.split("\n\n"):
        for line in _wrap_text(pdf, paragraph, font, 10, max_width, base_dir):
            if y < margin:
                pdf.showPage()
                pdf.setFont(font, 10)
                y = height - margin
            draw_line(line, y)
            y -= 0.5 * cm
        y -= 0.3 * cm

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


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
