from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Course, FeeInstallment, Intake, Module, ModuleProgress, Student, User
from ..serializers import course_dict, intake_dict
from ..utils import (admin_required, current_user, error, log_activity, login_required, notify, parse_date,
                     to_decimal)

bp = Blueprint("courses", __name__, url_prefix="/api")


def _apply_course(c, d):
    c.name = (d.get("name") or "").strip()
    c.code = (d.get("code") or "").strip().upper()
    if not c.name or not c.code:
        raise ValueError("Course code and name are required")
    c.description = d.get("description")
    c.duration_weeks = int(d.get("duration_weeks") or 12)
    if c.duration_weeks < 1:
        raise ValueError("Duration must be at least 1 week")
    c.trainer_id = d.get("trainer_id") or None
    if c.trainer_id and not User.query.filter_by(id=c.trainer_id, role="trainer").first():
        raise ValueError("Selected trainer does not exist")
    fee = to_decimal(d.get("total_fee") or 0, "total fee")
    if fee < 0:
        raise ValueError("Fee cannot be negative")
    c.total_fee = fee

    # fee structure (installments) must add up to the total fee
    inst = d.get("installments") or []
    total = sum(to_decimal(i.get("amount") or 0, "installment amount") for i in inst)
    if inst and total != fee:
        raise ValueError(f"Installments add up to {total:,.2f} but the total fee is {fee:,.2f}. They must match.")
    c.installments[:] = []
    for n, i in enumerate(inst, 1):
        c.installments.append(FeeInstallment(label=(i.get("label") or f"Installment {n}").strip(),
                                             amount=to_decimal(i.get("amount") or 0), position=n,
                                             due_after_days=int(i.get("due_after_days") or 0)))

    # modules: update existing ones in place (keeps students' progress), add new, delete removed
    mods = d.get("modules") or []
    keep_ids = {int(m["id"]) for m in mods if m.get("id")}
    for m in list(c.modules):
        if m.id not in keep_ids:
            ModuleProgress.query.filter_by(module_id=m.id).delete()
            c.modules.remove(m)
    existing = {m.id: m for m in c.modules}
    for n, m in enumerate(mods, 1):
        name = (m.get("name") or "").strip()
        if not name:
            continue
        if m.get("id") and int(m["id"]) in existing:
            row = existing[int(m["id"])]
            row.name, row.position, row.description = name, n, m.get("description")
        else:
            c.modules.append(Module(name=name, position=n, description=m.get("description")))


@bp.get("/courses")
@login_required
def list_courses():
    u = current_user()
    q = Course.query
    s = (request.args.get("q") or "").strip()
    if s:
        q = q.filter(db.or_(Course.name.like(f"%{s}%"), Course.code.like(f"%{s}%")))
    return jsonify(items=[course_dict(c, include_fees=u.role == "admin") for c in q.order_by(Course.name).all()])


@bp.get("/courses/<int:cid>")
@login_required
def get_course(cid):
    return jsonify(course=course_dict(db.get_or_404(Course, cid), include_fees=current_user().role == "admin"))


@bp.post("/courses")
@admin_required
def create_course():
    d = request.get_json(silent=True) or {}
    c = Course()
    try:
        _apply_course(c, d)
        if Course.query.filter_by(code=c.code).first():
            return error("A course with that code already exists", 409)
    except ValueError as e:
        db.session.rollback()
        return error(str(e))
    db.session.add(c)
    log_activity("course_created", f"{c.code} {c.name}")
    db.session.commit()
    return jsonify(course=course_dict(c)), 201


@bp.put("/courses/<int:cid>")
@admin_required
def update_course(cid):
    c = db.get_or_404(Course, cid)
    d = request.get_json(silent=True) or {}
    try:
        with db.session.no_autoflush:
            _apply_course(c, d)
            dup = Course.query.filter(Course.code == c.code, Course.id != cid).first()
        if dup:
            db.session.rollback()
            return error("A course with that code already exists", 409)
    except ValueError as e:
        db.session.rollback()
        return error(str(e))
    log_activity("course_updated", f"{c.code} {c.name}")
    db.session.commit()
    return jsonify(course=course_dict(c))


@bp.delete("/courses/<int:cid>")
@admin_required
def delete_course(cid):
    c = db.get_or_404(Course, cid)
    if Student.query.filter_by(course_id=cid).count():
        return error("This course has registered students and cannot be deleted.", 409)
    log_activity("course_deleted", f"{c.code} {c.name}")
    db.session.delete(c)
    db.session.commit()
    return jsonify(message="Course deleted")


# ---------------- intakes ----------------
@bp.get("/intakes")
@login_required
def list_intakes():
    u = current_user()
    q = Intake.query
    if request.args.get("course_id"):
        q = q.filter_by(course_id=request.args.get("course_id", type=int))
    if u.role == "trainer":
        q = q.filter_by(trainer_id=u.id) if request.args.get("mine") else q
    return jsonify(items=[intake_dict(i) for i in q.order_by(Intake.start_date.desc()).all()])


def _apply_intake(i, d):
    i.name = (d.get("name") or "").strip()
    if not i.name:
        raise ValueError("Intake name is required")
    if not d.get("course_id") or not db.session.get(Course, d["course_id"]):
        raise ValueError("Select a valid course")
    i.course_id = d["course_id"]
    i.start_date = parse_date(d.get("start_date"), "start date")
    if not i.start_date:
        raise ValueError("Start date is required")
    i.end_date = parse_date(d.get("end_date"), "end date")
    if i.end_date and i.end_date < i.start_date:
        raise ValueError("End date cannot be before the start date")
    i.trainer_id = d.get("trainer_id") or None


@bp.post("/intakes")
@admin_required
def create_intake():
    i = Intake()
    try:
        _apply_intake(i, request.get_json(silent=True) or {})
    except ValueError as e:
        return error(str(e))
    db.session.add(i)
    db.session.flush()
    if i.trainer_id:
        notify("New class assigned", f"You have been assigned to intake {i.name} ({i.course.name})", user_id=i.trainer_id)
    log_activity("intake_created", f"{i.name} - {i.course.name}")
    db.session.commit()
    return jsonify(intake=intake_dict(i)), 201


@bp.put("/intakes/<int:iid>")
@admin_required
def update_intake(iid):
    i = db.get_or_404(Intake, iid)
    old_trainer = i.trainer_id
    try:
        _apply_intake(i, request.get_json(silent=True) or {})
    except ValueError as e:
        return error(str(e))
    if i.trainer_id and i.trainer_id != old_trainer:
        notify("New class assigned", f"You have been assigned to intake {i.name} ({i.course.name})", user_id=i.trainer_id)
    log_activity("intake_updated", f"{i.name}")
    db.session.commit()
    return jsonify(intake=intake_dict(i))


@bp.delete("/intakes/<int:iid>")
@admin_required
def delete_intake(iid):
    i = db.get_or_404(Intake, iid)
    if Student.query.filter_by(intake_id=iid).count():
        return error("This intake has students and cannot be deleted.", 409)
    log_activity("intake_deleted", i.name)
    db.session.delete(i)
    db.session.commit()
    return jsonify(message="Intake deleted")
