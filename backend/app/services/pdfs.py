import io
import os

import qrcode
from flask import current_app
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..utils import get_setting
from . import fees

BRAND = colors.HexColor("#1d4ed8")
DARK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")


def logo_path():
    folder = current_app.config["UPLOAD_FOLDER"]
    custom = get_setting("logo")
    if custom:
        p = os.path.join(folder, custom)
        if os.path.isfile(p):
            return p
    p = os.path.join(folder, "default_logo.png")
    if not os.path.isfile(p):
        os.makedirs(folder, exist_ok=True)
        img = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((10, 10, 390, 390), fill=(29, 78, 216, 255))
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 170)
        except Exception:
            font = ImageFont.load_default()
        d.text((200, 200), "TC", fill=(255, 255, 255, 255), font=font, anchor="mm")
        img.save(p)
    return p


def qr_reader(text):
    img = qrcode.make(text, box_size=6, border=1)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def money(n):
    return f"{get_setting('currency')} {float(n):,.2f}"


def receipt_pdf(payment):
    s = payment.student
    sm = fees.summary(s)
    # balances "as at this receipt": count only payments up to and including this one
    paid_to_date = sum(float(p.amount) for p in s.payments if (p.payment_date, p.id) <= (payment.payment_date, payment.id))
    balance = max(0.0, float(s.fee_payable) - paid_to_date)
    buf = io.BytesIO()
    w, h = A4
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Receipt {payment.receipt_number}")
    # header band
    c.setFillColor(BRAND)
    c.rect(0, h - 38 * mm, w, 38 * mm, fill=1, stroke=0)
    c.drawImage(ImageReader(logo_path()), 15 * mm, h - 32 * mm, 26 * mm, 26 * mm, mask="auto")
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(46 * mm, h - 17 * mm, get_setting("academy_name"))
    c.setFont("Helvetica", 9)
    c.drawString(46 * mm, h - 23 * mm, get_setting("academy_address"))
    line = "  |  ".join(x for x in [get_setting("academy_phone"), get_setting("academy_email")] if x)
    c.drawString(46 * mm, h - 28 * mm, line)
    c.setFont("Helvetica-Bold", 16)
    c.drawRightString(w - 15 * mm, h - 18 * mm, "PAYMENT RECEIPT")
    c.setFont("Helvetica", 10)
    c.drawRightString(w - 15 * mm, h - 25 * mm, f"No. {payment.receipt_number}")
    # body table
    rows = [
        ("Receipt Number", payment.receipt_number),
        ("Date", payment.payment_date.strftime("%d %B %Y")),
        ("Student Name", s.full_name),
        ("Student Number", s.student_number),
        ("Course", s.course.name),
        ("Payment Method", payment.method),
        ("M-Pesa Transaction Code", payment.mpesa_code or "N/A"),
    ]
    y = h - 55 * mm
    for k, v in rows:
        c.setFillColor(MUTED); c.setFont("Helvetica", 10); c.drawString(20 * mm, y, k)
        c.setFillColor(DARK); c.setFont("Helvetica-Bold", 11); c.drawString(75 * mm, y, str(v))
        c.setStrokeColor(colors.HexColor("#e2e8f0")); c.line(20 * mm, y - 3 * mm, w - 20 * mm, y - 3 * mm)
        y -= 9 * mm
    # amounts box
    y -= 4 * mm
    c.setFillColor(colors.HexColor("#eff6ff")); c.roundRect(20 * mm, y - 38 * mm, w - 40 * mm, 42 * mm, 3 * mm, fill=1, stroke=0)
    c.setFillColor(MUTED); c.setFont("Helvetica", 10)
    c.drawString(26 * mm, y - 6 * mm, "AMOUNT PAID")
    c.setFillColor(BRAND); c.setFont("Helvetica-Bold", 24)
    c.drawString(26 * mm, y - 17 * mm, money(payment.amount))
    c.setFillColor(DARK); c.setFont("Helvetica", 10)
    c.drawString(26 * mm, y - 27 * mm, f"Total Fees Paid (to date):  {money(paid_to_date)}")
    c.drawString(26 * mm, y - 33 * mm, f"Outstanding Balance:  {money(balance)}")
    # QR
    verify_url = f"{current_app.config['FRONTEND_URL']}/verify/receipt/{payment.receipt_number}"
    c.drawImage(qr_reader(verify_url), w - 62 * mm, y - 36 * mm, 32 * mm, 32 * mm)
    c.setFont("Helvetica", 7); c.setFillColor(MUTED)
    c.drawCentredString(w - 46 * mm, y - 40 * mm, "Scan to verify receipt")
    # footer
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(w / 2, 30 * mm, "Thank you for your payment. This is a computer-generated receipt.")
    c.setStrokeColor(MUTED); c.line(w - 80 * mm, 48 * mm + 0, w - 20 * mm, 48 * mm)
    c.setFont("Helvetica", 8); c.drawCentredString(w - 50 * mm, 44 * mm, "Received by: " + (payment.recorder.name if payment.recorder else "Accounts"))
    c.showPage(); c.save()
    buf.seek(0)
    return buf


