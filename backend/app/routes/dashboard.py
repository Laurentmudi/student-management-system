from datetime import date, timedelta

from flask import Blueprint, jsonify

from ..extensions import db
from ..models import Attendance, CLEARED, Course, Intake, Payment, Student
from ..serializers import payment_dict
from ..services import fees, progress as prog
from ..utils import current_user, login_required, trainer_scope_filter

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@bp.get("")
@login_required
def dashboard():
    u = current_user()
    if u.role == "admin":
        return jsonify(role="admin", **admin_stats())
    return jsonify(role="trainer", **trainer_stats(u))


def admin_stats():
    today = date.today()
    cnt = lambda *f: Student.query.filter(*f).count()
    collected = db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0)).scalar()
    outstanding_total, due_students, due_amount = 0.0, 0, 0.0
    for s in Student.query.filter(Student.status.in_(["Active", "In Progress", CLEARED, "Suspended"])).all():
        sm = fees.summary(s)
        outstanding_total += sm["balance"]
        nd = sm["next_due"]
        if nd and s.status in ("Active", "In Progress") and date.fromisoformat(nd["due_date"]) <= today + timedelta(days=7):
            due_students += 1
            due_amount += nd["outstanding"]
    recent_students = Student.query.order_by(Student.created_at.desc(), Student.id.desc()).limit(6).all()
    recent_payments = Payment.query.order_by(Payment.created_at.desc(), Payment.id.desc()).limit(6).all()
    month_start = today.replace(day=1)
    month = db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0)).filter(Payment.payment_date >= month_start).scalar()
    status_counts = {st: cnt(Student.status == st) for st in ("Active", "In Progress", CLEARED, "Suspended", "Withdrawn")}
    return {
        "total_students": cnt(),
        "active_students": cnt(Student.status.in_(["Active", "In Progress"])),
        "in_progress": status_counts["In Progress"],
        "cleared": status_counts[CLEARED],
        "total_courses": Course.query.count(),
        "fees_collected": float(collected or 0),
        "collected_this_month": float(month or 0),
        "outstanding_balances": outstanding_total,
        "payments_due_count": due_students,
        "payments_due_amount": due_amount,
        "status_counts": status_counts,
        "recent_payments": [payment_dict(p) for p in recent_payments],
        "recent_registrations": [{"id": s.id, "student_number": s.student_number, "name": s.full_name,
                                  "course_name": s.course.name, "registration_date": s.registration_date.isoformat()}
                                 for s in recent_students],
    }


def trainer_stats(u):
    # NOTE: intentionally contains no financial fields
    students = trainer_scope_filter(Student.query, u).all()
    active = [s for s in students if s.status in ("Active", "In Progress")]
    intake_ids = {s.intake_id for s in students if s.intake_id} | {i.id for i in Intake.query.filter_by(trainer_id=u.id).all()}
    today = date.today()
    recorded = {a.student_id for a in Attendance.query.filter(
        Attendance.date == today, Attendance.student_id.in_([s.id for s in active] or [0])).all()}
    pending = 0 if today.weekday() >= 5 else len([s for s in active if s.id not in recorded])
    behind = [s for s in active if prog.is_behind(s)]
    return {
        "assigned_students": len(students),
        "assigned_classes": len(intake_ids),
        "attendance_pending": pending,
        "in_progress": sum(1 for s in students if s.status == "In Progress"),
        "cleared": sum(1 for s in students if s.status == CLEARED),
        "behind_schedule": len(behind),
        "behind_list": [{"id": s.id, "name": s.full_name, "student_number": s.student_number,
                         "course_name": s.course.name, "percent": prog.progress_for(s)["percent"]} for s in behind[:8]],
    }
