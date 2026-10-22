from datetime import date

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import CLEARED, Certificate, Course, Module, ModuleProgress, Remark, Student
from ..services import progress as prog
from ..services.messaging import send_to_student
from ..utils import (can_access_student, current_user, error, get_setting, log_activity, login_required, notify,
                     paginate, trainer_scope_filter)

bp = Blueprint("progress", __name__, url_prefix="/api")


def _student_or_403(sid):
    s = db.get_or_404(Student, sid)
    if not can_access_student(current_user(), s):
        return None, error("This student is not assigned to you", 403)
    return s, None


@bp.get("/students/<int:sid>/progress")
@login_required
def get_progress(sid):
    s, err = _student_or_403(sid)
    if err:
        return err
    return jsonify(progress=prog.progress_for(s), status=s.status)


@bp.put("/students/<int:sid>/progress")
@login_required
def set_progress(sid):
    """Body: {module_id, completed: true|false}. Auto-updates the student's status."""
    s, err = _student_or_403(sid)
    if err:
        return err
    d = request.get_json(silent=True) or {}
    m = db.session.get(Module, d.get("module_id") or 0)
    if not m or m.course_id != s.course_id:
        return error("Module does not belong to this student's course")
    if s.status in ("Suspended", "Withdrawn"):
        return error(f"Progress cannot be updated while the student is {s.status}")
    row = ModuleProgress.query.filter_by(student_id=s.id, module_id=m.id).first()
    if d.get("completed", True):
        if not row:
            db.session.add(ModuleProgress(student_id=s.id, module_id=m.id, completed_on=date.today(), updated_by=current_user().id))
    elif row:
        if Certificate.query.filter_by(student_id=s.id).first():
            return error("A certificate has already been issued; progress can no longer be reverted")
        db.session.delete(row)
    db.session.flush()
    newly = prog.refresh_status(s)
    if newly:
        notify("Student completed course", f"{s.full_name} ({s.student_number}) completed {s.course.name}", role="admin", link="/certificates")
        send_to_student(s, "completion",
                        f"{get_setting('academy_name')}: Congratulations {s.full_name}! You have completed {s.course.name}. "
                        f"Your certificate will be issued shortly.", dedupe_key=f"done:{s.id}")
    log_activity("progress_updated", f"{s.student_number} {m.name} -> {'done' if d.get('completed', True) else 'undone'}")
    db.session.commit()
    return jsonify(progress=prog.progress_for(s), status=s.status, newly_cleared=newly)


@bp.get("/students/<int:sid>/remarks")
@login_required
def list_remarks(sid):
    s, err = _student_or_403(sid)
    if err:
        return err
    rows = Remark.query.filter_by(student_id=sid).order_by(Remark.created_at.desc()).all()
    return jsonify(items=[{"id": r.id, "text": r.text, "author": r.author.name if r.author else "—",
                           "created_at": r.created_at.isoformat()} for r in rows])


@bp.post("/students/<int:sid>/remarks")
@login_required
def add_remark(sid):
    s, err = _student_or_403(sid)
    if err:
        return err
    text = ((request.get_json(silent=True) or {}).get("text") or "").strip()
    if not text:
        return error("Remark cannot be empty")
    db.session.add(Remark(student_id=sid, author_id=current_user().id, text=text))
    log_activity("remark_added", f"{s.student_number}")
    db.session.commit()
    return jsonify(message="Remark added"), 201


@bp.get("/progress/overview")
@login_required
def overview():
    u = current_user()
    q = trainer_scope_filter(Student.query, u)
    if request.args.get("course_id", type=int):
        q = q.filter(Student.course_id == request.args.get("course_id", type=int))
    if request.args.get("status"):
        q = q.filter(Student.status == request.args.get("status"))
    else:
        q = q.filter(Student.status.in_(["Active", "In Progress", CLEARED]))
    term = (request.args.get("q") or "").strip()
    if term:
        q = q.filter(db.or_(Student.first_name.like(f"%{term}%"), Student.last_name.like(f"%{term}%"),
                            Student.student_number.like(f"%{term}%")))
    items, meta = paginate(q.order_by(Student.first_name))
    out = []
    for s in items:
        p = prog.progress_for(s)
        out.append({"id": s.id, "student_number": s.student_number, "name": s.full_name, "course_name": s.course.name,
                    "status": s.status, "completed": p["completed"], "remaining": p["remaining"], "total": p["total"],
                    "percent": p["percent"], "behind": prog.is_behind(s, p)})
    return jsonify(items=out, **meta)
