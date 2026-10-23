import { Link } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { ErrorBox, Loading, Progress, fdate, money, useApi } from "../components/ui.jsx";

const initials = (n) => (n || "?").split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

const Stat = ({ i, l, v, c = "" }) => (
  <div className={`kpi ${c}`}>
    <div className="kpi-icon"><i className={`bi bi-${i}`}></i></div>
    <div><div className="kpi-l">{l}</div><div className="kpi-v">{v}</div></div>
  </div>
);

const Banner = ({ hello, text, children }) => (
  <div className="banner">
    <div>
      <div className="banner-date">
        <i className="bi bi-calendar3"></i>{" "}
        {new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
      </div>
      <h1>{hello}</h1>
      <p>{text}</p>
    </div>
    <div className="banner-actions">{children}</div>
  </div>
);

function Donut({ data, total }) {
  const R = 52, C = 2 * Math.PI * R;
  let offset = 0;
  const safe = Math.max(1, total);
  return (
    <svg viewBox="0 0 140 140" className="donut" role="img" aria-label="Students by status">
      <circle cx="70" cy="70" r={R} fill="none" stroke="#e2e8f0" strokeWidth="16" />
      {data.filter((x) => x.value > 0).map((x) => {
        const len = (x.value / safe) * C;
        const el = (
          <circle key={x.label} cx="70" cy="70" r={R} fill="none" stroke={x.color} strokeWidth="16"
            strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-offset} transform="rotate(-90 70 70)" />
        );
        offset += len;
        return el;
      })}
      <text x="70" y="68" textAnchor="middle" className="donut-n">{total}</text>
      <text x="70" y="86" textAnchor="middle" className="donut-t">students</text>
    </svg>
  );
}

function Ring({ pct }) {
  const R = 40, C = 2 * Math.PI * R;
  return (
    <svg viewBox="0 0 100 100" className="ring" role="img" aria-label={`${pct}% collected`}>
      <circle cx="50" cy="50" r={R} fill="none" stroke="rgba(255,255,255,.18)" strokeWidth="10" />
      <circle cx="50" cy="50" r={R} fill="none" stroke="#38bdf8" strokeWidth="10" strokeLinecap="round"
        strokeDasharray={`${(pct / 100) * C} ${C}`} transform="rotate(-90 50 50)" />
      <text x="50" y="55" textAnchor="middle" className="ring-n">{pct}%</text>
    </svg>
  );
}

export default function Dashboard() {
  const { user, isAdmin } = useAuth();
  const { data: d, loading, error } = useApi("/dashboard");
  if (loading) return <Loading />;
  if (error) return <ErrorBox msg={error} />;
  const hello = `Welcome back, ${user.name.split(" ")[0]}`;
  return isAdmin ? <Admin d={d} hello={hello} /> : <Trainer d={d} hello={hello} />;
}

