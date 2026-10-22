from datetime import date

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Attendance, Intake, Student
from ..services.progress import attendance_stats
from ..utils import (can_access_student, current_user, error, log_activity, login_required, parse_date,
                     trainer_scope_filter)

bp = Blueprint("attendance", __name__, url_prefix="/api")
STATUSES = ("Present", "Absent", "Late")


@bp.get("/classes")
@login_required
def classes():
    """A 'class' is an intake group. Trainers see the intakes they teach or have students in."""
    u = current_user()
    students = trainer_scope_filter(Student.query.filter(Student.status.in_(["Active", "In Progress"])), u).all()
    intake_ids = {s.intake_id for s in students if s.intake_id}
    if u.role == "trainer":
        intake_ids |= {i.id for i in Intake.query.filter_by(trainer_id=u.id).all()}
    q = Intake.query.filter(Intake.id.in_(intake_ids)) if u.role == "trainer" else Intake.query
    out = []
    for i in q.order_by(Intake.start_date.desc()).all():
        out.append({"id": i.id, "name": i.name, "course_name": i.course.name, "course_id": i.course_id,
                    "start_date": i.start_date.isoformat(), "trainer_name": i.trainer.name if i.trainer else None,
                    "students": sum(1 for s in students if s.intake_id == i.id)})
    unassigned = [s for s in students if not s.intake_id]
    return jsonify(items=out, no_intake_students=len(unassigned))


@bp.get("/attendance/sheet")
@login_required
def sheet():
    u = current_user()
    day = parse_date(request.args.get("date")) or date.today()
    q = trainer_scope_filter(Student.query.filter(Student.status.in_(["Active", "In Progress"])), u)
    if request.args.get("intake_id") == "none":
        q = q.filter(Student.intake_id.is_(None))
    elif request.args.get("intake_id", type=int):
        q = q.filter(Student.intake_id == request.args.get("intake_id", type=int))
    if request.args.get("course_id", type=int):
        q = q.filter(Student.course_id == request.args.get("course_id", type=int))
    students = q.order_by(Student.first_name, Student.last_name).all()
    existing = {a.student_id: a for a in Attendance.query.filter(
        Attendance.date == day, Attendance.student_id.in_([s.id for s in students] or [0])).all()}
    items = [{"student_id": s.id, "student_number": s.student_number, "name": s.full_name, "photo": s.photo,
              "course_name": s.course.name, "status": existing[s.id].status if s.id in existing else None,
              "note": existing[s.id].note if s.id in existing else "",
              "attendance_percent": attendance_stats(s.id)["percent"]} for s in students]
    return jsonify(date=day.isoformat(), items=items, recorded=len(existing))


@bp.post("/attendance/bulk")
@login_required
def bulk():
    u = current_user()
    d = request.get_json(silent=True) or {}
    try:
        day = parse_date(d.get("date")) or date.today()
    except ValueError as e:
        return error(str(e))
    if day > date.today():
        return error("Attendance cannot be recorded for a future date")
    saved = 0
    for r in d.get("records") or []:
        if r.get("status") not in STATUSES:
            continue
        s = db.session.get(Student, r.get("student_id") or 0)
        if not s or not can_access_student(u, s):
            return error("You can only record attendance for your own students", 403)
        row = Attendance.query.filter_by(student_id=s.id, date=day).first()
        if row:
            row.status, row.note, row.recorded_by = r["status"], r.get("note"), u.id
        else:
            db.session.add(Attendance(student_id=s.id, date=day, status=r["status"], note=r.get("note"), recorded_by=u.id))
        saved += 1
    log_activity("attendance_recorded", f"{saved} records for {day}")
    db.session.commit()
    return jsonify(saved=saved)


@bp.get("/attendance/student/<int:sid>")
@login_required
def history(sid):
    s = db.get_or_404(Student, sid)
    if not can_access_student(current_user(), s):
        return error("This student is not assigned to you", 403)
    rows = Attendance.query.filter_by(student_id=sid).order_by(Attendance.date.desc()).all()
    return jsonify(items=[{"id": r.id, "date": r.date.isoformat(), "status": r.status, "note": r.note} for r in rows],
                   stats=attendance_stats(sid))


@bp.put("/attendance/<int:aid>")
@login_required
def edit(aid):
    r = db.get_or_404(Attendance, aid)
    s = db.session.get(Student, r.student_id)
    if not can_access_student(current_user(), s):
        return error("This student is not assigned to you", 403)
    d = request.get_json(silent=True) or {}
    if d.get("status") not in STATUSES:
        return error("Status must be Present, Absent or Late")
    r.status, r.note, r.recorded_by = d["status"], d.get("note", r.note), current_user().id
    log_activity("attendance_edited", f"{s.student_number} {r.date} -> {r.status}")
    db.session.commit()
    return jsonify(message="Updated", stats=attendance_stats(s.id))
