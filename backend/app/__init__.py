import atexit
import os

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .config import Config
from .extensions import cors, db, jwt


def widen_log_column():
    """Older databases created message_logs.to_number as VARCHAR(30); email addresses need more room.
    Safe to run on every start (it does nothing when already widened)."""
    from sqlalchemy import text
    try:
        if db.engine.dialect.name == "mysql":
            db.session.execute(text("ALTER TABLE message_logs MODIFY to_number VARCHAR(150) NULL"))
            db.session.commit()
    except Exception:
        db.session.rollback()

def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    from .routes import (attendance, auth, certificates, courses, dashboard, notifications, payments, progress,
                         public, reports, search, settings, students, users)
    for m in (auth, users, courses, students, payments, attendance, progress, certificates, reports, dashboard,
              search, notifications, settings, public):
        app.register_blueprint(m.bp)

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @jwt.unauthorized_loader
    def _unauth(msg):
        return jsonify(error="Please sign in to continue"), 401

    @jwt.invalid_token_loader
    def _invalid(msg):
        return jsonify(error="Session invalid. Please sign in again."), 401

    @jwt.expired_token_loader
    def _expired(h, p):
        return jsonify(error="Session expired. Please sign in again."), 401

    @app.errorhandler(HTTPException)
    def _http(e):
        return jsonify(error=e.description or e.name), e.code

    @app.errorhandler(Exception)
    def _any(e):
        db.session.rollback()
        app.logger.exception("Unhandled error")
        return jsonify(error="Unexpected server error"), 500

    with app.app_context():
        db.create_all()
        widen_log_column()

    if app.config["ENABLE_SCHEDULER"] and not app.config.get("TESTING"):
        # avoid starting twice under the Flask reloader
        if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
            start_scheduler(app)
    return app


def start_scheduler(app):
    from apscheduler.schedulers.background import BackgroundScheduler
    from .services.reminders import run_reminders
    from .models import Attendance, Student
    from .utils import notify
    from datetime import date

    def reminders_job():
        with app.app_context():
            res = run_reminders()
            app.logger.info("Reminder job: %s", res)

    def attendance_job():
        """Weekday afternoon nudge for trainers who haven't recorded today's attendance."""
        with app.app_context():
            today = date.today()
            if today.weekday() >= 5:
                return
            from .models import User
            for t in User.query.filter_by(role="trainer", is_active=True).all():
                from .utils import trainer_scope_filter
                studs = trainer_scope_filter(Student.query.filter(Student.status.in_(["Active", "In Progress"])), t).all()
                if not studs:
                    continue
                done = Attendance.query.filter(Attendance.date == today, Attendance.student_id.in_([s.id for s in studs])).count()
                if done < len(studs):
                    notify("Attendance reminder", f"Attendance for {today:%d %b} is incomplete ({len(studs) - done} students pending).",
                           user_id=t.id, link="/attendance")
            db.session.commit()

    sched = BackgroundScheduler(timezone="Africa/Nairobi")
    sched.add_job(reminders_job, "cron", hour=app.config["REMINDER_HOUR"], minute=0, id="reminders")
    sched.add_job(attendance_job, "cron", day_of_week="mon-fri", hour=14, minute=0, id="attendance")
    sched.start()
    atexit.register(lambda: sched.shutdown(wait=False))
