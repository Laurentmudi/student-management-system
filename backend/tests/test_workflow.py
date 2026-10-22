"""End-to-end test of the whole system against MySQL: registration -> fees -> receipts -> progress
-> certificate -> reports, plus the Administrator/Trainer permission boundary."""
import io
from datetime import date

from app.extensions import db
from app.models import User

state = {}


def uid(email):
    return User.query.filter_by(email=email).first().id


def test_auth_required(client):
    assert client.get("/api/students").status_code == 401
    assert client.post("/api/auth/login", json={"email": "admin@test.com", "password": "bad"}).status_code == 401


def test_create_course_with_fee_structure(client, admin_h, app):
    with app.app_context():
        tid = uid("trainer@test.com")
    bad = client.post("/api/courses", headers=admin_h, json={
        "code": "PY", "name": "Python", "duration_weeks": 8, "total_fee": 30000, "trainer_id": tid,
        "installments": [{"label": "A", "amount": 10000, "due_after_days": 0}], "modules": [{"name": "M1"}]})
    assert bad.status_code == 400  # installments must sum to total
    r = client.post("/api/courses", headers=admin_h, json={
        "code": "PY", "name": "Python", "duration_weeks": 8, "total_fee": 30000, "trainer_id": tid,
        "installments": [{"label": "Deposit", "amount": 10000, "due_after_days": 0},
                         {"label": "Balance", "amount": 20000, "due_after_days": 30}],
        "modules": [{"name": "Basics"}, {"name": "Flask"}]})
    assert r.status_code == 201, r.get_json()
    state["course"] = r.get_json()["course"]
    assert len(state["course"]["modules"]) == 2


def test_intake_and_student_registration(client, admin_h, app):
    with app.app_context():
        tid = uid("trainer@test.com")
    r = client.post("/api/intakes", headers=admin_h, json={"course_id": state["course"]["id"], "name": "Jan 2026",
                                                           "start_date": "2026-01-10", "trainer_id": tid})
    assert r.status_code == 201
    state["intake"] = r.get_json()["intake"]
    data = {"first_name": "Amina", "last_name": "Hassan", "gender": "Female", "phone": "0712000111",
            "national_id": "12345678", "course_id": state["course"]["id"], "intake_id": state["intake"]["id"],
            "date_of_birth": "2000-05-05", "registration_date": "2026-01-10",
            "photo": (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 50), "p.png"),
            "id_front": (io.BytesIO(b"x" * 20), "front.jpg"), "id_back": (io.BytesIO(b"x" * 20), "back.pdf")}
    r = client.post("/api/students", headers=admin_h, data=data, content_type="multipart/form-data")
    assert r.status_code == 201, r.get_json()
    s = r.get_json()["student"]
    assert s["student_number"].startswith("STU-") and s["status"] == "Active"
    assert s["trainer_id"] == uid_cached("trainer@test.com", app)  # defaulted from intake
    assert s["fee_payable"] == 30000 and s["balance"] == 30000
    state["student"] = s
    # duplicate national ID rejected
    data["photo"] = (io.BytesIO(b"x"), "p.png"); data["id_front"] = (io.BytesIO(b"x"), "f.jpg"); data["id_back"] = (io.BytesIO(b"x"), "b.jpg")
    assert client.post("/api/students", headers=admin_h, data=data, content_type="multipart/form-data").status_code == 400
    # wrong file type rejected
    d2 = {"first_name": "X", "last_name": "Y", "phone": "07", "course_id": state["course"]["id"], "photo": (io.BytesIO(b"x"), "evil.exe")}
    assert client.post("/api/students", headers=admin_h, data=d2, content_type="multipart/form-data").status_code == 400


def uid_cached(email, app):
    with app.app_context():
        return uid(email)


