"""Creates the first administrator (and, with --demo, sample data).

    python seed.py            # admin only
    python seed.py --demo     # admin + sample trainers, courses, students, payments
"""
import os
import sys
from datetime import date, timedelta

from app import create_app
from app.extensions import db
from app.models import Course, FeeInstallment, Intake, Module, Payment, Student, User
from app.utils import next_number


def ensure_admin():
    email = os.getenv("ADMIN_EMAIL", "admin@tucode.ac.ke").lower()
    u = User.query.filter_by(email=email).first()
    if u:
        print(f"Admin already exists: {email}")
        return u
    u = User(name=os.getenv("ADMIN_NAME", "System Administrator"), email=email, role="admin")
    u.set_password(os.getenv("ADMIN_PASSWORD", "Admin@12345"))
    db.session.add(u)
    db.session.commit()
    print(f"Created admin {email}")
    return u


def demo(admin):
    if Course.query.count():
        print("Demo data skipped (courses already exist)")
        return
    t1 = User(name="Grace Wanjiru", email="grace@tucode.ac.ke", phone="0711000001", role="trainer")
    t2 = User(name="Peter Otieno", email="peter@tucode.ac.ke", phone="0711000002", role="trainer")
    for t in (t1, t2):
        t.set_password("Trainer@123")
        db.session.add(t)
    db.session.flush()

    def course(code, name, weeks, fee, trainer, modules):
        c = Course(code=code, name=name, duration_weeks=weeks, total_fee=fee, trainer_id=trainer.id,
                   description=f"{name} programme")
        for n, m in enumerate(modules, 1):
            c.modules.append(Module(name=m, position=n))
        a = round(fee * 0.5)
        c.installments += [FeeInstallment(label="Deposit", amount=a, due_after_days=0, position=1),
                           FeeInstallment(label="Second installment", amount=fee - a - round(fee * 0.2), due_after_days=30, position=2),
                           FeeInstallment(label="Final installment", amount=round(fee * 0.2), due_after_days=60, position=3)]
        db.session.add(c)
        return c

    web = course("WDEV", "Full-Stack Web Development", 16, 45000, t1,
                 ["HTML & CSS", "JavaScript Fundamentals", "Python & Flask", "React", "Databases (MySQL)", "Capstone Project"])
    data = course("DSCI", "Data Science with Python", 12, 38000, t2,
                  ["Python Basics", "Data Analysis (Pandas)", "Visualisation", "Machine Learning"])
    db.session.flush()
    i1 = Intake(course_id=web.id, name="Web Dev - Jan 2026", start_date=date.today() - timedelta(days=70), trainer_id=t1.id)
    i2 = Intake(course_id=data.id, name="Data Science - Mar 2026", start_date=date.today() - timedelta(days=35), trainer_id=t2.id)
    db.session.add_all([i1, i2])
    db.session.flush()
    people = [("Brian", "Mwangi", "Male", "0712345601", web, i1, t1), ("Faith", "Achieng", "Female", "0712345602", web, i1, t1),
              ("Kevin", "Kiprop", "Male", "0712345603", data, i2, t2), ("Mercy", "Njeri", "Female", "0712345604", data, i2, t2)]
    for f, l, g, ph, c, i, t in people:
        s = Student(student_number="TMP", first_name=f, last_name=l, gender=g, phone=ph, course_id=c.id, intake_id=i.id,
                    trainer_id=t.id, registration_date=i.start_date, expected_completion=i.start_date + timedelta(weeks=c.duration_weeks),
                    fee_payable=c.total_fee, email=f"{f.lower()}@example.com", address="Nairobi")
        s.student_number = next_number(Student, Student.student_number, "STU", 4)
        db.session.add(s)
        db.session.flush()
    db.session.commit()
    first = Student.query.first()
    p = Payment(receipt_number="TMP", student_id=first.id, amount=22500, method="M-Pesa", mpesa_code="SAMPLE001A",
                payment_date=date.today() - timedelta(days=60), recorded_by=admin.id)
    p.receipt_number = next_number(Payment, Payment.receipt_number, "RCT", 5)
    db.session.add(p)
    db.session.commit()
    print("Demo data created. Trainer logins: grace@tucode.ac.ke / peter@tucode.ac.ke  (password Trainer@123)")


if __name__ == "__main__":
    app = create_app({"ENABLE_SCHEDULER": False})
    with app.app_context():
        admin = ensure_admin()
        if "--demo" in sys.argv:
            demo(admin)
