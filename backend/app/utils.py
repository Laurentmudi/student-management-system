import os
import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from functools import wraps

from flask import current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from werkzeug.utils import secure_filename

from .extensions import db
from .models import ActivityLog, Notification, Setting, Student, User, Intake

ALLOWED_IMAGE = {"png", "jpg", "jpeg", "webp"}
ALLOWED_DOC = ALLOWED_IMAGE | {"pdf"}

DEFAULT_SETTINGS = {
    "academy_name": "Tu-Code Academy",
    "academy_address": "Nairobi, Kenya",
    "academy_phone": "",
    "academy_email": "",
    "signatory_name": "Academy Director",
    "signatory_title": "Authorized Signature",
    "logo": "",
    "currency": "KES",
    "msg_provider": "log",           # log | twilio | africastalking
    "channel_sms": "1",
    "channel_whatsapp": "1",
    "remind_days_before": "3",       # send a reminder N days before the due date
    "remind_overdue_every": "7",     # repeat overdue reminders every N days
    "twilio_sid": "", "twilio_token": "", "twilio_sms_from": "", "twilio_whatsapp_from": "",
    "at_username": "", "at_api_key": "", "at_sender_id": "",
}
SECRET_SETTINGS = {"twilio_token", "at_api_key"}


# ---------- settings ----------
def get_setting(key):
    row = db.session.get(Setting, key)
    if row is not None and row.value is not None:
        return row.value
    return DEFAULT_SETTINGS.get(key, "")


def all_settings(mask=False):
    out = {k: get_setting(k) for k in DEFAULT_SETTINGS}
    if mask:
        for k in SECRET_SETTINGS:
            out[k] = "********" if out[k] else ""
    return out


def set_setting(key, value):
    row = db.session.get(Setting, key)
    if row is None:
        db.session.add(Setting(key=key, value=value))
    else:
        row.value = value


# ---------- auth ----------
def current_user():
    uid = get_jwt_identity()
    return db.session.get(User, int(uid)) if uid else None


def roles_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            verify_jwt_in_request()
            u = current_user()
            if not u or not u.is_active:
                return jsonify(error="Account disabled or not found"), 401
            if roles and u.role not in roles:
                return jsonify(error="You do not have permission to access this resource"), 403
            return fn(*a, **kw)
        return wrapper
    return deco


admin_required = roles_required("admin")
login_required = roles_required()


def log_activity(action, detail="", user=None):
    try:
        u = user or current_user()
        db.session.add(ActivityLog(user_id=u.id if u else None, action=action, detail=(detail or "")[:500],
                                   ip=(request.remote_addr or "")[:45]))
    except Exception:  # logging must never break a request
        pass


def notify(title, message="", role=None, user_id=None, link=None):
    """Creates an in-app notification for one user, or for every active user of a role."""
    ids = [user_id] if user_id else [u.id for u in User.query.filter_by(role=role, is_active=True).all()] if role else []
    for uid in ids:
        db.session.add(Notification(title=title, message=(message or "")[:500], user_id=uid, link=link))


# ---------- trainer scope ----------
def trainer_scope_filter(query, user):
    """Restrict a Student query to what a trainer may see."""
    if user.role == "admin":
        return query
    intake_ids = [i.id for i in Intake.query.filter_by(trainer_id=user.id).all()]
    cond = Student.trainer_id == user.id
    if intake_ids:
        cond = db.or_(cond, Student.intake_id.in_(intake_ids))
    return query.filter(cond)


def can_access_student(user, student):
    if user.role == "admin":
        return True
    if student.trainer_id == user.id:
        return True
    return bool(student.intake and student.intake.trainer_id == user.id)


# ---------- numbering ----------
def next_number(model, column, prefix, width=5, year=True):
    """Generates e.g. TCA-2026-00012 using the highest existing sequence for the year."""
    y = date.today().year
    stem = f"{prefix}-{y}-" if year else f"{prefix}-"
    last = (model.query.filter(column.like(stem + "%")).order_by(column.desc()).first())
    seq = 1
    if last:
        m = re.search(r"(\d+)$", getattr(last, column.key))
        if m:
            seq = int(m.group(1)) + 1
    return f"{stem}{seq:0{width}d}"


# ---------- files ----------
def ext_of(filename):
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def save_upload(file_storage, subdir, allowed=ALLOWED_DOC):
    if not file_storage or not file_storage.filename:
        return None
    ext = ext_of(file_storage.filename)
    if ext not in allowed:
        raise ValueError(f"File type .{ext} is not allowed. Allowed: {', '.join(sorted(allowed))}")
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subdir)
    os.makedirs(folder, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(folder, secure_filename(name)))
    return f"{subdir}/{name}"


def remove_upload(rel):
    if not rel:
        return
    path = os.path.abspath(os.path.join(current_app.config["UPLOAD_FOLDER"], rel))
    if path.startswith(os.path.abspath(current_app.config["UPLOAD_FOLDER"])) and os.path.isfile(path):
        os.remove(path)


# ---------- parsing ----------
def parse_date(v, field="date"):
    if v in (None, ""):
        return None
    if isinstance(v, date):
        return v
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid {field}: expected YYYY-MM-DD")


def to_decimal(v, field="amount"):
    try:
        d = Decimal(str(v).replace(",", ""))
    except Exception:
        raise ValueError(f"Invalid {field}")
    return d


def num(v):
    return float(v or 0)


def normalize_phone(p):
    """Converts Kenyan numbers to E.164 (+2547XXXXXXXX). Other numbers returned with a leading +."""
    if not p:
        return ""
    s = re.sub(r"[^\d+]", "", p)
    if s.startswith("+"):
        return s
    if s.startswith("00"):
        return "+" + s[2:]
    if s.startswith("0") and len(s) == 10:
        return "+254" + s[1:]
    if s.startswith("254"):
        return "+" + s
    if len(s) == 9 and s[0] in "17":
        return "+254" + s
    return "+" + s


def error(msg, code=400):
    return jsonify(error=msg), code


def paginate(query, default_per_page=20):
    page = max(1, request.args.get("page", 1, type=int))
    per = min(200, max(1, request.args.get("per_page", default_per_page, type=int)))
    total = query.count()
    items = query.limit(per).offset((page - 1) * per).all()
    return items, {"page": page, "per_page": per, "total": total, "pages": max(1, -(-total // per))}
