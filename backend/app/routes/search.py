from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Certificate, Course, Payment, Student
from ..utils import current_user, login_required, trainer_scope_filter

bp = Blueprint("search", __name__, url_prefix="/api/search")


@bp.get("")
@login_required
def search():
    """Global search: student name/number/phone/course, receipt no., M-Pesa code, certificate no.
    Trainers only ever get students within their scope (no payments or financial hits)."""
    u = current_user()
    term = (request.args.get("q") or "").strip()
    if len(term) < 2:
        return jsonify(students=[], payments=[], certificates=[])
    like = f"%{term}%"
    sq = trainer_scope_filter(Student.query.join(Course, Student.course_id == Course.id), u).filter(
        db.or_(Student.first_name.like(like), Student.last_name.like(like),
               db.func.concat(Student.first_name, " ", Student.last_name).like(like),
               Student.student_number.like(like), Student.phone.like(like), Student.alt_phone.like(like),
               Course.name.like(like), Course.code.like(like)))
    students = [{"id": s.id, "student_number": s.student_number, "name": s.full_name, "phone": s.phone,
                 "course_name": s.course.name, "status": s.status} for s in sq.limit(15).all()]
    payments, certs = [], []
    if u.role == "admin":
        pq = Payment.query.filter(db.or_(Payment.receipt_number.like(like), Payment.mpesa_code.like(like))).limit(10).all()
        payments = [{"id": p.id, "receipt_number": p.receipt_number, "mpesa_code": p.mpesa_code, "student_id": p.student_id,
                     "student_name": p.student.full_name, "amount": float(p.amount),
                     "payment_date": p.payment_date.isoformat()} for p in pq]
        cq = Certificate.query.filter(Certificate.certificate_number.like(like)).limit(10).all()
        certs = [{"id": c.id, "certificate_number": c.certificate_number, "student_id": c.student_id,
                  "student_name": c.student.full_name} for c in cq]
    return jsonify(students=students, payments=payments, certificates=certs)
