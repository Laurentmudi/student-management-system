from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import ActivityLog, MessageLog
from ..services.reminders import run_reminders
from ..utils import (ALLOWED_IMAGE, DEFAULT_SETTINGS, SECRET_SETTINGS, admin_required, all_settings, error,
                     log_activity, paginate, remove_upload, save_upload, set_setting, get_setting)

bp = Blueprint("settings", __name__, url_prefix="/api")


@bp.get("/settings")
@admin_required
def get_settings():
    return jsonify(settings=all_settings(mask=True))


@bp.put("/settings")
@admin_required
def put_settings():
    d = request.get_json(silent=True) or {}
    for k, v in d.items():
        if k not in DEFAULT_SETTINGS or k == "logo":
            continue
        if k in SECRET_SETTINGS and v == "********":
            continue  # unchanged masked secret
        set_setting(k, str(v))
    if d.get("msg_provider") and d["msg_provider"] not in ("log", "twilio", "africastalking"):
        db.session.rollback()
        return error("Unknown messaging provider")
    log_activity("settings_updated", ", ".join(k for k in d if k not in SECRET_SETTINGS))
    db.session.commit()
    return jsonify(settings=all_settings(mask=True))


@bp.post("/settings/logo")
@admin_required
def upload_logo():
    try:
        rel = save_upload(request.files.get("logo"), "branding", ALLOWED_IMAGE)
    except ValueError as e:
        return error(str(e))
    if not rel:
        return error("No file uploaded")
    remove_upload(get_setting("logo"))
    set_setting("logo", rel)
    log_activity("logo_updated")
    db.session.commit()
    return jsonify(logo=rel)


@bp.post("/settings/run-reminders")
@admin_required
def run_now():
    res = run_reminders()
    log_activity("reminders_run", str(res))
    db.session.commit()
    return jsonify(**res)


@bp.get("/activity-logs")
@admin_required
def activity_logs():
    from ..models import User
    q = ActivityLog.query
    s = (request.args.get("q") or "").strip()
    if s:
        q = q.filter(db.or_(ActivityLog.action.like(f"%{s}%"), ActivityLog.detail.like(f"%{s}%")))
    items, meta = paginate(q.order_by(ActivityLog.id.desc()), 25)
    return jsonify(items=[{"id": a.id, "user": a.user.name if a.user else "—", "action": a.action, "detail": a.detail,
                           "ip": a.ip, "created_at": a.created_at.isoformat()} for a in items], **meta)


@bp.get("/message-logs")
@admin_required
def message_logs():
    q = MessageLog.query
    if request.args.get("status"):
        q = q.filter_by(status=request.args["status"])
    items, meta = paginate(q.order_by(MessageLog.id.desc()), 25)
    return jsonify(items=[{"id": m.id, "student": m.student.full_name if m.student else "—", "channel": m.channel,
                           "kind": m.kind, "to": m.to_number, "body": m.body, "status": m.status, "error": m.error,
                           "created_at": m.created_at.isoformat()} for m in items], **meta)
