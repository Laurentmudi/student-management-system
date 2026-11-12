from datetime import date

from flask import Blueprint, jsonify, request, send_file

from ..extensions import db
from ..models import CLEARED, Certificate, Student
from ..serializers import certificate_dict
from ..services import fees, pdfs
from ..services.messaging import send_to_student
from ..utils import (admin_required, current_user, error, get_setting, log_activity, next_number, notify,
                     paginate)

bp = Blueprint("certificates", __name__, url_prefix="/api/certificates")


@bp.get("")
@admin_required
def issued():
    q = Certificate.query.join(Student, Certificate.student_id == Student.id)
    s = (request.args.get("q") or "").strip()
    if s:
        like = f"%{s}%"
        q = q.filter(db.or_(Certificate.certificate_number.like(like), Student.first_name.like(like),
                            Student.last_name.like(like), Student.student_number.like(like)))
    items, meta = paginate(q.order_by(Certificate.id.desc()))
    return jsonify(items=[certificate_dict(c) for c in items], **meta)


@bp.get("/eligible")
@admin_required
def eligible():
    """Students whose status is Cleared (Completed) and who have no certificate yet."""
    issued_ids = db.session.query(Certificate.student_id)
    rows = Student.query.filter(Student.status == CLEARED, ~Student.id.in_(issued_ids)).order_by(Student.completed_on.desc()).all()
    rows = [s for s in rows if fees.summary(s)["balance"] <= 0]   # fees must be fully paid
    return jsonify(items=[{"id": s.id, "student_number": s.student_number, "name": s.full_name,
                           "course_name": s.course.name,
                           "completed_on": s.completed_on.isoformat() if s.completed_on else None} for s in rows])


@bp.post("")
@admin_required
def generate():
    d = request.get_json(silent=True) or {}
    s = db.session.get(Student, d.get("student_id") or 0)
    if not s:
        return error("Select a valid student")
    if s.status != CLEARED:
        return error("Only students with status 'Cleared (Completed)' are eligible for a certificate", 409)
    balance = fees.summary(s)["balance"]
    if balance > 0:
        return error(f"Fees not fully paid. Outstanding balance: {get_setting('currency')} {balance:,.2f}. "
                     "A certificate can only be issued once the balance is zero.", 409)
    if Certificate.query.filter_by(student_id=s.id).first():
        return error("A certificate has already been issued for this student", 409)
    c = Certificate(certificate_number="TMP", student_id=s.id, completion_date=s.completed_on or date.today(),
                    issue_date=date.today(), issued_by=current_user().id)
    c.certificate_number = next_number(Certificate, Certificate.certificate_number, "TCA-CERT", 5)
    db.session.add(c)
    db.session.flush()
    send_to_student(s, "certificate",
                    f"{get_setting('academy_name')}: Dear {s.full_name}, your certificate for {s.course.name} "
                    f"(No. {c.certificate_number}) is ready. Please collect it from the office.", dedupe_key=f"cert:{s.id}")
    log_activity("certificate_issued", f"{c.certificate_number} {s.student_number}")
    db.session.commit()
    return jsonify(certificate=certificate_dict(c)), 201


@bp.get("/<int:cid>/pdf")
@admin_required
def pdf(cid):
    c = db.get_or_404(Certificate, cid)
    balance = fees.summary(c.student)["balance"]
    if balance > 0:
        return error(f"Fees not fully paid. Outstanding balance: {get_setting('currency')} {balance:,.2f}", 409)
    log_activity("certificate_viewed", c.certificate_number)
    db.session.commit()
    return send_file(pdfs.certificate_pdf(c), mimetype="application/pdf", download_name=f"{c.certificate_number}.pdf",
                     as_attachment=request.args.get("download") == "1")