function Admin({ d, hello }) {
  const sc = d.status_counts;
  const slices = [
    { label: "Active", value: sc["Active"], color: "#3b82f6" },
    { label: "In Progress", value: sc["In Progress"], color: "#f59e0b" },
    { label: "Cleared (Completed)", value: sc["Cleared (Completed)"], color: "#10b981" },
    { label: "Suspended", value: sc["Suspended"], color: "#ef4444" },
    { label: "Withdrawn", value: sc["Withdrawn"], color: "#94a3b8" },
  ];
  const expected = d.fees_collected + d.outstanding_balances;
  const pct = expected ? Math.round((d.fees_collected * 100) / expected) : 0;

  return (
    <>
      <Banner hello={hello} text="Here is what is happening at the academy today.">
        <Link className="btn light" to="/students/new"><i className="bi bi-person-plus"></i> Register student</Link>
        <Link className="btn ghost-light" to="/payments?new=1"><i className="bi bi-cash-coin"></i> Record payment</Link>
      </Banner>

      <div className="bento">
        <div className="tile dark s5">
          <span className="tile-label"><i className="bi bi-wallet2"></i> Fees collected</span>
          <div className="fin">
            <div>
              <div className="big">{money(d.fees_collected)}</div>
              <div className="sub">{money(d.collected_this_month)} this month</div>
            </div>
            <Ring pct={pct} />
          </div>
          <div className="mini-row">
            <div><small>Outstanding balances</small><b className="neg">{money(d.outstanding_balances)}</b></div>
            <div><small>Payments due (7 days)</small><b>{money(d.payments_due_amount)}</b><em>{d.payments_due_count} student(s)</em></div>
          </div>
        </div>

        <div className="tile s4">
          <span className="tile-label dark-text"><i className="bi bi-pie-chart"></i> Students by status</span>
          <div className="donut-wrap">
            <Donut data={slices} total={d.total_students} />
            <ul className="legend">
              {slices.map((s) => (
                <li key={s.label}><i style={{ background: s.color }}></i><span>{s.label}</span><b>{s.value}</b></li>
              ))}
            </ul>
          </div>
          <div className="pills">
            <span><b>{d.active_students}</b> active</span>
            <span><b>{d.in_progress}</b> in progress</span>
            <span><b>{d.cleared}</b> cleared</span>
          </div>
        </div>

        <div className="tile accent s3">
          <i className="bi bi-journal-bookmark accent-ico"></i>
          <div className="big">{d.total_courses}</div>
          <div className="sub">Courses offered</div>
          <Link to="/courses" className="tile-link">Manage courses <i className="bi bi-arrow-right"></i></Link>
        </div>

        <div className="tile s7">
          <div className="tile-head">
            <span className="tile-label dark-text"><i className="bi bi-receipt"></i> Recent payments</span>
            <Link to="/payments">View all</Link>
          </div>
          {d.recent_payments.map((p) => (
            <div className="feed-row" key={p.id}>
              <div className="ava green">{initials(p.student_name)}</div>
              <div className="feed-main">
                <Link to={`/students/${p.student_id}`}>{p.student_name}</Link>
                <small>{p.receipt_number} · {fdate(p.payment_date)}</small>
              </div>
              <b className="pos">+ {money(p.amount)}</b>
            </div>
          ))}
          {!d.recent_payments.length && <div className="feed-empty">No payments recorded yet.</div>}
        </div>

        <div className="tile s5">
          <div className="tile-head">
            <span className="tile-label dark-text"><i className="bi bi-person-plus"></i> New registrations</span>
            <Link to="/students">View all</Link>
          </div>
          {d.recent_registrations.map((s) => (
            <div className="feed-row" key={s.id}>
              <div className="ava">{initials(s.name)}</div>
              <div className="feed-main">
                <Link to={`/students/${s.id}`}>{s.name}</Link>
                <small>{s.course_name}</small>
              </div>
              <small className="muted">{fdate(s.registration_date)}</small>
            </div>
          ))}
          {!d.recent_registrations.length && <div className="feed-empty">No students registered yet.</div>}
        </div>
      </div>
    </>
  );
}

function Trainer({ d, hello }) {
  return (
    <>
      <Banner hello={hello} text="Your classes and students at a glance.">
        <Link className="btn light" to="/attendance"><i className="bi bi-calendar-check"></i> Record attendance</Link>
      </Banner>
      <div className="grid stats">
        <Stat i="people" l="Assigned Students" v={d.assigned_students} />
        <Stat i="easel" l="Assigned Classes" v={d.assigned_classes} />
        <Stat i="calendar-check" l="Attendance Pending (today)" v={d.attendance_pending} c="amber" />
        <Stat i="hourglass-split" l="Students in Progress" v={d.in_progress} c="amber" />
        <Stat i="patch-check" l="Cleared (Completed)" v={d.cleared} c="green" />
        <Stat i="exclamation-triangle" l="Behind Schedule" v={d.behind_schedule} c="red" />
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