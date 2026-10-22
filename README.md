# Tu-Code Academy — Student Management System

A full-stack web application for Tu-Code Academy: student registration, courses & intakes, trainers, fee
structures and installments, payments with PDF receipts, SMS/WhatsApp payment reminders, attendance,
progress tracking, certificates, dashboards, reports (PDF / Excel), search, notifications, activity logs
and role-based access (Administrator / Trainer).

| Layer    | Technology                                                        |
|----------|-------------------------------------------------------------------|
| Frontend | React 18 + Vite + React Router + Axios (responsive, mobile-ready) |
| Backend  | Python Flask (REST API), SQLAlchemy, JWT auth, ReportLab, openpyxl|
| Database | MySQL (8.x or MariaDB 10.x / XAMPP)                               |

> The requirements document lists PHP for the backend; this build follows the request to use **Flask + React + MySQL**.
> Every functional requirement in the document is implemented (see the checklist at the bottom).

```
student-management-system/
├── backend/      Flask API  (app/, tests/, seed.py, run.py, requirements.txt, .env.example)
├── frontend/     React app  (src/, package.json, vite.config.js)
├── database/     setup.sql (create DB + user)  ·  schema.sql (optional reference schema)
└── README.md
```

---------------------------------------------------------------------------------------------------

## 1. What you need to install

| Tool                | Version        | Download                          | Check with            |
|---------------------|----------------|-----------------------------------|-----------------------|
| **Python**          | 3.10 or newer  | https://www.python.org/downloads/ | `python --version`    |
| **Node.js** (+ npm) | 18 or newer    | https://nodejs.org/ (LTS)         | `node -v` and `npm -v`|
| **MySQL Server**    | 8.x (or MariaDB, or the MySQL in XAMPP) | https://dev.mysql.com/downloads/mysql/ | `mysql --version` |
| **Git**             | any recent     | https://git-scm.com/downloads     | `git --version`       |

On Windows tick **"Add Python to PATH"** during the Python install. Use any editor (VS Code recommended).

---------------------------------------------------------------------------------------------------

## 2. Create the database

Make sure MySQL is running, then from the project folder run (enter your MySQL root password when asked):

```bash
mysql -u root -p < database/setup.sql
```

This creates database `tucode_sms` and a user `sms_user` / `sms_password`.
(Using XAMPP/phpMyAdmin instead? Open the SQL tab and paste the contents of `database/setup.sql`.)

The application creates all tables itself on first start. `database/schema.sql` is only a reference copy.

---------------------------------------------------------------------------------------------------

## 3. Run the backend (Flask API on http://localhost:5000)

**Linux / macOS**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python seed.py --demo        # creates the admin account (+ sample data; omit --demo for a clean system)
python run.py
```

**Windows (PowerShell / CMD)**
```bat
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python seed.py --demo
python run.py
```

Open `backend/.env` and change the values marked **CHANGE THESE** (SECRET_KEY, JWT_SECRET_KEY) — and the
database password if you used a different one. Check it works: http://localhost:5000/api/health → `{"status":"ok"}`.

### Default logins (change the passwords after first sign-in: *Account → Change password*)

| Role          | Email                  | Password       |
|---------------|------------------------|----------------|
| Administrator | `admin@tucode.ac.ke`   | `Admin@12345`  |
| Trainer (demo)| `grace@tucode.ac.ke`   | `Trainer@123`  |
| Trainer (demo)| `peter@tucode.ac.ke`   | `Trainer@123`  |

(The admin email/password come from `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env`. Trainers exist only if you used `--demo`;
otherwise create them in the app under **Trainers**.)

---------------------------------------------------------------------------------------------------

## 4. Run the frontend (React on http://localhost:5173)

Open a **second terminal**:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** and sign in. In development, Vite forwards `/api/...` to the Flask server automatically.

---------------------------------------------------------------------------------------------------

## 5. Git (already initialised)

The folder is already a Git repository with commits on branch `main`.

```bash
git status
git log --oneline
```

To publish it on GitHub: create an **empty** repository there, then

```bash
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

Secrets are protected: `.gitignore` excludes `backend/.env`, `venv/`, `node_modules/`, uploads and build output.
Never commit your real `.env`.

---------------------------------------------------------------------------------------------------

## 6. Using the system — typical workflow

1. **Settings** → academy name, address, logo, certificate signatory (used on receipts and certificates).
2. **Trainers** → add trainer accounts.
3. **Courses & Intakes** → create a course with modules, total fee and optional installments (they must add up
   to the fee), then create intakes and assign trainers.
