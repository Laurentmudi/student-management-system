import os
from datetime import date, timedelta

from flask import Blueprint, current_app, jsonify, request, send_from_directory

from ..extensions import db
from ..models import Course, Intake, Student, User
from ..serializers import student_dict
from ..services import fees
from ..utils import (admin_required, can_access_student, current_user, error, log_activity, login_required,
                     next_number, notify, paginate, parse_date, remove_upload, roles_required, save_upload,
                     to_decimal, ALLOWED_IMAGE, ALLOWED_DOC)
from ..models import STUDENT_STATUSES, CLEARED
from ..services.progress import refresh_status

bp = Blueprint("students", __name__, url_prefix="/api")


def _form():
    return request.form if request.form else (request.get_json(silent=True) or {})


def _apply(s, d, files, creating):
    req = {"first_name": "First name", "last_name": "Last name", "phone": "Phone number", "course_id": "Course"}
    for k, label in req.items():
        if not str(d.get(k) or "").strip():
            raise ValueError(f"{label} is required")
    s.first_name, s.last_name = d["first_name"].strip(), d["last_name"].strip()
    if d.get("gender") and d["gender"] not in ("Male", "Female", "Other"):
        raise ValueError("Invalid gender")
    s.gender = d.get("gender") or None
    s.date_of_birth = parse_date(d.get("date_of_birth"), "date of birth")
    if s.date_of_birth and s.date_of_birth > date.today():
        raise ValueError("Date of birth cannot be in the future")
    s.national_id = (d.get("national_id") or "").strip() or None
    if s.national_id:
        dup = Student.query.filter(Student.national_id == s.national_id, Student.id != (s.id or 0)).first()
        if dup:
            raise ValueError(f"National ID already registered to {dup.full_name} ({dup.student_number})")
    s.phone, s.alt_phone = d["phone"].strip(), (d.get("alt_phone") or "").strip() or None
    s.email, s.address = (d.get("email") or "").strip() or None, (d.get("address") or "").strip() or None
    if s.email and "@" not in s.email:
        raise ValueError("Invalid email address")
    s.guardian_name = (d.get("guardian_name") or "").strip() or None
    s.guardian_relationship = (d.get("guardian_relationship") or "").strip() or None
    s.guardian_phone = (d.get("guardian_phone") or "").strip() or None

    course = db.session.get(Course, int(d["course_id"]))
    if not course:
        raise ValueError("Selected course does not exist")
    course_changed = s.course_id != course.id
    s.course_id = course.id
    intake_id = int(d["intake_id"]) if d.get("intake_id") not in (None, "", "null") else None
    if intake_id:
        intake = db.session.get(Intake, intake_id)
        if not intake or intake.course_id != course.id:
            raise ValueError("Selected intake does not belong to the selected course")
    s.intake_id = intake_id
    trainer_id = int(d["trainer_id"]) if d.get("trainer_id") not in (None, "", "null") else None
    if not trainer_id:  # sensible default: intake trainer, then course lead trainer
        trainer_id = (intake.trainer_id if intake_id else None) or course.trainer_id
    if trainer_id and not User.query.filter_by(id=trainer_id, role="trainer").first():
        raise ValueError("Selected trainer does not exist")
    s.trainer_id = trainer_id
    s.registration_date = parse_date(d.get("registration_date"), "registration date") or s.registration_date or date.today()
    s.expected_completion = parse_date(d.get("expected_completion"), "expected completion date") \
        or s.registration_date + timedelta(weeks=course.duration_weeks)
    if s.expected_completion < s.registration_date:
        raise ValueError("Expected completion cannot be before registration date")

    status = d.get("status")
    if status and status not in STUDENT_STATUSES:
        raise ValueError("Invalid status")
    if creating:
        if status == CLEARED:
            raise ValueError("A student can only become Cleared by completing all modules")
        s.status = status if status in ("Suspended", "Withdrawn") else "Active"
    elif status in ("Suspended", "Withdrawn"):
        s.status = status
    elif status and s.status in ("Suspended", "Withdrawn"):
        s.status = "Active"  # re-activated; refresh_status() recalculates from module progress
    # Active / In Progress / Cleared are otherwise automatic and follow module progress
    if creating or course_changed or d.get("fee_payable") not in (None, ""):
        if d.get("fee_payable") not in (None, ""):
            s.fee_payable = to_decimal(d["fee_payable"], "fee payable")
            if s.fee_payable < 0:
                raise ValueError("Fee payable cannot be negative")
        else:
            s.fee_payable = course.total_fee

    for field, sub, allowed in (("photo", "photos", ALLOWED_IMAGE), ("id_front", "ids", ALLOWED_DOC), ("id_back", "ids", ALLOWED_DOC)):
        f = files.get(field)
        if f and f.filename:
            new = save_upload(f, sub, allowed)
            remove_upload(getattr(s, field))
            setattr(s, field, new)


