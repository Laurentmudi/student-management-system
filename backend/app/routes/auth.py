from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token

from ..extensions import db
from ..models import User
from ..utils import current_user, error, log_activity, login_required

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/login")
def login():
    d = request.get_json(silent=True) or {}
    email = (d.get("email") or "").strip().lower()
    u = User.query.filter(db.func.lower(User.email) == email).first()
    if not u or not u.check_password(d.get("password") or ""):
        log_activity("login_failed", f"Failed login for {email}", user=u)
        db.session.commit()
        return error("Invalid email or password", 401)
    if not u.is_active:
        return error("This account has been disabled. Contact the administrator.", 403)
    token = create_access_token(identity=str(u.id), additional_claims={"role": u.role})
    log_activity("login", f"{u.name} signed in", user=u)
    db.session.commit()
    return jsonify(token=token, user=u.to_dict())


@bp.get("/me")
@login_required
def me():
    return jsonify(user=current_user().to_dict())


@bp.post("/change-password")
@login_required
def change_password():
    d = request.get_json(silent=True) or {}
    u = current_user()
    if not u.check_password(d.get("current_password") or ""):
        return error("Current password is incorrect")
    new = d.get("new_password") or ""
    if len(new) < 8:
        return error("New password must be at least 8 characters")
    u.set_password(new)
    log_activity("password_changed", u.name)
    db.session.commit()
    return jsonify(message="Password updated")
