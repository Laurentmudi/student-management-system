import io
import os

import qrcode
from flask import current_app
from PIL import Image, ImageDraw, ImageFont, ImageOps
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


from ..utils import get_setting
from . import fees

# Fixed brand files kept inside the project (these are deployed with the code)
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets")

# Brand colours (navy + gold)
BRAND = colors.HexColor("#1D2245")
GOLD = colors.HexColor("#F7B500")
DARK = colors.HexColor("#1D2245")
MUTED = colors.HexColor("#666666")


def logo_path():
    folder = current_app.config["UPLOAD_FOLDER"]
    custom = get_setting("logo")
    if custom:
        p = os.path.join(folder, custom)
        if os.path.isfile(p):
            return p
    for ext in ("png", "jpg", "jpeg"):
        fixed = os.path.join(ASSETS_DIR, f"logo.{ext}")
        if os.path.isfile(fixed):
            return fixed
    p = os.path.join(folder, "default_logo.png")
    if not os.path.isfile(p):
        os.makedirs(folder, exist_ok=True)
        img = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((10, 10, 390, 390), fill=(29, 34, 69, 255))
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 170)
        except Exception:
            font = ImageFont.load_default()
        d.text((200, 200), "TC", fill=(247, 181, 0, 255), font=font, anchor="mm")
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
    c.setFillColor(GOLD)
    c.rect(0, h - 40 * mm, w, 2 * mm, fill=1, stroke=0)
    c.drawImage(ImageReader(logo_path()), 15 * mm, h - 32 * mm, 26 * mm, 26 * mm, mask="auto")
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(46 * mm, h - 17 * mm, get_setting("academy_name"))
    c.setFont("Helvetica", 9)
    c.drawString(46 * mm, h - 23 * mm, get_setting("academy_address"))
    line = "  |  ".join(x for x in [get_setting("academy_phone"), get_setting("academy_email")] if x)
    c.drawString(46 * mm, h - 28 * mm, line)
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 16)
    c.drawRightString(w - 15 * mm, h - 18 * mm, "PAYMENT RECEIPT")
    c.setFillColor(colors.white)
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
        c.setStrokeColor(colors.HexColor("#eeeeee")); c.line(20 * mm, y - 3 * mm, w - 20 * mm, y - 3 * mm)
        y -= 9 * mm
    # amounts box
    y -= 4 * mm
    c.setFillColor(colors.HexColor("#fff6d6")); c.roundRect(20 * mm, y - 38 * mm, w - 40 * mm, 42 * mm, 3 * mm, fill=1, stroke=0)
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


# =====================================================================
#  CERTIFICATE - uses your template image (no old design any more)
#  Put the template in:  backend/uploads/branding/
#  and name it:          certificate_template.jpg   (.jpeg or .png also work)
# =====================================================================
# Extra file names to try if certificate_template.* is not found
CERT_TEMPLATE_EXTRA_NAMES = ["1000883699 (1).jpg"]

# x, y are fractions of the image: x=0.5 is the middle, y=0.0 is the top edge, y=1.0 the bottom edge
CERT_FIELDS = {
    # Student name: biggest text, brand navy, gold line underneath so it stands out from the template wording
    "name":   {"x": 0.50, "y": 0.38, "size": 24, "font": "Times-BoldItalic", "color": "#1D2245", "rule": True},
    # Course: bold navy with a thin gold line underneath
    "course": {"x": 0.50, "y": 0.58, "size": 20, "font": "Helvetica-Bold",   "color": "#1D2245", "rule": True},
    # Date and certificate number: small and quiet
    "date":   {"x": 0.53, "y": 0.88, "size": 10, "font": "Helvetica",        "color": "#555555"},
    "number": {"x": 0.50, "y": 0.94, "size": 10, "font": "Helvetica-Bold",   "color": "#555555"},
    # QR code in the bottom right corner (x, y = centre of the QR)
    "qr":     {"x": 0.85, "y": 0.79, "size_mm": 20},

    "credit": {"x": 0.50, "y": 0.69, "size": 18, "font": "Times-BoldItalic", "color": "#1D2245", "rule": True},
}
RULE_COLOR = "#F7B500"   # gold line under the name and course


def certificate_template_path():
    folders = [ASSETS_DIR, os.path.join(current_app.config["UPLOAD_FOLDER"], "branding")]
    names = [f"certificate_template.{e}" for e in ("jpg", "jpeg", "png", "JPG", "JPEG", "PNG")]
    for folder in folders:
        for name in names + CERT_TEMPLATE_EXTRA_NAMES:
            p = os.path.join(folder, name)
            if os.path.isfile(p):
                return p
    raise FileNotFoundError(
        f"Certificate template not found. Put certificate_template.jpg in: {ASSETS_DIR}")


def certificate_pdf(cert):
    template = certificate_template_path()
    s = cert.student

    img = Image.open(template)
    try:
        img = ImageOps.exif_transpose(img)   # some photos are stored rotated
    except Exception:
        pass
    img = img.convert("RGB")                  # fixes CMYK / transparent files
    iw, ih = img.size
    w = 297 * mm                              # A4-landscape width; height follows the template shape
    h = w * ih / iw
    img_buf = io.BytesIO()
    img.save(img_buf, "JPEG", quality=95)
    img_buf.seek(0)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))
    c.setTitle(f"Certificate {cert.certificate_number}")
    c.drawImage(ImageReader(img_buf), 0, 0, w, h)

    def put(key, text):
        f = CERT_FIELDS[key]
        x, y = w * f["x"], h * (1 - f["y"])
        c.setFillColor(colors.HexColor(f["color"]))
        c.setFont(f["font"], f["size"])
        c.drawCentredString(x, y, text)
        if f.get("rule"):                                   # gold line under the text
            half = c.stringWidth(text, f["font"], f["size"]) / 2 + 6 * mm
            c.setStrokeColor(colors.HexColor(RULE_COLOR))
            c.setLineWidth(1.6)
            c.line(x - half, y - f["size"] * 0.35, x + half, y - f["size"] * 0.35)

    put("name", s.full_name)
    put("course", s.course.name)
    put("date", cert.completion_date.strftime("%d %B %Y"))
    put("number", f"Certificate No: {cert.certificate_number}")
    put("credit", "Credit")

    q = CERT_FIELDS["qr"]
    size = q["size_mm"] * mm
    url = f"{current_app.config['FRONTEND_URL']}/verify/certificate/{cert.certificate_number}"
    c.drawImage(qr_reader(url), w * q["x"] - size / 2, h * (1 - q["y"]) - size / 2, size, size)
    c.showPage()
    c.save()
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
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
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