@bp.get("/students")
@login_required
def list_students():
    u = current_user()
    q = Student.query.join(Course, Student.course_id == Course.id)
    from ..utils import trainer_scope_filter
    q = trainer_scope_filter(q, u)
    s = (request.args.get("q") or "").strip()
    if s:
        like = f"%{s}%"
        q = q.filter(db.or_(Student.first_name.like(like), Student.last_name.like(like),
                            db.func.concat(Student.first_name, " ", Student.last_name).like(like),
                            Student.student_number.like(like), Student.phone.like(like),
                            Student.alt_phone.like(like), Student.national_id.like(like), Course.name.like(like)))
    for key in ("course_id", "intake_id", "trainer_id"):
        if request.args.get(key, type=int) and (key != "trainer_id" or u.role == "admin"):
            q = q.filter(getattr(Student, key) == request.args.get(key, type=int))
    if request.args.get("status"):
        q = q.filter(Student.status == request.args.get("status"))
    q = q.order_by(Student.created_at.desc(), Student.id.desc())
    items, meta = paginate(q)
    return jsonify(items=[student_dict(x, u) for x in items], **meta)


@bp.post("/students")
@admin_required
def create_student():
    s = Student(student_number="TMP")
    try:
        _apply(s, _form(), request.files, creating=True)
        s.student_number = next_number(Student, Student.student_number, "STU", 4)
    except ValueError as e:
        db.session.rollback()
        return error(str(e))
    db.session.add(s)
    db.session.flush()
    notify("New student registered", f"{s.full_name} ({s.student_number}) joined {s.course.name}", role="admin", link=f"/students/{s.id}")
    if s.trainer_id:
        notify("New student assigned", f"{s.full_name} ({s.student_number}) was assigned to you", user_id=s.trainer_id, link=f"/students/{s.id}")
    log_activity("student_registered", f"{s.student_number} {s.full_name}")
    db.session.commit()
    return jsonify(student=student_dict(s, current_user(), detail=True)), 201


@bp.get("/students/<int:sid>")
@login_required
def get_student(sid):
    s = db.get_or_404(Student, sid)
    u = current_user()
    if not can_access_student(u, s):
        return error("This student is not assigned to you", 403)
    return jsonify(student=student_dict(s, u, detail=True))


@bp.put("/students/<int:sid>")
@admin_required
def update_student(sid):
    s = db.get_or_404(Student, sid)
    old_trainer = s.trainer_id
    try:
        _apply(s, _form(), request.files, creating=False)
        db.session.flush()
        if s.status in ("Active", "In Progress", CLEARED):
            refresh_status(s)
    except ValueError as e:
        db.session.rollback()
        return error(str(e))
    if s.trainer_id and s.trainer_id != old_trainer:
        notify("New student assigned", f"{s.full_name} ({s.student_number}) was assigned to you", user_id=s.trainer_id, link=f"/students/{s.id}")
    log_activity("student_updated", f"{s.student_number} {s.full_name}")
    db.session.commit()
    return jsonify(student=student_dict(s, current_user(), detail=True))


@bp.delete("/students/<int:sid>")
@admin_required
def delete_student(sid):
    s = db.get_or_404(Student, sid)
    if s.payments:
        return error("This student has payment records and cannot be deleted. Set the status to Withdrawn instead.", 409)
    from ..models import Attendance, Certificate, ModuleProgress, Remark, MessageLog
    if Certificate.query.filter_by(student_id=sid).count():
        return error("This student has an issued certificate and cannot be deleted.", 409)
    for m in (Attendance, ModuleProgress, Remark, MessageLog):
        m.query.filter_by(student_id=sid).delete()
    for f in (s.photo, s.id_front, s.id_back):
        remove_upload(f)
    log_activity("student_deleted", f"{s.student_number} {s.full_name}")
    db.session.delete(s)
    db.session.commit()
    return jsonify(message="Student deleted")


@bp.get("/students/<int:sid>/fees")
@admin_required
def student_fees(sid):
    s = db.get_or_404(Student, sid)
    return jsonify(fees=fees.summary(s))


# ---- authenticated file serving (photos for everyone logged in, ID scans for admins only) ----
@bp.get("/files/<path:rel>")
@login_required
def serve_file(rel):
    top = rel.split("/")[0]
    if top == "ids" and current_user().role != "admin":
        return error("Only administrators can view identity documents", 403)
    if top not in ("photos", "ids", "branding"):
        return error("Not found", 404)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], rel)
