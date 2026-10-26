from datetime import datetime, date
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db

STUDENT_STATUSES = ["Active", "In Progress", "Cleared (Completed)", "Suspended", "Withdrawn"]
CLEARED = "Cleared (Completed)"


class User(db.Model):
    """Administrators and Trainers share this table; `role` decides access."""
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(30))
    role = db.Column(db.String(20), nullable=False, default="trainer")  # admin | trainer
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email, "phone": self.phone,
                "role": self.role, "is_active": self.is_active,
                "created_at": self.created_at.isoformat() if self.created_at else None}


class Course(db.Model):
    __tablename__ = "courses"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    duration_weeks = db.Column(db.Integer, default=12, nullable=False)
    total_fee = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    trainer_id = db.Column(db.Integer, db.ForeignKey("users.id"))  # lead trainer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    trainer = db.relationship("User")
    modules = db.relationship("Module", backref="course", cascade="all, delete-orphan",
                              order_by="Module.position")
    installments = db.relationship("FeeInstallment", backref="course", cascade="all, delete-orphan",
                                   order_by="FeeInstallment.position")
    intakes = db.relationship("Intake", backref="course", cascade="all, delete-orphan")


class Module(db.Model):
    __tablename__ = "modules"
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(255))
    position = db.Column(db.Integer, default=1, nullable=False)


class FeeInstallment(db.Model):
    """Fee structure: a course's fee is split into installments, each due N days after registration."""
    __tablename__ = "fee_installments"
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    label = db.Column(db.String(80), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    due_after_days = db.Column(db.Integer, default=0, nullable=False)
    position = db.Column(db.Integer, default=1, nullable=False)


class Intake(db.Model):
    __tablename__ = "intakes"
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    trainer_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    trainer = db.relationship("User")


class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    student_number = db.Column(db.String(30), unique=True, nullable=False)
    photo = db.Column(db.String(255))
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(10))
    date_of_birth = db.Column(db.Date)
    national_id = db.Column(db.String(30))
    phone = db.Column(db.String(30), nullable=False)
    alt_phone = db.Column(db.String(30))
    email = db.Column(db.String(150))
    address = db.Column(db.String(255))
    guardian_name = db.Column(db.String(120))
    guardian_relationship = db.Column(db.String(60))
    guardian_phone = db.Column(db.String(30))
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    intake_id = db.Column(db.Integer, db.ForeignKey("intakes.id"))
    trainer_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    registration_date = db.Column(db.Date, default=date.today, nullable=False)
    expected_completion = db.Column(db.Date)
    status = db.Column(db.String(30), default="Active", nullable=False)
    completed_on = db.Column(db.Date)
    id_front = db.Column(db.String(255))
    id_back = db.Column(db.String(255))
    fee_payable = db.Column(db.Numeric(12, 2), default=0, nullable=False)  # snapshot of course fee
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    course = db.relationship("Course")
    intake = db.relationship("Intake")
    trainer = db.relationship("User")
    payments = db.relationship("Payment", backref="student", cascade="all, delete-orphan",
                               order_by="Payment.payment_date.desc()")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    receipt_number = db.Column(db.String(30), unique=True, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    payment_date = db.Column(db.Date, default=date.today, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    method = db.Column(db.String(30), nullable=False, default="M-Pesa")
    mpesa_code = db.Column(db.String(30), unique=True)
    notes = db.Column(db.String(255))
    recorded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    recorder = db.relationship("User")


class ModuleProgress(db.Model):
    __tablename__ = "module_progress"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey("modules.id"), nullable=False)
    completed_on = db.Column(db.Date, default=date.today)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    __table_args__ = (db.UniqueConstraint("student_id", "module_id", name="uq_student_module"),)


class Remark(db.Model):
    __tablename__ = "remarks"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship("User")


class Attendance(db.Model):
    __tablename__ = "attendance"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), nullable=False)  # Present | Absent | Late
    note = db.Column(db.String(255))
    recorded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    __table_args__ = (db.UniqueConstraint("student_id", "date", name="uq_student_date"),)


class Certificate(db.Model):
    __tablename__ = "certificates"
    id = db.Column(db.Integer, primary_key=True)
    certificate_number = db.Column(db.String(30), unique=True, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), unique=True, nullable=False)
    completion_date = db.Column(db.Date, nullable=False)
    issue_date = db.Column(db.Date, default=date.today, nullable=False)
    issued_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    student = db.relationship("Student")


class MessageLog(db.Model):
    """Every SMS / WhatsApp message the system sends (or simulates)."""
    __tablename__ = "message_logs"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"))
    channel = db.Column(db.String(15), nullable=False)  # sms | whatsapp
    kind = db.Column(db.String(30), nullable=False)  # reminder_before | reminder_overdue | payment | completion | certificate
    dedupe_key = db.Column(db.String(80), index=True)
    to_number = db.Column(db.String(150)) 
    body = db.Column(db.Text)
    status = db.Column(db.String(20))  # sent | simulated | failed
    error = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship("Student")


class Notification(db.Model):
    """In-app notifications. user_id NULL + role set = broadcast to that role."""
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    role = db.Column(db.String(20))
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.String(500))
    link = db.Column(db.String(200))
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(60), nullable=False)
    detail = db.Column(db.String(500))
    ip = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User")


class Setting(db.Model):
    __tablename__ = "settings"
    key = db.Column(db.String(60), primary_key=True)
    value = db.Column(db.Text)


def money(v):
    return Decimal(v or 0).quantize(Decimal("0.01"))
