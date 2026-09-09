from decimal import Decimal
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from shared.models import Case, WorkLog

# Fixed-template version per CLAUDE.md's Phase 3 scope ("no real AI/LLM
# needed, this is intentionally simple") — a flat hourly rate stands in for
# whatever a real billing engine would derive per-lawyer/per-matter-type.
HOURLY_RATE = Decimal("450.00")


def compute_case_totals(case_id: int, tenant_id: int, db) -> tuple[Decimal, Decimal]:
    """Sums every WorkLog on the case (WorkLogs have no archive concept, so
    this is simply all rows) into total_hours, then derives total_fee at the
    flat HOURLY_RATE. Returns (total_hours, total_fee) as Decimals ready to
    store on a new Narrative row.
    """
    hours = [wl.hours for wl in db.query(WorkLog.hours).filter(WorkLog.tenant_id == tenant_id, WorkLog.case_id == case_id)]
    total_hours = sum((Decimal(h) for h in hours), Decimal("0"))
    total_fee = (total_hours * HOURLY_RATE).quantize(Decimal("0.01"))
    return total_hours, total_fee


def generate_narrative_text(case: Case, total_hours: Decimal, total_fee: Decimal) -> str:
    """Fixed-template narrative body — no LLM call, per CLAUDE.md. Kept plain
    text (no markup) since it's stored as-is and also fed directly into the
    PDF export below.
    """
    return (
        f"Narrative summary for case \"{case.title}\" (case #{case.id}).\n\n"
        f"Total billable hours recorded: {total_hours:.2f}.\n"
        f"Billed at a flat rate of ₪{HOURLY_RATE:.2f} per hour, "
        f"the total fee for this narrative is ₪{total_fee:.2f}.\n\n"
        f"This narrative reflects all work log entries recorded on this case "
        f"as of the time of generation. A new narrative supersedes this one "
        f"if generated again; this row remains in the case's narrative history."
    )


def build_narrative_pdf(case: Case, narrative) -> bytes:
    """Renders one Narrative row into a simple single-page PDF. Plain
    reportlab canvas drawing — no template engine needed for this fixed
    layout.
    """
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 2 * cm

    y = height - margin
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin, y, "Case Narrative")
    y -= 1 * cm

    pdf.setFont("Helvetica", 11)
    pdf.drawString(margin, y, f"Case: {case.title} (#{case.id})")
    y -= 0.6 * cm
    pdf.drawString(margin, y, f"Narrative #{narrative.id} — generated {narrative.created_at:%Y-%m-%d %H:%M}")
    y -= 0.6 * cm
    pdf.drawString(margin, y, f"Total hours: {narrative.total_hours:.2f}")
    y -= 0.6 * cm
    pdf.drawString(margin, y, f"Total fee: ₪{narrative.total_fee:.2f}")
    y -= 1 * cm

    pdf.setFont("Helvetica", 10)
    max_width = width - 2 * margin
    for paragraph in narrative.generated_text.split("\n\n"):
        for line in _wrap_text(pdf, paragraph, "Helvetica", 10, max_width):
            if y < margin:
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                y = height - margin
            pdf.drawString(margin, y, line)
            y -= 0.5 * cm
        y -= 0.3 * cm

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _wrap_text(pdf: canvas.Canvas, text: str, font: str, size: int, max_width: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if pdf.stringWidth(candidate, font, size) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]
