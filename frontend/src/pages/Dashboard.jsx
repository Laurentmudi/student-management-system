import { Link } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { Avatar, Badge, ErrorBox, Loading, PageHeader, Progress, fdate, money, useApi } from "../components/ui.jsx";

const Stat = ({ l, v, c = "" }) => <div className={`stat ${c}`}><div className="l">{l}</div><div className="v">{v}</div></div>;

export default function Dashboard() {
  const { user, isAdmin } = useAuth();
  const { data: d, loading, error } = useApi("/dashboard");
  if (loading) return <Loading />;
  if (error) return <ErrorBox msg={error} />;
  const hello = `Welcome back, ${user.name.split(" ")[0]}`;
  return isAdmin ? <Admin d={d} hello={hello} /> : <Trainer d={d} hello={hello} />;
}

function Admin({ d, hello }) {
  const total = Math.max(1, d.total_students);
  return (
    <>
      <PageHeader title="Administrator Dashboard" sub={hello}>
        <Link className="btn primary" to="/students/new">+ Register student</Link>
        <Link className="btn" to="/payments?new=1">+ Record payment</Link>
      </PageHeader>
      <div className="grid stats">
        <Stat l="Total Students" v={d.total_students} />
        <Stat l="Active Students" v={d.active_students} />
        <Stat l="Students in Progress" v={d.in_progress} c="amber" />
        <Stat l="Cleared (Completed)" v={d.cleared} c="green" />
        <Stat l="Total Courses" v={d.total_courses} />
        <Stat l="Fees Collected" v={money(d.fees_collected)} c="green" />
        <Stat l="Outstanding Balances" v={money(d.outstanding_balances)} c="red" />
        <Stat l={`Payments Due (7 days) · ${money(d.payments_due_amount)}`} v={d.payments_due_count} c="amber" />
      </div>
      <div className="grid two">
        <div className="card flush">
          <div className="card-head"><h2>Recent Payments</h2><Link to="/payments">View all</Link></div>
          <div className="table-wrap"><table><thead><tr><th>Receipt</th><th>Student</th><th>Date</th><th className="right">Amount</th></tr></thead>
            <tbody>{d.recent_payments.map((p) => (
              <tr key={p.id}><td>{p.receipt_number}</td><td><Link to={`/students/${p.student_id}`}>{p.student_name}</Link></td><td>{fdate(p.payment_date)}</td><td className="right">{money(p.amount)}</td></tr>))}
              {!d.recent_payments.length && <tr><td colSpan="4" className="muted">No payments yet</td></tr>}</tbody></table></div>
        </div>
        <div className="card flush">
          <div className="card-head"><h2>Recent Registrations</h2><Link to="/students">View all</Link></div>
          <div className="table-wrap"><table><thead><tr><th>Student</th><th>Course</th><th>Registered</th></tr></thead>
            <tbody>{d.recent_registrations.map((s) => (
              <tr key={s.id}><td><Link to={`/students/${s.id}`}>{s.name}</Link><br /><small className="muted">{s.student_number}</small></td><td>{s.course_name}</td><td>{fdate(s.registration_date)}</td></tr>))}
              {!d.recent_registrations.length && <tr><td colSpan="3" className="muted">No students yet</td></tr>}</tbody></table></div>
        </div>
      </div>
      <div className="grid two">
        <div className="card"><h2>Students by status</h2><div className="status-bars">
          {Object.entries(d.status_counts).map(([k, v]) => <div className="row" key={k}><span>{k}</span><div className="b"><i style={{ width: (v * 100) / total + "%" }} /></div><b>{v}</b></div>)}
        </div></div>
        <div className="card"><h2>This month</h2><div className="stat green" style={{ boxShadow: "none", padding: ".4rem 1rem" }}><div className="l">Collected this month</div><div className="v">{money(d.collected_this_month)}</div></div></div>
      </div>
    </>
  );
}

function Trainer({ d, hello }) {
  return (
    <>
      <PageHeader title="Trainer Dashboard" sub={hello}><Link className="btn primary" to="/attendance">Record attendance</Link></PageHeader>
      <div className="grid stats">
        <Stat l="Assigned Students" v={d.assigned_students} />
        <Stat l="Assigned Classes" v={d.assigned_classes} />
        <Stat l="Attendance Pending (today)" v={d.attendance_pending} c="amber" />
        <Stat l="Students in Progress" v={d.in_progress} c="amber" />
        <Stat l="Cleared (Completed)" v={d.cleared} c="green" />
        <Stat l="Behind Schedule" v={d.behind_schedule} c="red" />
      </div>
      <div className="card flush">
        <div className="card-head"><h2>Students behind schedule</h2><Link to="/progress">All progress</Link></div>
        <div className="table-wrap"><table><thead><tr><th>Student</th><th>Course</th><th>Progress</th></tr></thead>
          <tbody>{d.behind_list.map((s) => <tr key={s.id}><td><Link to={`/students/${s.id}?tab=progress`}>{s.name}</Link><br /><small className="muted">{s.student_number}</small></td><td>{s.course_name}</td><td style={{ width: 200 }}><Progress value={s.percent} small /></td></tr>)}
            {!d.behind_list.length && <tr><td colSpan="3" className="muted">Great — nobody is behind schedule.</td></tr>}</tbody></table></div>
      </div>
    </>
  );
}
