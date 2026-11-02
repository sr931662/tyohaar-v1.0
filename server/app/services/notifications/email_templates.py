"""
HTML email templates.

Email clients (Gmail, Outlook, Apple Mail, phone apps) ignore most modern CSS,
so everything here is table-based with inline styles and system fonts: no
external assets, no flexbox, no media queries that a client might strip. The
layout is a single 600px column that collapses to the screen width on a phone.

Every value that came from a user (names, notes, addresses) goes through
`esc()` before it is placed in markup.
"""

from __future__ import annotations

from datetime import time
from decimal import Decimal
from html import escape

from app.services.bookings.invoice_pdf import InvoiceData, inr

# Brand colours, shared with the PDF invoice and the apps.
INK = "#2A2018"
MUTED = "#6B5D50"
SAFFRON = "#C96E1A"
CREAM = "#F6F1E8"
LINE = "#E8DFD0"
GREEN = "#2E7D4F"


def esc(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)


def shell(*, preheader: str, heading: str, body_html: str, footer_note: str = "") -> str:
    """The branded frame every Tyohaar email shares."""
    return f"""\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>{esc(heading)}</title>
</head>
<body style="margin:0;padding:0;background:{CREAM};">
<span style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">{esc(preheader)}</span>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{CREAM};">
  <tr><td align="center" style="padding:24px 12px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="max-width:600px;background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid {LINE};">
      <tr><td style="background:{SAFFRON};padding:22px 28px;">
        <span style="font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:22px;font-weight:800;letter-spacing:.5px;color:#ffffff;">Tyohaar</span>
      </td></tr>
      <tr><td style="padding:28px 28px 8px;font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:{INK};">
        <h1 style="margin:0 0 6px;font-size:22px;line-height:1.3;color:{INK};">{esc(heading)}</h1>
      </td></tr>
      <tr><td style="padding:0 28px 24px;font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:{INK};">
        {body_html}
      </td></tr>
      <tr><td style="background:{CREAM};padding:16px 28px;font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:12px;line-height:1.6;color:{MUTED};">
        {esc(footer_note) if footer_note else "This is an automated message from Tyohaar. Please don&rsquo;t reply to this email."}
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""


def otp_email(otp: str, purpose_label: str, expire_minutes: int) -> str:
    body = f"""\
<p style="margin:0 0 14px;">Use the code below to {esc(purpose_label)}. It expires in {int(expire_minutes)} minutes.</p>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
  <td align="center" style="background:{CREAM};border-radius:12px;padding:20px;">
    <span style="font-size:32px;font-weight:800;letter-spacing:8px;color:{SAFFRON};">{esc(otp)}</span>
  </td></tr></table>
