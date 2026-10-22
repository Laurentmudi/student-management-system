from datetime import date
from decimal import Decimal

from flask import Blueprint, jsonify, request, send_file

from ..extensions import db
from ..models import Payment, Student
from ..serializers import payment_dict
from ..services import fees, pdfs
from ..services.messaging import send_to_student
from ..services.reminders import fmt
from ..utils import (admin_required, current_user, error, get_setting, log_activity, next_number, paginate,
                     parse_date, to_decimal)

bp = Blueprint("payments", __name__, url_prefix="/api/payments")
METHODS = ["M-Pesa", "Cash", "Bank Transfer", "Cheque", "Card"]


def _validate(d, student, existing=None):
    amount = to_decimal(d.get("amount"), "amount")
    if amount <= 0:
        raise ValueError("Amount must be greater than zero")
    method = d.get("method") or "M-Pesa"
    if method not in METHODS:
        raise ValueError("Invalid payment method")
    code = (d.get("mpesa_code") or "").strip().upper() or None
    if method == "M-Pesa" and not code:
        raise ValueError("M-Pesa transaction code is required for M-Pesa payments")
    if method != "M-Pesa" and not d.get("keep_code"):
        code = code if code else None
    if code:
        dup = Payment.query.filter(Payment.mpesa_code == code, Payment.id != (existing.id if existing else 0)).first()
        if dup:
            raise ValueError(f"M-Pesa code {code} was already used on receipt {dup.receipt_number}")
    pdate = parse_date(d.get("payment_date"), "payment date") or date.today()
    if pdate > date.today():
        raise ValueError("Payment date cannot be in the future")
    paid_other = fees.paid_total(student.id) - (Decimal(existing.amount) if existing else Decimal(0))
    if paid_other + amount > Decimal(student.fee_payable):
        left = Decimal(student.fee_payable) - paid_other
        raise ValueError(f"Amount exceeds the outstanding balance ({left:,.2f})")
    return amount, method, code, pdate


@bp.get("")
@admin_required
def list_payments():
    q = Payment.query.join(Student, Payment.student_id == Student.id)
    s = (request.args.get("q") or "").strip()
    if s:
        like = f"%{s}%"
        q = q.filter(db.or_(Payment.receipt_number.like(like), Payment.mpesa_code.like(like),
                            Student.first_name.like(like), Student.last_name.like(like),
                            db.func.concat(Student.first_name, " ", Student.last_name).like(like),
                            Student.student_number.like(like), Student.phone.like(like)))
    if request.args.get("student_id", type=int):
        q = q.filter(Payment.student_id == request.args.get("student_id", type=int))
    if request.args.get("method"):
        q = q.filter(Payment.method == request.args.get("method"))
    if request.args.get("date_from"):
        q = q.filter(Payment.payment_date >= parse_date(request.args["date_from"]))
    if request.args.get("date_to"):
        q = q.filter(Payment.payment_date <= parse_date(request.args["date_to"]))
    total_amount = q.with_entities(db.func.coalesce(db.func.sum(Payment.amount), 0)).scalar()
    items, meta = paginate(q.order_by(Payment.payment_date.desc(), Payment.id.desc()))
    return jsonify(items=[payment_dict(p) for p in items], total_amount=float(total_amount or 0), **meta)


@bp.post("")
@admin_required
def create_payment():
    d = request.get_json(silent=True) or {}
    student = db.session.get(Student, d.get("student_id") or 0)
    if not student:
        return error("Select a valid student")
    try:
        amount, method, code, pdate = _validate(d, student)
    except ValueError as e:
        return error(str(e))
    p = Payment(receipt_number="TMP", student_id=student.id, payment_date=pdate, amount=amount, method=method,
                mpesa_code=code, notes=d.get("notes"), recorded_by=current_user().id)
    p.receipt_number = next_number(Payment, Payment.receipt_number, "RCT", 5)
    db.session.add(p)
    db.session.flush()
    sm = fees.summary(student)
    send_to_student(student, "payment",
                    f"{get_setting('academy_name')}: Dear {student.full_name}, we have received {fmt(float(amount))} "
                    f"(Receipt {p.receipt_number}). Total paid: {fmt(sm['total_paid'])}. Balance: {fmt(sm['balance'])}. Thank you.")
    log_activity("payment_recorded", f"{p.receipt_number} {student.student_number} {amount}")
    db.session.commit()
    return jsonify(payment=payment_dict(p), fees=sm), 201


@bp.put("/<int:pid>")
@admin_required
def update_payment(pid):
    p = db.get_or_404(Payment, pid)
    d = request.get_json(silent=True) or {}
    try:
        amount, method, code, pdate = _validate({**d, "student_id": p.student_id}, p.student, existing=p)
    except ValueError as e:
        return error(str(e))
    old = f"{p.amount} {p.method} {p.mpesa_code}"
    p.amount, p.method, p.mpesa_code, p.payment_date = amount, method, code, pdate
    p.notes = d.get("notes", p.notes)
    log_activity("payment_edited", f"{p.receipt_number}: was {old}, now {amount} {method} {code}")
    db.session.commit()
    return jsonify(payment=payment_dict(p))


@bp.get("/<int:pid>")
@admin_required
def get_payment(pid):
    return jsonify(payment=payment_dict(db.get_or_404(Payment, pid)))


@bp.get("/<int:pid>/receipt")
@admin_required
def receipt(pid):
    p = db.get_or_404(Payment, pid)
    buf = pdfs.receipt_pdf(p)
    log_activity("receipt_viewed", p.receipt_number)
    db.session.commit()
    return send_file(buf, mimetype="application/pdf", download_name=f"{p.receipt_number}.pdf",
                     as_attachment=request.args.get("download") == "1")


@bp.get("/methods")
@admin_required
def methods():
    return jsonify(items=METHODS)