def test_payments_receipts_and_balances(client, admin_h):
    sid = state["student"]["id"]
    # M-Pesa requires a code
    assert client.post("/api/payments", headers=admin_h, json={"student_id": sid, "amount": 5000, "method": "M-Pesa"}).status_code == 400
    r = client.post("/api/payments", headers=admin_h, json={"student_id": sid, "amount": 12000, "method": "M-Pesa",
                                                            "mpesa_code": "qwe123abc", "payment_date": "2026-01-10"})
    assert r.status_code == 201, r.get_json()
    p = r.get_json()["payment"]
    assert p["receipt_number"].startswith("RCT-") and p["mpesa_code"] == "QWE123ABC"
    assert r.get_json()["fees"]["balance"] == 18000
    state["payment"] = p
    # duplicate M-Pesa code, overpayment
    assert client.post("/api/payments", headers=admin_h, json={"student_id": sid, "amount": 100, "method": "M-Pesa", "mpesa_code": "QWE123ABC"}).status_code == 400
    assert client.post("/api/payments", headers=admin_h, json={"student_id": sid, "amount": 99999, "method": "Cash"}).status_code == 400
    # PDF receipt
    pdf = client.get(f"/api/payments/{p['id']}/receipt", headers=admin_h)
    assert pdf.status_code == 200 and pdf.data[:4] == b"%PDF"
    # edit payment
    r = client.put(f"/api/payments/{p['id']}", headers=admin_h, json={"amount": 10000, "method": "M-Pesa", "mpesa_code": "QWE123ABC", "payment_date": "2026-01-10"})
    assert r.status_code == 200
    fees = client.get(f"/api/students/{sid}/fees", headers=admin_h).get_json()["fees"]
    assert fees["total_paid"] == 10000 and fees["balance"] == 20000
    # installment 1 (10000) paid; installment 2 overdue (registered Jan 2026, due +30d)
    assert fees["schedule"][0]["status"] == "Paid" and fees["schedule"][1]["overdue"] is True
    # search by receipt & M-Pesa code
    assert client.get("/api/payments?q=QWE123", headers=admin_h).get_json()["total"] == 1
    assert client.get(f"/api/search?q={p['receipt_number']}", headers=admin_h).get_json()["payments"]


def test_public_receipt_verification_has_no_balance(client):
    r = client.get(f"/api/public/verify/receipt/{state['payment']['receipt_number']}")
    assert r.status_code == 200 and "balance" not in r.get_json()
    assert client.get("/api/public/verify/receipt/NOPE").status_code == 404


def test_reminders_run_and_are_deduplicated(client, admin_h):
    r1 = client.post("/api/settings/run-reminders", headers=admin_h).get_json()
    assert r1["messages"] >= 1 and r1["overdue_students"] == 1
    r2 = client.post("/api/settings/run-reminders", headers=admin_h).get_json()
    assert r2["messages"] == 0  # same period -> no duplicate spam
    logs = client.get("/api/message-logs", headers=admin_h).get_json()["items"]
    assert any(l["kind"] == "reminder_overdue" and "Outstanding" in l["body"].title() or "outstanding" in l["body"] for l in logs)
    assert {l["channel"] for l in logs} >= {"sms", "whatsapp"}


def test_trainer_cannot_see_finances(client, trainer_h, trainer2_h):
    sid = state["student"]["id"]
    s = client.get(f"/api/students/{sid}", headers=trainer_h).get_json()["student"]
    for k in ("fee_payable", "fees_paid", "balance", "fees", "id_front", "national_id_scan"):
        assert k not in s, k
    lst = client.get("/api/students", headers=trainer_h).get_json()["items"]
    assert lst and all("balance" not in x for x in lst)
    c = client.get("/api/courses", headers=trainer_h).get_json()["items"][0]
    assert "total_fee" not in c and "installments" not in c
    for path in ("/api/payments", f"/api/students/{sid}/fees", "/api/reports/outstanding", "/api/settings",
                 "/api/certificates", "/api/activity-logs", "/api/users"):
        assert client.get(path, headers=trainer_h).status_code == 403, path
    assert client.post("/api/payments", headers=trainer_h, json={"student_id": sid, "amount": 1}).status_code == 403
    assert client.get(f"/api/payments/{state['payment']['id']}/receipt", headers=trainer_h).status_code == 403
    d = client.get("/api/dashboard", headers=trainer_h).get_json()
    assert "fees_collected" not in d and d["assigned_students"] == 1
    # search never returns payments to trainers
    assert client.get("/api/search?q=QWE123", headers=trainer_h).get_json()["payments"] == []
    # another trainer sees nothing of this student
    assert client.get(f"/api/students/{sid}", headers=trainer2_h).status_code == 403
    assert client.get("/api/students", headers=trainer2_h).get_json()["total"] == 0
    assert client.get(f"/api/attendance/student/{sid}", headers=trainer2_h).status_code == 403
    assert client.get(f"/api/files/{state['student'].get('id_front') or 'ids/x'}", headers=trainer_h).status_code == 403


