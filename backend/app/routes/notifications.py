from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Notification
from ..utils import current_user, login_required, paginate

bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@bp.get("")
@login_required
def list_mine():
    u = current_user()
    q = Notification.query.filter_by(user_id=u.id)
    if request.args.get("unread") == "1":
        q = q.filter_by(is_read=False)
    unread = Notification.query.filter_by(user_id=u.id, is_read=False).count()
    items, meta = paginate(q.order_by(Notification.created_at.desc(), Notification.id.desc()), 30)
    return jsonify(items=[{"id": n.id, "title": n.title, "message": n.message, "link": n.link, "is_read": n.is_read,
                           "created_at": n.created_at.isoformat()} for n in items], unread=unread, **meta)


@bp.post("/<int:nid>/read")
@login_required
def read_one(nid):
    n = db.get_or_404(Notification, nid)
    if n.user_id == current_user().id:
        n.is_read = True
        db.session.commit()
    return jsonify(ok=True)


@bp.post("/read-all")
@login_required
def read_all():
    Notification.query.filter_by(user_id=current_user().id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify(ok=True)
