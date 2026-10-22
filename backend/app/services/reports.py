"""All nine reports return (title, columns, rows, summary-dict, subtitle)."""
import io
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from ..extensions import db
from ..models import Attendance, CLEARED, Certificate, Course, Intake, Payment, Student, User
from ..utils import get_setting, parse_date
from . import fees
from . import progress as prog


def _m(n):
    return f"{float(n):,.2f}"


def _students(a):
    q = Student.query
    if a.get("course_id"):
        q = q.filter(Student.course_id == int(a["course_id"]))
    if a.get("intake_id"):
        q = q.filter(Student.intake_id == int(a["intake_id"]))
    if a.get("status"):
        q = q.filter(Student.status == a["status"])
    return q.order_by(Student.first_name, Student.last_name).all()


def _payments(a):
    q = Payment.query.join(Student, Payment.student_id == Student.id)
    if a.get("course_id"):
        q = q.filter(Student.course_id == int(a["course_id"]))
    if a.get("date_from"):
        q = q.filter(Payment.payment_date >= parse_date(a["date_from"]))
    if a.get("date_to"):
        q = q.filter(Payment.payment_date <= parse_date(a["date_to"]))
    return q.order_by(Payment.payment_date, Payment.id).all()


def student_list(a):
    rows = [[s.student_number, s.full_name, s.gender or "", s.phone, s.email or "", s.course.name,
             s.intake.name if s.intake else "", s.trainer.name if s.trainer else "", s.status,
             s.registration_date.isoformat()] for s in _students(a)]
    return ("Student List", ["Student No.", "Name", "Gender", "Phone", "Email", "Course", "Intake", "Trainer", "Status", "Registered"],
            rows, {"Total students": len(rows)})


def fee_collection(a):
    rows, tot_exp, tot_col = [], 0.0, 0.0
    for c in Course.query.order_by(Course.name).all():
        studs = Student.query.filter_by(course_id=c.id).all()
        exp = sum(float(s.fee_payable) for s in studs)
        q = Payment.query.join(Student, Payment.student_id == Student.id).filter(Student.course_id == c.id)
        if a.get("date_from"):
            q = q.filter(Payment.payment_date >= parse_date(a["date_from"]))
        if a.get("date_to"):
            q = q.filter(Payment.payment_date <= parse_date(a["date_to"]))
        col = float(q.with_entities(db.func.coalesce(db.func.sum(Payment.amount), 0)).scalar() or 0)
        n = q.count()
        paid_all = sum(float(fees.paid_total(s.id)) for s in studs)
        rows.append([c.name, len(studs), n, _m(exp), _m(col), _m(max(0, exp - paid_all)),
                     f"{(paid_all * 100 / exp):.1f}%" if exp else "-"])
        tot_exp += exp
        tot_col += col
    return ("Fee Collection Report", ["Course", "Students", "Payments in period", "Fees Payable", "Collected in period", "Outstanding (all time)", "Collection rate"],
            rows, {"Collected in period": _m(tot_col), "Total fees payable": _m(tot_exp)})


def outstanding(a):
    rows, total = [], 0.0
    for s in _students(a):
        if s.status in ("Withdrawn",):
            continue
        sm = fees.summary(s)
        if sm["balance"] <= 0:
            continue
        nd = sm["next_due"]
        rows.append([s.student_number, s.full_name, s.phone, s.course.name, _m(sm["total_payable"]), _m(sm["total_paid"]),
                     _m(sm["balance"]), nd["due_date"] if nd else "", "OVERDUE" if sm["is_overdue"] else "Pending"])
        total += sm["balance"]
    return ("Outstanding Balances", ["Student No.", "Name", "Phone", "Course", "Payable", "Paid", "Balance", "Next due", "State"],
            rows, {"Students with balance": len(rows), "Total outstanding": _m(total)})


def payment_history(a):
    running = {}
    allp = Payment.query.order_by(Payment.payment_date, Payment.id).all()
    info = {}
    for p in allp:
        running[p.student_id] = running.get(p.student_id, 0.0) + float(p.amount)
        info[p.id] = max(0.0, float(p.student.fee_payable) - running[p.student_id])
    rows, total = [], 0.0
    for p in _payments(a):
        rows.append([p.payment_date.isoformat(), p.receipt_number, p.student.student_number, p.student.full_name,
                     p.method, p.mpesa_code or "", _m(p.amount), _m(info.get(p.id, 0)), p.recorder.name if p.recorder else ""])
        total += float(p.amount)
    return ("Payment History", ["Date", "Receipt", "Student No.", "Student", "Method", "M-Pesa Code", "Amount", "Balance after", "Recorded by"],
            rows, {"Payments": len(rows), "Total": _m(total)})


def attendance_report(a):
    rows = []
    for s in _students(a):
        q = Attendance.query.filter_by(student_id=s.id)
        if a.get("date_from"):
            q = q.filter(Attendance.date >= parse_date(a["date_from"]))
        if a.get("date_to"):
            q = q.filter(Attendance.date <= parse_date(a["date_to"]))
        recs = q.all()
        c = {"Present": 0, "Absent": 0, "Late": 0}
        for r in recs:
            c[r.status] += 1
        t = len(recs)
        rows.append([s.student_number, s.full_name, s.course.name, t, c["Present"], c["Late"], c["Absent"],
                     f"{(c['Present'] + c['Late']) * 100 / t:.1f}%" if t else "-"])
    return ("Attendance Report", ["Student No.", "Name", "Course", "Sessions", "Present", "Late", "Absent", "Attendance %"], rows,
            {"Students": len(rows)})


