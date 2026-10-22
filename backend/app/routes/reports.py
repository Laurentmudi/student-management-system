from datetime import date

from flask import Blueprint, jsonify, request, send_file

from ..services import pdfs, reports
from ..utils import admin_required, error, log_activity
from ..extensions import db

bp = Blueprint("reports", __name__, url_prefix="/api/reports")


@bp.get("")
@admin_required
def catalogue():
    return jsonify(items=[{"key": k, "title": t} for k, t in reports.REPORT_TITLES.items()])


@bp.get("/<key>")
@admin_required
def run(key):
    fn = reports.REPORTS.get(key)
    if not fn:
        return error("Unknown report", 404)
    args = request.args.to_dict()
    try:
        title, cols, rows, summary = fn(args)
    except ValueError as e:
        return error(str(e))
    fmt = args.get("format", "json")
    log_activity("report_generated", f"{title} ({fmt})")
    db.session.commit()
    if fmt == "pdf":
        sub = ", ".join(f"{k}={v}" for k, v in args.items() if k not in ("format",) and v) or None
        return send_file(pdfs.table_pdf(title, cols, rows, summary, sub), mimetype="application/pdf",
                         download_name=f"{key}-{date.today()}.pdf", as_attachment=True)
    if fmt in ("xlsx", "excel"):
        return send_file(reports.to_xlsx(title, cols, rows, summary),
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                         download_name=f"{key}-{date.today()}.xlsx", as_attachment=True)
    return jsonify(title=title, columns=cols, rows=rows, summary=summary)
