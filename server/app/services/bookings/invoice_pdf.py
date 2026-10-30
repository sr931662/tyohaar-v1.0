"""
Customer invoice PDF.

`build_invoice_pdf` is a pure function from `InvoiceData` to PDF bytes, so the
layout is testable without a database. The service layer assembles the data
from the booking and its snapshotted lines; nothing here reads a live package,
so an invoice never changes after the fact.

Every line carries one of three labels, printed as a coloured badge *and*
spelled out in a legend, so nobody has to guess what they keep and what goes
back:

    RENTAL   returnable item — returned after the event
    KEEP     the customer keeps it
    SERVICE  a service, not a product

Vendor identities are deliberately absent: customers never see them.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import date, time
from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

_FONTS = Path(__file__).resolve().parents[2] / "assets" / "fonts"
FONT, FONT_BOLD = "TyDejaVu", "TyDejaVu-Bold"

_registered = False


def _register_fonts() -> None:
    """DejaVu Sans (free licence) because the built-in PDF fonts have no ₹."""
    global _registered
    if _registered:
        return
    pdfmetrics.registerFont(TTFont(FONT, str(_FONTS / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(_FONTS / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=FONT_BOLD, italic=FONT, boldItalic=FONT_BOLD)
    _registered = True


KIND_LABELS = {
    "rental": ("RENTAL", "#2F7A4B", "#E3F2E8", "Returnable item — please hand it back after the event"),
    "keep": ("KEEP", "#9A6A00", "#FBF0D6", "Yours to keep"),
    "service": ("SERVICE", "#2F4F9A", "#E5ECFA", "A service, not a product"),
}
BRAND = colors.HexColor("#8A1F3D")
INK = colors.HexColor("#2A2018")
MUTED = colors.HexColor("#6B5D50")
LINE = colors.HexColor("#E3DACB")


@dataclass
class InvoiceLine:
    kind: str                      # rental | keep | service
    name: str
    quantity: int
    unit: str | None
    unit_price: Decimal
    total: Decimal
    note: str | None = None        # what the customer asked for, e.g. "ANITA 30"
    is_addon: bool = False


@dataclass
class InvoiceData:
    invoice_number: str
    issued_on: date
    booking_number: str
    booking_status: str
    payment_status: str
    package_name: str | None
    celebration_title: str | None
    event_date: date
    start_time: time | None
    end_time: time | None
    venue: list[str]
    customer_name: str | None
    customer_phone: str | None
    customer_email: str | None
    lines: list[InvoiceLine]
    subtotal: Decimal
    discount: Decimal
    taxable: Decimal
    tax: Decimal
    platform_fee: Decimal
    total: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    balloon_colors: list[tuple[str, str]] = field(default_factory=list)   # (name, #hex) in the order chosen
    balloon_finish: str | None = None
    customization_note: str | None = None
    special_instructions: str | None = None
    currency_symbol: str = "₹"
    gst_rate_percent: int = 18


def inr(amount: Decimal | int | float, symbol: str = "₹") -> str:
    """₹12,34,567.50 — Indian digit grouping; paise shown only when present."""
    value = Decimal(str(amount)).quantize(Decimal("0.01"))
    sign = "-" if value < 0 else ""
    whole, _, frac = f"{abs(value):.2f}".partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return f"{sign}{symbol}{whole}" + ("" if frac == "00" else f".{frac}")


def _fmt_time(t: time | None) -> str:
    return t.strftime("%I:%M %p").lstrip("0") if t else ""


def _styles() -> dict[str, ParagraphStyle]:
    base = dict(fontName=FONT, textColor=INK, fontSize=9, leading=12.5)
    return {
        "body": ParagraphStyle("body", **base),
        "small": ParagraphStyle("small", **{**base, "fontSize": 7.8, "leading": 10.5, "textColor": MUTED}),
        "label": ParagraphStyle("label", **{**base, "fontName": FONT_BOLD, "fontSize": 7.5, "textColor": MUTED, "leading": 10}),
        "h1": ParagraphStyle("h1", **{**base, "fontName": FONT_BOLD, "fontSize": 22, "leading": 26, "textColor": BRAND}),
        "title": ParagraphStyle("title", **{**base, "fontName": FONT_BOLD, "fontSize": 16, "leading": 20, "alignment": TA_RIGHT}),
        "right": ParagraphStyle("right", **{**base, "alignment": TA_RIGHT}),
        "boldright": ParagraphStyle("boldright", **{**base, "fontName": FONT_BOLD, "alignment": TA_RIGHT}),
        "bold": ParagraphStyle("bold", **{**base, "fontName": FONT_BOLD}),
        "h2": ParagraphStyle("h2", **{**base, "fontName": FONT_BOLD, "fontSize": 10.5, "leading": 14, "textColor": BRAND}),
        "cell": ParagraphStyle("cell", **{**base, "fontSize": 8.6, "leading": 11.5}),
        "badge": ParagraphStyle("badge", **{**base, "fontName": FONT_BOLD, "fontSize": 7.4, "leading": 9, "alignment": 1}),
    }


def _p(text: str | None, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text or "—").replace("\n", "<br/>"), style)


def _two_col(left, right, widths=(90 * mm, 90 * mm)) -> Table:
    t = Table([[left, right]], colWidths=widths)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
    return t


def _info_block(title: str, rows: list[tuple[str, str | None]], st) -> list:
    out = [Paragraph(escape(title.upper()), st["label"]), Spacer(1, 2)]
    for label, value in rows:
        if value:
            out.append(Paragraph(f"<font color='#6B5D50'>{escape(label)}</font>&nbsp;&nbsp;{escape(value)}", st["body"]))
    return out


def build_invoice_pdf(d: InvoiceData) -> bytes:
    _register_fonts()
    st = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=16 * mm,
        title=f"Invoice {d.invoice_number}", author="Tyohaar", subject=f"Booking {d.booking_number}",
    )
    # SimpleDocTemplate's frame keeps 6pt of padding each side; size to what is really usable.
    width = A4[0] - 32 * mm - 12
    sym = d.currency_symbol
    story: list = []

    # ── Header ────────────────────────────────────────────────────────────────
    header = Table(
        [[Paragraph("Tyohaar", st["h1"]),
          [Paragraph("INVOICE", st["title"]),
           Paragraph(f"No. {escape(d.invoice_number)}", st["right"]),
           Paragraph(f"Date {d.issued_on.strftime('%d %b %Y')}", st["right"])]]],
        colWidths=[width * 0.5, width * 0.5],
    )
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, 0), 1.2, BRAND),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story += [header, Spacer(1, 8)]

    # ── Booking + customer ────────────────────────────────────────────────────
    when = d.event_date.strftime("%A, %d %B %Y")
    clock = ""
    if d.start_time:
        clock = _fmt_time(d.start_time) + (f" - {_fmt_time(d.end_time)}" if d.end_time else "")
    paid_label = d.payment_status.replace("_", " ").title()
    story.append(_two_col(
        _info_block("Booking", [
            ("Booking no.", d.booking_number),
            ("Package", d.package_name),
            ("Celebration", d.celebration_title),
            ("Event date", when),
            ("Time", clock or None),
            ("Status", d.booking_status.replace("_", " ").title()),
            ("Payment", paid_label),
        ], st),
        _info_block("Billed to", [
            ("Name", d.customer_name),
            ("Phone", d.customer_phone),
            ("Email", d.customer_email),
            ("Venue", ", ".join(v for v in d.venue if v) or None),
        ], st),
    ))
    story.append(Spacer(1, 10))

    # ── Balloon décor ─────────────────────────────────────────────────────────
    if d.balloon_colors or d.balloon_finish:
        cells, widths, style = [], [], [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]
        cells.append(Paragraph("BALLOON DÉCOR", st["label"]))
        widths.append(30 * mm)
        for i, (name, hexcode) in enumerate(d.balloon_colors, start=1):
            cells.append("")
            widths.append(5 * mm)
            style += [("BACKGROUND", (len(cells) - 1, 0), (len(cells) - 1, 0), colors.HexColor(hexcode)),
                      ("BOX", (len(cells) - 1, 0), (len(cells) - 1, 0), 0.5, LINE)]
            cells.append(Paragraph(f"{i}. {escape(name)}", st["body"]))
            widths.append(26 * mm)
        if d.balloon_finish:
            cells.append(Paragraph(f"Finish: <b>{escape(d.balloon_finish)}</b>", st["body"]))
            widths.append(40 * mm)
        deco = Table([cells], colWidths=widths, rowHeights=[7 * mm])
        deco.setStyle(TableStyle(style))
        story += [deco, Spacer(1, 10)]

    # ── Lines ─────────────────────────────────────────────────────────────────
    head = ["Type", "Item", "Qty", "Rate", "Amount"]
    rows = [[Paragraph(h, st["label"]) for h in head[:2]] + [Paragraph(h, st["label"]) for h in head[2:]]]
    style = [
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, LINE),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
    ]
    for i, line in enumerate(d.lines, start=1):
        label, fg, bg, _meaning = KIND_LABELS.get(line.kind, KIND_LABELS["keep"])
        name = f"<b>{escape(line.name)}</b>" + (" <font color='#6B5D50'>(add-on)</font>" if line.is_addon else "")
        if line.note:
            name += f"<br/><font color='#6B5D50'>Custom: </font><b>{escape(line.note)}</b>"
        qty = f"{line.quantity}" + (f" {escape(line.unit)}" if line.unit else "")
        badge = Paragraph(f"<font color='{fg}'>{label}</font>", st["badge"])
        rows.append([badge, Paragraph(name, st["cell"]), Paragraph(qty, st["right"]),
                     Paragraph(inr(line.unit_price, sym), st["right"]), Paragraph(inr(line.total, sym), st["boldright"])])
        style += [("BACKGROUND", (0, i), (0, i), colors.HexColor(bg)), ("BOX", (0, i), (0, i), 0.6, colors.HexColor(fg))]
    if len(rows) == 1:
        rows.append([Paragraph("—", st["body"]), Paragraph("Package base price only", st["cell"]), "", "", ""])
    table = Table(rows, colWidths=[22 * mm, width - 22 * mm - 22 * mm - 28 * mm - 30 * mm, 22 * mm, 28 * mm, 30 * mm], repeatRows=1)
    table.setStyle(TableStyle(style))
    story += [Paragraph("Items &amp; services", st["h2"]), Spacer(1, 4), table, Spacer(1, 6)]

    # Legend: only the labels actually used, spelled out.
    used = []
    for k in ("rental", "keep", "service"):
        if any(line.kind == k for line in d.lines):
            label, fg, bg, meaning = KIND_LABELS[k]
            used.append([Paragraph(f"<font color='{fg}'>{label}</font>", st["badge"]), Paragraph(meaning, st["small"])])
    if used:
        legend = Table(used, colWidths=[22 * mm, width - 22 * mm])
        ls = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
        for i, k in enumerate([k for k in ("rental", "keep", "service") if any(line.kind == k for line in d.lines)]):
            ls += [("BACKGROUND", (0, i), (0, i), colors.HexColor(KIND_LABELS[k][2])), ("BOX", (0, i), (0, i), 0.6, colors.HexColor(KIND_LABELS[k][1]))]
        legend.setStyle(TableStyle(ls))
        story += [Paragraph("What the labels mean", st["label"]), Spacer(1, 3), legend, Spacer(1, 8)]

    # ── Totals ────────────────────────────────────────────────────────────────
    tot = [("Package &amp; items", d.subtotal, False)]
    if d.discount > 0:
        tot.append(("Discount", -d.discount, False))
    # GST is an admin switch: a booking made while it was off carries no tax,
    # and shows no GST row rather than a misleading "GST @ 18%: ₹0".
    if d.tax > 0:
        tot.append((f"GST @ {d.gst_rate_percent}%", d.tax, False))
    if d.platform_fee > 0:
        tot.append(("Platform fee", d.platform_fee, False))
    tot.append(("Total", d.total, True))
    if d.amount_paid > 0:
        tot.append(("Paid", d.amount_paid, False))
    tot.append(("Balance due", d.amount_due, True))
    trows = [[Paragraph(label, st["bold" if bold else "body"]), Paragraph(inr(val, sym), st["boldright" if bold else "right"])] for label, val, bold in tot]
    ttable = Table(trows, colWidths=[40 * mm, 34 * mm], hAlign="RIGHT")
    ts = [("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    for i, (_l, _v, bold) in enumerate(tot):
        if bold:
            ts.append(("LINEABOVE", (0, i), (-1, i), 0.8, INK))
    ttable.setStyle(TableStyle(ts))
    story += [KeepTogether([ttable]), Spacer(1, 10)]

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes = []
    if d.customization_note:
        notes += [Paragraph("YOUR CUSTOMISATION NOTE", st["label"]), _p(d.customization_note, st["body"]), Spacer(1, 4)]
    if d.special_instructions:
        notes += [Paragraph("SPECIAL INSTRUCTIONS", st["label"]), _p(d.special_instructions, st["body"]), Spacer(1, 4)]
    story += notes

    story += [
        Spacer(1, 6),
        Paragraph(
            "Items marked RENTAL remain the property of the vendor and must be returned after the event in the condition they "
            "were supplied; damage or loss may be chargeable. Items marked KEEP are yours to keep. "
            "This is a computer-generated invoice and needs no signature.", st["small"]),
    ]

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont(FONT, 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(16 * mm, 9 * mm, f"Tyohaar  |  Invoice {d.invoice_number}  |  Booking {d.booking_number}")
        canvas.drawRightString(A4[0] - 16 * mm, 9 * mm, f"Page {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
