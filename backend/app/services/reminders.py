from datetime import date, datetime, timedelta

from ..extensions import db
from ..models import Student
from ..utils import get_setting, notify
from . import fees
from .messaging import send_to_student


def fmt(n):
    return f"{get_setting('currency')} {n:,.2f}"


def build_message(student, due, balance, overdue):
    academy = get_setting("academy_name")
    lead = ("This is a reminder that your fee payment is OVERDUE." if overdue
            else "This is a friendly reminder that a fee payment is coming due.")
    return (f"{academy}: Dear {student.full_name}, {lead} "
            f"Amount due: {fmt(due['outstanding'])}. Due date: {due['due_date']}. "
            f"Total outstanding balance: {fmt(balance)}. Please pay via M-Pesa or at the office. Thank you.")


def run_reminders(today=None):
    """Sends 'before due date' and 'overdue' reminders. Safe to run repeatedly: each
    reminder is de-duplicated per student/installment/period so nobody is spammed."""
    today = today or date.today()
    before = int(get_setting("remind_days_before") or 3)
    every = max(1, int(get_setting("remind_overdue_every") or 7))
    sent = overdue_count = 0
    students = Student.query.filter(Student.status.in_(["Active", "In Progress"])).all()
    for s in students:
        sm = fees.summary(s)
        due = sm["next_due"]
        if not due or sm["balance"] <= 0:
            continue
        due_date = date.fromisoformat(due["due_date"])
        days_to = (due_date - today).days
        key = None
        if 0 <= days_to <= before:
            overdue = False
            key = f"rem:{s.id}:{due['no']}:before"
        elif days_to < 0:
            overdue = True
            period = (-days_to) // every
            key = f"rem:{s.id}:{due['no']}:over{period}"
            overdue_count += 1
        else:
            continue
        res = send_to_student(s, "reminder_overdue" if overdue else "reminder_before",
                              build_message(s, due, sm["balance"], overdue), dedupe_key=key)
        if res:
            sent += len(res)
            if overdue:
                notify("Overdue payment", f"{s.full_name} ({s.student_number}) is overdue: {fmt(due['outstanding'])} since {due['due_date']}",
                       role="admin", link=f"/students/{s.id}")
    db.session.commit()
    return {"messages": sent, "overdue_students": overdue_count}
