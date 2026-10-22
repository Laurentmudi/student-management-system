from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Course, Intake, Student, User
from ..utils import admin_required, error, log_activity, login_required

bp = Blueprint("users", __name__, url_prefix="/api/users")


@bp.get("")
@admin_required
def list_users():
    q = User.query
    role = request.args.get("role")
    if role:
        q = q.filter_by(role=role)
    s = (request.args.get("q") or "").strip()
    if s:
        like = f"%{s}%"
        q = q.filter(db.or_(User.name.like(like), User.email.like(like), User.phone.like(like)))
    out = []
    for u in q.order_by(User.name).all():
        d = u.to_dict()
        d["student_count"] = Student.query.filter_by(trainer_id=u.id).count()
        out.append(d)
    return jsonify(items=out)


@bp.post("")
@admin_required
def create_user():
    d = request.get_json(silent=True) or {}
    name, email = (d.get("name") or "").strip(), (d.get("email") or "").strip().lower()
    if not name or not email:
        return error("Name and email are required")
    if len(d.get("password") or "") < 8:
        return error("Password must be at least 8 characters")
    if User.query.filter(db.func.lower(User.email) == email).first():
        return error("A user with that email already exists", 409)
    role = d.get("role") if d.get("role") in ("admin", "trainer") else "trainer"
    u = User(name=name, email=email, phone=d.get("phone"), role=role)
    u.set_password(d["password"])
    db.session.add(u)
    log_activity("user_created", f"{role} {name} ({email})")
    db.session.commit()
    return jsonify(user=u.to_dict()), 201


@bp.put("/<int:uid>")
@admin_required
def update_user(uid):
    u = db.get_or_404(User, uid)
    d = request.get_json(silent=True) or {}
    if "name" in d and d["name"].strip():
        u.name = d["name"].strip()
    if "phone" in d:
        u.phone = d["phone"]
    if "email" in d:
        email = d["email"].strip().lower()
        other = User.query.filter(db.func.lower(User.email) == email, User.id != uid).first()
        if other:
            return error("Another user already uses that email", 409)
        u.email = email
    if "is_active" in d:
        from ..utils import current_user
        if u.id == current_user().id and not d["is_active"]:
            return error("You cannot disable your own account")
        u.is_active = bool(d["is_active"])
    if d.get("password"):
        if len(d["password"]) < 8:
            return error("Password must be at least 8 characters")
        u.set_password(d["password"])
    log_activity("user_updated", f"{u.name} ({u.email})")
    db.session.commit()
    return jsonify(user=u.to_dict())


@bp.delete("/<int:uid>")
@admin_required
def delete_user(uid):
    from ..utils import current_user
    u = db.get_or_404(User, uid)
    if u.id == current_user().id:
        return error("You cannot delete your own account")
    in_use = (Student.query.filter_by(trainer_id=uid).count() + Intake.query.filter_by(trainer_id=uid).count()
              + Course.query.filter_by(trainer_id=uid).count())
    if in_use:
        return error("This user is assigned to students/courses/intakes. Reassign them or disable the account instead.", 409)
    from ..models import Notification
    Notification.query.filter_by(user_id=uid).delete()
    log_activity("user_deleted", f"{u.name} ({u.email})")
    db.session.delete(u)
    db.session.commit()
    return jsonify(message="User deleted")
