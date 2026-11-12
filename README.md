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



## 1. What you need to install

| Tool                | Version        | Download                          | Check with            |
|---------------------|----------------|-----------------------------------|-----------------------|
| **Python**          | 3.10 or newer  | https://www.python.org/downloads/ | `python --version`    |
| **Node.js** (+ npm) | 18 or newer    | https://nodejs.org/ (LTS)         | `node -v` and `npm -v`|
| **MySQL Server**    | 8.x (or MariaDB, or the MySQL in XAMPP) | https://dev.mysql.com/downloads/mysql/ | `mysql --version` |
| **Git**             | any recent     | https://git-scm.com/downloads     | `git --version`       |


### Default logins (change the passwords after first sign-in: *Account → Change password*)

| Role          | Email                  | Password       |
|---------------|------------------------|----------------|
| Administrator | `admin@tucode.ac.ke`   | `Admin@12345`  |
| Trainer (demo)| `grace@tucode.ac.ke`   | `Trainer@123`  |
| Trainer (demo)| `peter@tucode.ac.ke`   | `Trainer@123`  |

(The admin email/password come from `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env`. Trainers exist only if you used `--demo`;
otherwise create them in the app under **Trainers**.)
