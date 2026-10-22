from datetime import date

from ..extensions import db
from ..models import Attendance, CLEARED, Module, ModuleProgress, Student


def progress_for(student):
    modules = Module.query.filter_by(course_id=student.course_id).order_by(Module.position).all()
    done_rows = {p.module_id: p for p in ModuleProgress.query.filter_by(student_id=student.id).all()}
    items = [{"id": m.id, "name": m.name, "position": m.position, "completed": m.id in done_rows,
              "completed_on": done_rows[m.id].completed_on.isoformat() if m.id in done_rows and done_rows[m.id].completed_on else None}
             for m in modules]
    done = sum(1 for i in items if i["completed"])
    total = len(items)
    return {"modules": items, "completed": done, "remaining": total - done, "total": total,
            "percent": round(done * 100 / total, 1) if total else 0.0}


def expected_percent(student):
    """Share of the course timeline that has elapsed (used for 'behind schedule')."""
    if not student.expected_completion or not student.registration_date:
        return None
    span = (student.expected_completion - student.registration_date).days
    if span <= 0:
        return 100.0
    elapsed = (date.today() - student.registration_date).days
    return max(0.0, min(100.0, elapsed * 100 / span))


def is_behind(student, prog=None):
    if student.status not in ("Active", "In Progress"):
        return False
    prog = prog or progress_for(student)
    exp = expected_percent(student)
    return exp is not None and prog["percent"] + 15 < exp  # 15-point tolerance


def refresh_status(student):
    """Auto-move status Active -> In Progress -> Cleared (Completed) as modules are ticked.
    Suspended / Withdrawn are manual and are left untouched. Returns True if newly cleared."""
    if student.status in ("Suspended", "Withdrawn"):
        return False
    p = progress_for(student)
    newly_cleared = False
    if p["total"] > 0 and p["completed"] == p["total"]:
        if student.status != CLEARED:
            student.status = CLEARED
            student.completed_on = date.today()
            newly_cleared = True
    elif p["completed"] > 0:
        student.status = "In Progress"
        student.completed_on = None
    else:
        student.status = "Active"
        student.completed_on = None
    return newly_cleared


def attendance_stats(student_id):
    rows = Attendance.query.filter_by(student_id=student_id).all()
    total = len(rows)
    c = {"Present": 0, "Absent": 0, "Late": 0}
    for r in rows:
        c[r.status] = c.get(r.status, 0) + 1
    attended = c["Present"] + c["Late"]
    return {"total": total, "present": c["Present"], "absent": c["Absent"], "late": c["Late"],
            "percent": round(attended * 100 / total, 1) if total else None}