def test_attendance(client, trainer_h, trainer2_h):
    sid = state["student"]["id"]
    sheet = client.get(f"/api/attendance/sheet?intake_id={state['intake']['id']}&date=2026-02-02", headers=trainer_h).get_json()
    assert len(sheet["items"]) == 1
    for day, st in (("2026-02-02", "Present"), ("2026-02-03", "Late"), ("2026-02-04", "Absent"), ("2026-02-05", "Present")):
        assert client.post("/api/attendance/bulk", headers=trainer_h, json={"date": day, "records": [{"student_id": sid, "status": st}]}).get_json()["saved"] == 1
    h = client.get(f"/api/attendance/student/{sid}", headers=trainer_h).get_json()
    assert h["stats"]["percent"] == 75.0 and h["stats"]["total"] == 4  # present + late counted as attended
    aid = h["items"][0]["id"]
    assert client.put(f"/api/attendance/{aid}", headers=trainer_h, json={"status": "Absent"}).status_code == 200
    assert client.post("/api/attendance/bulk", headers=trainer2_h, json={"date": "2026-02-02", "records": [{"student_id": sid, "status": "Present"}]}).status_code == 403
    assert client.post("/api/attendance/bulk", headers=trainer_h, json={"date": "2999-01-01", "records": []}).status_code == 400


def test_certificate_blocked_until_cleared_then_progress_clears(client, admin_h, trainer_h):
    sid = state["student"]["id"]
    r = client.post("/api/certificates", headers=admin_h, json={"student_id": sid})
    assert r.status_code == 409
    mods = state["course"]["modules"]
    r = client.put(f"/api/students/{sid}/progress", headers=trainer_h, json={"module_id": mods[0]["id"], "completed": True}).get_json()
    assert r["status"] == "In Progress" and r["progress"]["percent"] == 50.0 and r["progress"]["remaining"] == 1
    assert client.post("/api/certificates", headers=admin_h, json={"student_id": sid}).status_code == 409
    r = client.put(f"/api/students/{sid}/progress", headers=trainer_h, json={"module_id": mods[1]["id"], "completed": True}).get_json()
    assert r["status"] == "Cleared (Completed)" and r["newly_cleared"] is True
    # remark
    assert client.post(f"/api/students/{sid}/remarks", headers=trainer_h, json={"text": "Excellent work"}).status_code == 201
    assert client.get(f"/api/students/{sid}/remarks", headers=admin_h).get_json()["items"][0]["text"] == "Excellent work"
    # eligible list
    assert [e["id"] for e in client.get("/api/certificates/eligible", headers=admin_h).get_json()["items"]] == [sid]
    # admin got notified of completion
    n = client.get("/api/notifications", headers=admin_h).get_json()
    assert any("completed" in x["title"].lower() for x in n["items"])