4. **Students → Register student** → student number is generated automatically; upload photo and ID front/back.
5. **Payments → Record payment** (or from the student's *Fees* tab). A PDF receipt with QR code is generated; view,
   download, print or reprint it any time.
6. **Trainer** signs in → records **Attendance**, ticks **Progress** modules, adds **Remarks**.
   When every module is ticked the student becomes **Cleared (Completed)** automatically.
7. **Certificates** → eligible students appear; generate, download, print/reprint the PDF (QR verifies publicly).
8. **Reports** → nine reports, on screen or downloaded as PDF / Excel.

### Automatic SMS & WhatsApp reminders
* A scheduler inside the backend runs **every day at 08:00 (Nairobi time)** (`REMINDER_HOUR` in `.env`).
  It sends a reminder *N days before* each installment is due and repeats *overdue* reminders every N days
  (configurable in **Settings**), including student name, amount due, due date and outstanding balance.
  Nobody receives the same reminder twice. *Settings → Run reminders now* triggers it on demand.
* Payment confirmations, course-completion and "certificate ready" messages are sent automatically too.
* **Out of the box the provider is "Log only"**: messages are written to *Logs → SMS / WhatsApp messages* but not
  delivered, so you can test safely. To send real messages go to **Settings → SMS / WhatsApp provider**:
  * **Twilio** — SMS and WhatsApp (needs a Twilio account; use the WhatsApp sandbox/number for testing).
  * **Africa's Talking** — SMS (popular in Kenya).
* Keep the backend running continuously (see production notes) so the daily job fires.

### Roles and security
* **Administrator**: everything. **Trainer**: only their own students/classes; no fees, payments, balances,
  financial reports, certificates or settings — enforced on the **server** (API returns 403 / omits money fields),
  not just hidden in the menu.
* Passwords are hashed, login uses JWT tokens (12 h), and every important action is written to the **Activity log**.
* Identity-document scans are visible to administrators only.

---------------------------------------------------------------------------------------------------

## 7. Run the automated tests (optional)

The backend has 15 end-to-end tests (registration → fees → receipts → progress → certificates → reports, plus
trainer permission checks) that run against a real MySQL database.

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS tucode_sms_test CHARACTER SET utf8mb4; GRANT ALL ON tucode_sms_test.* TO 'sms_user'@'localhost';"
cd backend && python -m pytest -q tests
```
(The tests wipe and recreate tables in `tucode_sms_test` only — never your real database.)

---------------------------------------------------------------------------------------------------

## 8. Putting it online (production notes)

* Backend: `pip install -r requirements.txt` then `gunicorn -w 2 -b 127.0.0.1:5000 "app:create_app()"`
  (use **one** worker if you rely on the built-in scheduler, or set `ENABLE_SCHEDULER=0` and call
  `POST /api/settings/run-reminders` from a cron job). Put it behind Nginx/Apache with HTTPS.
* Frontend: `cd frontend && npm run build`, serve the `dist/` folder with Nginx, and either proxy `/api` to Flask or set
  `VITE_API_URL=https://your-domain/api` before building.
* In `backend/.env` set strong `SECRET_KEY` / `JWT_SECRET_KEY`, set `FRONTEND_URL` to your public site
  (it is embedded in the receipt/certificate QR codes) and `CORS_ORIGINS` to the same address.
* Back up the MySQL database and the `backend/uploads/` folder regularly.

## 9. Troubleshooting

| Problem | Fix |
|---------|-----|
| `Access denied for user 'sms_user'` | Re-run `database/setup.sql`, and make sure `DB_USER/DB_PASSWORD` in `backend/.env` match. |
| `Can't connect to MySQL server` | Start MySQL (XAMPP: click *Start* beside MySQL). Check `DB_HOST/DB_PORT`. |
| `cryptography` / `caching_sha2_password` error | `pip install cryptography` (already in requirements). |
| Login page shows "Network Error" | The backend isn't running — start `python run.py` in `backend/`. |
| `pip` not found / python not found (Windows) | Reinstall Python with *Add to PATH*, reopen the terminal. |
| Port 5000 busy (macOS AirPlay) | Change the port in `backend/run.py` **and** the proxy target in `frontend/vite.config.js`. |
| Forgot admin password | `cd backend && python -c "from app import create_app; from app.models import User; from app.extensions import db; a=create_app({'ENABLE_SCHEDULER':False}); c=a.app_context(); c.push(); u=User.query.filter_by(role='admin').first(); u.set_password('NewPass#123'); db.session.commit()"` |

---------------------------------------------------------------------------------------------------

## Requirements checklist (from *Student Management System Requirements.docx*)

| § | Requirement | Where |
|---|-------------|-------|
| 1 | Responsive web app (desktop + mobile) | Whole UI; slide-out menu on phones |
| 2 | Admin / Trainer roles; trainer sees only assigned students, no finances | `utils.py`, `serializers.py`, route guards |
| 3 | Student registration (auto number, photo, contacts, guardian, academic, ID front/back) | Students → Register |
| 4 | Courses, intakes, modules, duration, trainers | Courses & Intakes |
| 5 | Fee structure, installments, auto totals / paid / balance | Course form, student *Fees* tab |
| 6 | Payments: record, edit, search, history; receipt no., M-Pesa code | Payments |
| 7 | Automatic reminders before/after due date via SMS & WhatsApp | `services/reminders.py`, `messaging.py`, scheduler |
| 8 | PDF receipts with logo, QR; download / print / reprint | Payments |
| 9 | Progress: completed / remaining / %, auto "Cleared (Completed)" | Student → Progress |
| 10 | Attendance Present/Absent/Late, edit, history, % | Attendance |
| 11 | Certificates: only for Cleared; PDF, QR, auto number, reprint | Certificates |
| 12 | Admin & trainer dashboards | Dashboard |
| 13 | Nine reports as PDF and Excel | Reports |
| 14 | Search by name, number, phone, course, receipt, M-Pesa code, certificate no. | Top search bar + list filters |
| 15 | Student / admin / trainer notifications | In-app bell + SMS/WhatsApp to students |
| 16 | Secure login, password protection, RBAC, activity logs | Auth, Logs |
| 17 | Database MySQL, PDFs, SMS, WhatsApp, responsive | ✔ (backend in Flask as requested) |