def progress_report(a):
    rows = []
    for s in _students(a):
        p = prog.progress_for(s)
        rows.append([s.student_number, s.full_name, s.course.name, f"{p['completed']}/{p['total']}", p["remaining"],
                     f"{p['percent']}%", s.status, "Yes" if prog.is_behind(s, p) else "No"])
    return ("Student Progress Report", ["Student No.", "Name", "Course", "Modules done", "Remaining", "Progress", "Status", "Behind schedule"],
            rows, {"Students": len(rows)})


def enrolment(a):
    rows = []
    q = Intake.query
    if a.get("course_id"):
        q = q.filter_by(course_id=int(a["course_id"]))
    for i in q.order_by(Intake.start_date.desc()).all():
        studs = Student.query.filter_by(intake_id=i.id).all()
        cnt = lambda st: sum(1 for s in studs if s.status == st)
        rows.append([i.course.name, i.name, i.start_date.isoformat(), i.trainer.name if i.trainer else "", len(studs),
                     cnt("Active"), cnt("In Progress"), cnt(CLEARED), cnt("Suspended") + cnt("Withdrawn")])
    q2 = Student.query.filter(Student.intake_id.is_(None))
    if a.get("course_id"):
        q2 = q2.filter_by(course_id=int(a["course_id"]))
    for c in Course.query.all():
        studs = [s for s in q2.all() if s.course_id == c.id]
        if studs:
            cnt = lambda st: sum(1 for s in studs if s.status == st)
            rows.append([c.name, "(No intake)", "", "", len(studs), cnt("Active"), cnt("In Progress"), cnt(CLEARED),
                         cnt("Suspended") + cnt("Withdrawn")])
    return ("Course Enrolment Report", ["Course", "Intake", "Start date", "Trainer", "Enrolled", "Active", "In progress", "Cleared", "Suspended/Withdrawn"],
            rows, {"Total enrolled": sum(r[4] for r in rows)})


def completion(a):
    rows = []
    for s in _students({**a, "status": CLEARED}):
        cert = Certificate.query.filter_by(student_id=s.id).first()
        rows.append([s.student_number, s.full_name, s.course.name, s.registration_date.isoformat(),
                     s.completed_on.isoformat() if s.completed_on else "", cert.certificate_number if cert else "Not issued"])
    return ("Course Completion Report", ["Student No.", "Name", "Course", "Registered", "Completed", "Certificate"], rows,
            {"Completed students": len(rows)})


def certificate_issuance(a):
    q = Certificate.query
    if a.get("date_from"):
        q = q.filter(Certificate.issue_date >= parse_date(a["date_from"]))
    if a.get("date_to"):
        q = q.filter(Certificate.issue_date <= parse_date(a["date_to"]))
    rows = [[c.certificate_number, c.student.student_number, c.student.full_name, c.student.course.name,
             c.completion_date.isoformat(), c.issue_date.isoformat(),
             (db.session.get(User, c.issued_by).name if c.issued_by else "")] for c in q.order_by(Certificate.id).all()
            if not a.get("course_id") or c.student.course_id == int(a["course_id"])]
    return ("Certificate Issuance Report", ["Certificate No.", "Student No.", "Name", "Course", "Completed", "Issued", "Issued by"], rows,
            {"Certificates issued": len(rows)})


REPORTS = {
    "students": student_list, "fee-collection": fee_collection, "outstanding": outstanding,
    "payment-history": payment_history, "attendance": attendance_report, "progress": progress_report,
    "enrolment": enrolment, "completion": completion, "certificates": certificate_issuance,
}
REPORT_TITLES = {"students": "Student List", "fee-collection": "Fee Collection", "outstanding": "Outstanding Balances",
                 "payment-history": "Payment History", "attendance": "Attendance Report", "progress": "Student Progress Report",
                 "enrolment": "Course Enrolment Report", "completion": "Course Completion Report",
                 "certificates": "Certificate Issuance Report"}


def to_xlsx(title, columns, rows, summary):
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]
    ws.append([get_setting("academy_name")])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([title, f"Generated {date.today():%d %b %Y}"])
    ws["A2"].font = Font(bold=True, size=12)
    for k, v in (summary or {}).items():
        ws.append([k, v])
        ws.cell(ws.max_row, 1).font = Font(bold=True)
    ws.append([])
    ws.append(columns)
    hdr = ws.max_row
    for cell in ws[hdr]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1D4ED8")
        cell.alignment = Alignment(horizontal="center")
    for r in rows:
        ws.append(list(r))
    for i, col in enumerate(columns, 1):
        width = max([len(str(col))] + [len(str(r[i - 1])) for r in rows if i - 1 < len(r)]) + 3
        ws.column_dimensions[get_column_letter(i)].width = min(width, 45)
    ws.freeze_panes = ws.cell(hdr + 1, 1)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