def certificate_pdf(cert):
    s = cert.student
    buf = io.BytesIO()
    w, h = landscape(A4)
    c = canvas.Canvas(buf, pagesize=landscape(A4))
    c.setTitle(f"Certificate {cert.certificate_number}")
    c.setStrokeColor(BRAND); c.setLineWidth(6); c.rect(10 * mm, 10 * mm, w - 20 * mm, h - 20 * mm)
    c.setStrokeColor(colors.HexColor("#93c5fd")); c.setLineWidth(1.5); c.rect(15 * mm, 15 * mm, w - 30 * mm, h - 30 * mm)
    c.drawImage(ImageReader(logo_path()), w / 2 - 15 * mm, h - 50 * mm, 30 * mm, 30 * mm, mask="auto")
    c.setFillColor(DARK); c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(w / 2, h - 57 * mm, get_setting("academy_name").upper())
    c.setFillColor(BRAND); c.setFont("Times-Bold", 38)
    c.drawCentredString(w / 2, h - 77 * mm, "Certificate of Completion")
    c.setFillColor(MUTED); c.setFont("Helvetica", 12)
    c.drawCentredString(w / 2, h - 92 * mm, "This is to certify that")
    c.setFillColor(DARK); c.setFont("Times-BoldItalic", 34)
    c.drawCentredString(w / 2, h - 108 * mm, s.full_name)
    c.setStrokeColor(MUTED); c.setLineWidth(0.6); c.line(w / 2 - 80 * mm, h - 112 * mm, w / 2 + 80 * mm, h - 112 * mm)
    c.setFillColor(MUTED); c.setFont("Helvetica", 12)
    c.drawCentredString(w / 2, h - 123 * mm, "has successfully completed the course")
    c.setFillColor(DARK); c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(w / 2, h - 135 * mm, s.course.name)
    c.setFillColor(MUTED); c.setFont("Helvetica", 11)
    c.drawCentredString(w / 2, h - 146 * mm,
                        f"Date of Completion: {cert.completion_date.strftime('%d %B %Y')}     |     Date of Issue: {cert.issue_date.strftime('%d %B %Y')}")
    # signature
    c.setStrokeColor(DARK); c.line(35 * mm, 38 * mm, 95 * mm, 38 * mm)
    c.setFillColor(DARK); c.setFont("Helvetica-Bold", 11); c.drawCentredString(65 * mm, 32 * mm, get_setting("signatory_name"))
    c.setFont("Helvetica", 9); c.setFillColor(MUTED); c.drawCentredString(65 * mm, 27 * mm, get_setting("signatory_title") or "Authorized Signature")
    c.setFont("Helvetica-Oblique", 14); c.setFillColor(BRAND)
    c.drawCentredString(65 * mm, 41 * mm, get_setting("signatory_name"))
    # QR + cert no
    url = f"{current_app.config['FRONTEND_URL']}/verify/certificate/{cert.certificate_number}"
    c.drawImage(qr_reader(url), w - 60 * mm, 22 * mm, 28 * mm, 28 * mm)
    c.setFont("Helvetica", 8); c.setFillColor(MUTED)
    c.drawCentredString(w - 46 * mm, 18 * mm, "Scan to verify")
    c.setFont("Helvetica-Bold", 10); c.setFillColor(DARK)
    c.drawCentredString(w / 2, 24 * mm, f"Certificate No: {cert.certificate_number}")
    c.showPage(); c.save()
    buf.seek(0)
    return buf


def table_pdf(title, columns, rows, summary=None, subtitle=None):
    """Generic landscape table PDF used by every report."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm, title=title)
    ss = getSampleStyleSheet()
    cell = ParagraphStyle("cell", parent=ss["BodyText"], fontSize=7.5, leading=9)
    head = ParagraphStyle("head", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
    story = [Paragraph(f"<b>{get_setting('academy_name')}</b>", ss["Title"]),
             Paragraph(title, ss["Heading2"])]
    if subtitle:
        story.append(Paragraph(subtitle, ss["Normal"]))
    story.append(Spacer(1, 4 * mm))
    if summary:
        story.append(Paragraph("  |  ".join(f"<b>{k}:</b> {v}" for k, v in summary.items()), ss["Normal"]))
        story.append(Spacer(1, 3 * mm))
    data = [[Paragraph(str(c), head) for c in columns]]
    for r in rows:
        data.append([Paragraph("" if v is None else str(v), cell) for v in r])
    if len(data) == 1:
        data.append([Paragraph("No records found", cell)] + [""] * (len(columns) - 1))
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)

    def footer(cv, d):
        cv.setFont("Helvetica", 7); cv.setFillColor(MUTED)
        from datetime import datetime
        cv.drawString(12 * mm, 7 * mm, f"Generated {datetime.now():%d %b %Y %H:%M}")
        cv.drawRightString(landscape(A4)[0] - 12 * mm, 7 * mm, f"Page {d.page}")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    buf.seek(0)
    return buf