def test_certificate_generation_and_verification(client, admin_h, trainer_h):
    sid = state["student"]["id"]
    r = client.post("/api/certificates", headers=admin_h, json={"student_id": sid})
    assert r.status_code == 201, r.get_json()
    c = r.get_json()["certificate"]
    assert c["certificate_number"].startswith("TCA-CERT-")
    assert client.post("/api/certificates", headers=admin_h, json={"student_id": sid}).status_code == 409  # no duplicates
    pdf = client.get(f"/api/certificates/{c['id']}/pdf", headers=admin_h)
    assert pdf.status_code == 200 and pdf.data[:4] == b"%PDF"
    v = client.get(f"/api/public/verify/certificate/{c['certificate_number']}").get_json()
    assert v["valid"] and v["student_name"] == "Amina Hassan"
    # cannot revert progress once certificate issued
    r = client.put(f"/api/students/{sid}/progress", headers=trainer_h, json={"module_id": state["course"]["modules"][0]["id"], "completed": False})
    assert r.status_code == 400
    assert client.get(f"/api/search?q={c['certificate_number']}", headers=admin_h).get_json()["certificates"]


def test_dashboards(client, admin_h, trainer_h):
    d = client.get("/api/dashboard", headers=admin_h).get_json()
    assert d["total_students"] == 1 and d["cleared"] == 1 and d["fees_collected"] == 10000
    assert d["outstanding_balances"] == 20000 and d["total_courses"] == 1
    t = client.get("/api/dashboard", headers=trainer_h).get_json()
    assert t["cleared"] == 1 and t["assigned_classes"] == 1


def test_all_reports_in_all_formats(client, admin_h):
    keys = [r["key"] for r in client.get("/api/reports", headers=admin_h).get_json()["items"]]
    assert len(keys) == 9
    for k in keys:
        j = client.get(f"/api/reports/{k}", headers=admin_h)
        assert j.status_code == 200 and j.get_json()["columns"], k
        assert client.get(f"/api/reports/{k}?format=pdf", headers=admin_h).data[:4] == b"%PDF", k
        x = client.get(f"/api/reports/{k}?format=xlsx", headers=admin_h)
        assert x.data[:2] == b"PK", k  # xlsx is a zip
    out = client.get("/api/reports/outstanding", headers=admin_h).get_json()
    assert out["rows"][0][6] == "20,000.00"


def test_search_and_student_filters(client, admin_h):
    for q in ("Amina", "STU-", "0712000111", "Python"):
        assert client.get(f"/api/students?q={q}", headers=admin_h).get_json()["total"] == 1, q
    assert client.get("/api/students?q=zzzz", headers=admin_h).get_json()["total"] == 0


def test_activity_log_and_rules(client, admin_h):
    logs = client.get("/api/activity-logs?per_page=200", headers=admin_h).get_json()["items"]
    actions = {l["action"] for l in logs}
    assert {"student_registered", "payment_recorded", "certificate_issued", "login"} <= actions
    # student with payments can't be deleted; course with students can't be deleted
    assert client.delete(f"/api/students/{state['student']['id']}", headers=admin_h).status_code == 409
    assert client.delete(f"/api/courses/{state['course']['id']}", headers=admin_h).status_code == 409


def test_user_management_and_password_change(client, admin_h):
    r = client.post("/api/users", headers=admin_h, json={"name": "New Trainer", "email": "new@test.com", "password": "Secret123!", "role": "trainer"})
    assert r.status_code == 201
    assert client.post("/api/users", headers=admin_h, json={"name": "Dup", "email": "NEW@test.com", "password": "Secret123!"}).status_code == 409
    login = client.post("/api/auth/login", json={"email": "new@test.com", "password": "Secret123!"}).get_json()
    h = {"Authorization": "Bearer " + login["token"]}
    assert client.post("/api/auth/change-password", headers=h, json={"current_password": "wrong", "new_password": "Another123!"}).status_code == 400
    assert client.post("/api/auth/change-password", headers=h, json={"current_password": "Secret123!", "new_password": "Another123!"}).status_code == 200
    client.put(f"/api/users/{r.get_json()['user']['id']}", headers=admin_h, json={"is_active": False})
    assert client.post("/api/auth/login", json={"email": "new@test.com", "password": "Another123!"}).status_code == 403
