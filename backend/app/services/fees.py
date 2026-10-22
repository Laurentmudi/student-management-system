from datetime import date, timedelta
from decimal import Decimal

from ..models import Payment, Student
from ..extensions import db


def paid_total(student_id):
    v = db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0)).filter(Payment.student_id == student_id).scalar()
    return Decimal(v or 0)


def schedule(student, paid=None):
    """Builds the student's installment schedule from the course fee structure.
    Returns a list of dicts with cumulative amounts, due dates and paid/partial/pending/overdue status."""
    paid = Decimal(paid if paid is not None else paid_total(student.id))
    total = Decimal(student.fee_payable or 0)
    items = [(i.label, Decimal(i.amount), i.due_after_days) for i in student.course.installments]
    if not items:
        items = [("Full fee", total, 0)]
    # keep the schedule consistent with the student's own payable amount (e.g. after a discount)
    diff = total - sum(a for _, a, _ in items)
    if diff != 0:
        l, a, d = items[-1]
        items[-1] = (l, max(Decimal(0), a + diff), d)
    today = date.today()
    out, cum = [], Decimal(0)
    for idx, (label, amount, days) in enumerate(items, 1):
        prev = cum
        cum += amount
        due = student.registration_date + timedelta(days=days)
        if paid >= cum:
            status = "Paid"
        elif paid > prev:
            status = "Partial"
        else:
            status = "Pending"
        out.append({
            "no": idx, "label": label, "amount": float(amount), "cumulative": float(cum),
            "due_date": due.isoformat(), "status": status,
            "outstanding": float(max(Decimal(0), cum - paid)) if status != "Paid" else 0.0,
            "overdue": status != "Paid" and due < today,
        })
    return out


def summary(student):
    paid = paid_total(student.id)
    total = Decimal(student.fee_payable or 0)
    sched = schedule(student, paid)
    nxt = next((s for s in sched if s["status"] != "Paid"), None)
    return {
        "total_payable": float(total),
        "total_paid": float(paid),
        "balance": float(max(Decimal(0), total - paid)),
        "schedule": sched,
        "next_due": nxt,
        "is_overdue": bool(nxt and nxt["overdue"]),
    }
