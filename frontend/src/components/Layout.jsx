import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import api from "../api";
import { useAuth } from "../auth.jsx";
import { LogoImg } from "./ui.jsx";

const ADMIN_NAV = [
  ["/", "speedometer2", "Dashboard"],
  ["sec", "People"],
  ["/students", "mortarboard", "Students"],
  ["/trainers", "person-badge", "Trainers"],
  ["sec", "Academics"],
  ["/courses", "journal-bookmark", "Courses & Intakes"],
  ["/attendance", "calendar-check", "Attendance"],
  ["/progress", "graph-up-arrow", "Progress"],
  ["/certificates", "award", "Certificates"],
  ["sec", "Finance"],
  ["/payments", "credit-card", "Payments"],
  ["/reports", "bar-chart-line", "Reports"],
  ["sec", "System"],
  ["/logs", "clipboard-data", "Logs"],
  ["/settings", "gear", "Settings"],
];
const TRAINER_NAV = [
  ["/", "speedometer2", "Dashboard"],
  ["/students", "mortarboard", "My Students"],
  ["/attendance", "calendar-check", "Attendance"],
  ["/progress", "graph-up-arrow", "Progress"],
];

export default function Layout() {
  const { user, logout, isAdmin } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [q, setQ] = useState("");

  useEffect(() => setOpen(false), [loc.pathname]);
  useEffect(() => {
    const load = () => api.get("/notifications", { params: { per_page: 1 } }).then((r) => setUnread(r.data.unread)).catch(() => {});
    load();
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, [loc.pathname]);

  const items = isAdmin ? ADMIN_NAV : TRAINER_NAV;
  return (
    <div className="app">
      <div className={`scrim ${open ? "open" : ""}`} onClick={() => setOpen(false)} />
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="brand"><LogoImg /><div>Tu-Code Academy<small>Student Management</small></div></div>
        <nav className="nav">
          {items.map((it, i) => it[0] === "sec"
            ? <div key={i} className="sec">{it[1]}</div>
            : <NavLink key={it[0]} to={it[0]} end={it[0] === "/"} className={({ isActive }) => (isActive ? "active" : "")}><i className={`bi bi-${it[1]}`}></i>{it[2]}</NavLink>)}
        </nav>
        <div className="side-foot">
          <b>{user.name}</b><span style={{ textTransform: "capitalize" }}>{user.role}</span>
          <div style={{ marginTop: ".5rem", display: "flex", gap: ".5rem" }}>
            <button className="btn sm" onClick={() => nav("/account")}>Account</button>
            <button className="btn sm" onClick={() => { logout(); nav("/login"); }}>Sign out</button>
          </div>
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <button className="burger" onClick={() => setOpen(true)} aria-label="Menu">☰</button>
          <form className="search" onSubmit={(e) => { e.preventDefault(); if (q.trim().length > 1) nav(`/search?q=${encodeURIComponent(q.trim())}`); }}>
            <input placeholder={isAdmin ? "Search name, number, phone, course, receipt, M-Pesa code, certificate…" : "Search students by name, number, phone or course…"} value={q} onChange={(e) => setQ(e.target.value)} />
          </form>
          <button className="bell" onClick={() => nav("/notifications")} aria-label="Notifications">
  <i className="bi bi-bell"></i>
  {unread > 0 && <span className="count">{unread > 99 ? "99+" : unread}</span>}
</button>
        </header>
        <main className="content"><Outlet /></main>
      </div>
    </div>
  );
}
