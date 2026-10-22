from .models import Student
from .services import fees
from .services import progress as prog
from .utils import num


def course_dict(c, include_fees=True):
    d = {"id": c.id, "code": c.code, "name": c.name, "description": c.description,
         "duration_weeks": c.duration_weeks, "trainer_id": c.trainer_id,
         "trainer_name": c.trainer.name if c.trainer else None,
         "modules": [{"id": m.id, "name": m.name, "description": m.description, "position": m.position} for m in c.modules],
         "student_count": Student.query.filter_by(course_id=c.id).count()}
    if include_fees:
        d["total_fee"] = num(c.total_fee)
        d["installments"] = [{"id": i.id, "label": i.label, "amount": num(i.amount),
                              "due_after_days": i.due_after_days} for i in c.installments]
    return d


def intake_dict(i):
    return {"id": i.id, "course_id": i.course_id, "course_name": i.course.name, "name": i.name,
            "start_date": i.start_date.isoformat() if i.start_date else None,
            "end_date": i.end_date.isoformat() if i.end_date else None,
            "trainer_id": i.trainer_id, "trainer_name": i.trainer.name if i.trainer else None,
            "student_count": Student.query.filter_by(intake_id=i.id).count()}


def student_dict(s, user, detail=False):
    d = {
        "id": s.id, "student_number": s.student_number, "photo": s.photo,
        "first_name": s.first_name, "last_name": s.last_name, "full_name": s.full_name,
        "gender": s.gender, "date_of_birth": s.date_of_birth.isoformat() if s.date_of_birth else None,
        "national_id": s.national_id, "phone": s.phone, "alt_phone": s.alt_phone, "email": s.email,
        "address": s.address, "guardian_name": s.guardian_name,
        "guardian_relationship": s.guardian_relationship, "guardian_phone": s.guardian_phone,
        "course_id": s.course_id, "course_name": s.course.name,
        "intake_id": s.intake_id, "intake_name": s.intake.name if s.intake else None,
        "trainer_id": s.trainer_id, "trainer_name": s.trainer.name if s.trainer else None,
        "registration_date": s.registration_date.isoformat() if s.registration_date else None,
        "expected_completion": s.expected_completion.isoformat() if s.expected_completion else None,
        "completed_on": s.completed_on.isoformat() if s.completed_on else None,
        "status": s.status,
    }
    p = prog.progress_for(s)
    d["progress"] = {k: p[k] for k in ("completed", "remaining", "total", "percent")}
    if detail:
        d["has_id_front"] = bool(s.id_front)
        d["has_id_back"] = bool(s.id_back)
        d["progress_detail"] = p
        d["attendance"] = prog.attendance_stats(s.id)
        d["behind_schedule"] = prog.is_behind(s, p)
    if user.role == "admin":
        # financial data is ONLY ever attached for administrators
        sm = fees.summary(s)
        d["fee_payable"] = sm["total_payable"]
        d["fees_paid"] = sm["total_paid"]
        d["balance"] = sm["balance"]
        d["fees_overdue"] = sm["is_overdue"]
        if detail:
            d["id_front"] = s.id_front
            d["id_back"] = s.id_back
            d["fees"] = sm
    return d


def payment_dict(p):
    return {"id": p.id, "receipt_number": p.receipt_number, "student_id": p.student_id,
            "student_name": p.student.full_name, "student_number": p.student.student_number,
            "course_name": p.student.course.name, "payment_date": p.payment_date.isoformat(),
            "amount": num(p.amount), "method": p.method, "mpesa_code": p.mpesa_code, "notes": p.notes,
            "recorded_by": p.recorder.name if p.recorder else None}


def certificate_dict(c):
    return {"id": c.id, "certificate_number": c.certificate_number, "student_id": c.student_id,
            "student_name": c.student.full_name, "student_number": c.student.student_number,
            "course_name": c.student.course.name, "completion_date": c.completion_date.isoformat(),
            "issue_date": c.issue_date.isoformat()}