<p style="margin:16px 0 0;color:{MUTED};font-size:13px;">If you didn&rsquo;t request this code, you can safely ignore this email. Never share it with anyone.</p>"""
    return shell(
        preheader=f"Your Tyohaar code is {otp}",
        heading="Your verification code",
        body_html=body,
    )


# ── Booking emails ────────────────────────────────────────────────────────────

def _fmt_time(t: time | None) -> str:
    return t.strftime("%I:%M %p").lstrip("0") if t else ""


def _when(d: InvoiceData) -> str:
    day = d.event_date.strftime("%A, %d %B %Y")
    start, end = _fmt_time(d.start_time), _fmt_time(d.end_time)
    if start and end:
        return f"{day} · {start} – {end}"
    return f"{day} · {start}" if start else day


def _row(label: str, value_html: str) -> str:
    return (
        f'<tr><td style="padding:7px 0;color:{MUTED};font-size:13px;width:38%;vertical-align:top;">{esc(label)}</td>'
        f'<td style="padding:7px 0;font-size:14px;font-weight:600;vertical-align:top;">{value_html}</td></tr>'
    )


def _details_table(rows: list[tuple[str, str]]) -> str:
    inner = "".join(_row(label, value) for label, value in rows if value)
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-top:1px solid {LINE};border-bottom:1px solid {LINE};margin:14px 0;">{inner}</table>'
    )


def _lines_table(d: InvoiceData, *, show_prices: bool) -> str:
    if not d.lines:
        return ""
    head = (
        f'<tr><td style="padding:8px 0;font-size:12px;color:{MUTED};border-bottom:1px solid {LINE};">Item</td>'
        f'<td align="right" style="padding:8px 0;font-size:12px;color:{MUTED};border-bottom:1px solid {LINE};">Qty</td>'
        + (f'<td align="right" style="padding:8px 0;font-size:12px;color:{MUTED};border-bottom:1px solid {LINE};">Amount</td>' if show_prices else "")
        + "</tr>"
    )
    rows = []
    for line in d.lines:
        qty = f"{line.quantity}{(' ' + line.unit) if line.unit else ''}"
        note = (
            f'<div style="font-size:12px;color:{MUTED};font-weight:400;">{esc(line.note)}</div>' if line.note else ""
        )
        rows.append(
            f'<tr><td style="padding:9px 8px 9px 0;font-size:14px;border-bottom:1px solid {LINE};">{esc(line.name)}{note}</td>'
            f'<td align="right" style="padding:9px 0;font-size:14px;white-space:nowrap;border-bottom:1px solid {LINE};">{esc(qty)}</td>'
            + (f'<td align="right" style="padding:9px 0 9px 8px;font-size:14px;white-space:nowrap;border-bottom:1px solid {LINE};">{esc(inr(line.total, d.currency_symbol))}</td>' if show_prices else "")
            + "</tr>"
        )
    return (
        f'<h3 style="margin:18px 0 4px;font-size:15px;">What&rsquo;s included</h3>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{head}{"".join(rows)}</table>'
    )


def _totals_table(d: InvoiceData) -> str:
    sym = d.currency_symbol
    rows: list[tuple[str, Decimal, bool]] = [("Package &amp; items", d.subtotal, False)]
    if d.discount > 0:
        rows.append(("Discount", -d.discount, False))
    if d.tax > 0:
        rows.append((f"GST @ {d.gst_rate_percent}%", d.tax, False))
    if d.platform_fee > 0:
        rows.append(("Platform fee", d.platform_fee, False))
    rows.append(("Total", d.total, True))
    rows.append(("Paid", d.amount_paid, True))
    out = ""
    for label, value, strong in rows:
        weight = "800" if strong else "500"
        colour = GREEN if label == "Paid" else INK
        out += (
            f'<tr><td style="padding:5px 0;font-size:14px;font-weight:{weight};">{label}</td>'
            f'<td align="right" style="padding:5px 0;font-size:{"16" if strong else "14"}px;font-weight:{weight};color:{colour};">{esc(inr(value, sym))}</td></tr>'
        )
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:12px;">{out}</table>'


def _extras(d: InvoiceData) -> str:
    bits: list[str] = []
    if d.balloon_colors:
        ratios = d.balloon_ratios if len(d.balloon_ratios) == len(d.balloon_colors) else []
        swatches = "".join(
            f'<span style="display:inline-block;width:12px;height:12px;border-radius:6px;background:{esc(h)};'
            f'border:1px solid {LINE};margin:0 4px -1px 0;"></span>{esc(n)}'
            + (f" {int(ratios[i])}%" if ratios else "")
            + "&nbsp;&nbsp;"
            for i, (n, h) in enumerate(d.balloon_colors)
        )
        bits.append(_row("Balloon colours", swatches))
    if d.balloon_finish:
        bits.append(_row("Balloon finish", esc(d.balloon_finish)))
    if d.customization_note:
        bits.append(_row("Customisation", esc(d.customization_note)))
    if d.special_instructions:
        bits.append(_row("Special instructions", esc(d.special_instructions)))
    if not bits:
        return ""
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-bottom:1px solid {LINE};margin:0 0 6px;">{"".join(bits)}</table>'
    )


def booking_success_email(
    role: str,
    d: InvoiceData,
    *,
    vendor_name: str | None = None,
    payment_reference: str | None = None,
) -> tuple[str, str, str]:
    """
    (subject, html, plain-text) for a confirmed-and-paid booking, addressed to
    the `customer`, the `vendor` who fulfils it, or the platform `owner`.
    """
    venue = ", ".join(d.venue)
    customer_block = [
        ("Customer", esc(d.customer_name)),
        ("Phone", esc(d.customer_phone)),
        ("Email", esc(d.customer_email)),
    ]

    if role == "customer":
        heading = "Your booking is confirmed 🎉"
        intro = (
            f"<p style=\"margin:0 0 6px;\">Hi {esc((d.customer_name or 'there').split(' ')[0])}, thank you for booking with Tyohaar. "
            f"Your payment was received and your celebration is confirmed.</p>"
            f"<p style=\"margin:0;color:{MUTED};font-size:13px;\">Your invoice {esc(d.invoice_number)} is attached to this email as a PDF.</p>"
        )
        subject = f"Booking confirmed · {d.booking_number}"
        rows = [
            ("Booking number", esc(d.booking_number)),
            ("Package", esc(d.package_name)),
            ("Celebration", esc(d.celebration_title)),
            ("When", esc(_when(d))),
            ("Where", esc(venue)),
            ("Handled by", esc(vendor_name)),
            ("Payment reference", esc(payment_reference)),
        ]
        show_prices = True
    elif role == "vendor":
        heading = "New confirmed booking"
        intro = (
            "<p style=\"margin:0;\">A customer has booked and paid for one of your packages. "
            "Please open the vendor portal and set your preparation start time.</p>"
        )
        subject = f"New confirmed booking · {d.booking_number}"
        rows = [
            ("Booking number", esc(d.booking_number)),
            ("Package", esc(d.package_name)),
            ("When", esc(_when(d))),
            ("Where", esc(venue)),
            *customer_block,
        ]
        show_prices = True
    else:  # owner
        heading = "New booking received"
        intro = "<p style=\"margin:0;\">A booking has just been confirmed and paid.</p>"
        subject = f"New paid booking · {d.booking_number}"
        rows = [
            ("Booking number", esc(d.booking_number)),
            ("Package", esc(d.package_name)),
            ("Vendor", esc(vendor_name)),
            ("When", esc(_when(d))),
            ("Where", esc(venue)),
            *customer_block,
            ("Payment reference", esc(payment_reference)),
        ]
        show_prices = True

    body = (
        intro
        + _details_table(rows)
        + _extras(d)
        + _lines_table(d, show_prices=show_prices)
        + _totals_table(d)
    )
    html = shell(
        preheader=f"{heading} — booking {d.booking_number}",
        heading=heading,
        body_html=body,
    )

    text_lines = [heading, "", f"Booking: {d.booking_number}"]
    for label, value in [("Package", d.package_name), ("When", _when(d)), ("Where", venue), ("Vendor", vendor_name)]:
        if value:
            text_lines.append(f"{label}: {value}")
    if role != "customer":
        text_lines += [f"Customer: {d.customer_name or '-'}", f"Phone: {d.customer_phone or '-'}"]
    if payment_reference and role != "vendor":
        text_lines.append(f"Payment reference: {payment_reference}")
    text_lines += ["", "Items:"]
    text_lines += [f"- {line.name} x{line.quantity}: {inr(line.total, d.currency_symbol)}" for line in d.lines]
    text_lines += ["", f"Total: {inr(d.total, d.currency_symbol)}", f"Paid: {inr(d.amount_paid, d.currency_symbol)}"]
    if role == "customer":
        text_lines += ["", "Your invoice is attached as a PDF."]
    return subject, html, "\n".join(text_lines)
