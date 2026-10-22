import os

from flask import Blueprint, current_app, jsonify, send_file

from ..models import Certificate, Payment
from ..services import pdfs
from ..utils import get_setting

bp = Blueprint("public", __name__, url_prefix="/api/public")


@bp.get("/branding")
def branding():
    return jsonify(name=get_setting("academy_name"))


@bp.get("/logo")
def logo():
    return send_file(pdfs.logo_path())


@bp.get("/verify/certificate/<number>")
def verify_certificate(number):
    c = Certificate.query.filter_by(certificate_number=number).first()
    if not c:
        return jsonify(valid=False), 404
    return jsonify(valid=True, certificate_number=c.certificate_number, student_name=c.student.full_name,
                   course=c.student.course.name, completion_date=c.completion_date.isoformat(),
                   issue_date=c.issue_date.isoformat(), academy=get_setting("academy_name"))


@bp.get("/verify/receipt/<number>")
def verify_receipt(number):
    p = Payment.query.filter_by(receipt_number=number).first()
    if not p:
        return jsonify(valid=False), 404
    # deliberately minimal: no balances, phone numbers or other personal/financial detail
    return jsonify(valid=True, receipt_number=p.receipt_number, student_name=p.student.full_name,
                   amount=float(p.amount), payment_date=p.payment_date.isoformat(), academy=get_setting("academy_name"))
