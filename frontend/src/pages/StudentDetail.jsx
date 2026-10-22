import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import api, { errMsg, printPdf, viewPdf } from "../api";
import { useAuth } from "../auth.jsx";
import PaymentForm from "../components/PaymentForm.jsx";
import { AuthImage, Avatar, Badge, Empty, ErrorBox, Loading, PageHeader, Progress, fdate, fdatetime, money, useApi, useToast } from "../components/ui.jsx";

export default function StudentDetail() {
  const { id } = useParams();
  const { isAdmin } = useAuth();
  const [sp, setSp] = useSearchParams();
  const tab = sp.get("tab") || "overview";
  const { data, loading, error, reload } = useApi(`/students/${id}`);
  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox msg={error} />;
  const s = data.student;
  const tabs = [["overview", "Overview"], ...(isAdmin ? [["fees", "Fees"], ["payments", "Payments"]] : []), ["progress", "Progress"], ["attendance", "Attendance"], ["remarks", "Remarks"], ...(isAdmin ? [["documents", "Documents"]] : [])];
  return (
    <>
      <PageHeader title={s.full_name} sub={`${s.student_number} · ${s.course_name}`}>
        {isAdmin && <Link className="btn" to={`/students/${s.id}/edit`}>Edit</Link>}
        <Link className="btn" to="/students">← Back</Link>
      </PageHeader>
      <div className="card profile-head">
        {s.photo ? <AuthImage src={s.photo} className="big-photo" alt={s.full_name} /> : <Avatar name={s.full_name} size={96} />}
        <div style={{ flex: 1, minWidth: 220 }}>
          <div className="chips"><Badge text={s.status} />{s.behind_schedule && <span className="badge red">Behind schedule</span>}{isAdmin && s.fees_overdue && <span className="badge red">Fees overdue</span>}</div>
          <div style={{ margin: ".7rem 0 .3rem" }} className="muted">Overall progress ({s.progress.completed}/{s.progress.total} modules)</div>
          <Progress value={s.progress.percent} />
        </div>
        {isAdmin && <div style={{ textAlign: "right" }}><div className="muted">Outstanding balance</div><div style={{ fontSize: "1.5rem", fontWeight: 700, color: s.balance > 0 ? "var(--red)" : "var(--green)" }}>{money(s.balance)}</div></div>}
      </div>
      <div className="tabs">{tabs.map(([k, l]) => <button key={k} className={tab === k ? "on" : ""} onClick={() => setSp({ tab: k })}>{l}</button>)}</div>
      {tab === "overview" && <Overview s={s} isAdmin={isAdmin} />}
      {tab === "fees" && <Fees s={s} onChange={reload} />}
      {tab === "payments" && <StudentPayments s={s} onChange={reload} />}
      {tab === "progress" && <ProgressTab s={s} onChange={reload} />}
      {tab === "attendance" && <AttendanceTab s={s} onChange={reload} />}
      {tab === "remarks" && <Remarks s={s} />}
      {tab === "documents" && <Documents s={s} />}
    </>
  );
}

const KV = ({ k, v }) => <div><small>{k}</small><span>{v || "—"}</span></div>;

function Overview({ s, isAdmin }) {
  return (
    <div className="grid two">
      <div className="card"><h2>Personal & contact</h2><div className="kv">
        <KV k="Gender" v={s.gender} /><KV k="Date of birth" v={s.date_of_birth && fdate(s.date_of_birth)} />
        {isAdmin && <KV k="National ID" v={s.national_id} />}
        <KV k="Phone" v={s.phone} /><KV k="Alt. phone" v={s.alt_phone} /><KV k="Email" v={s.email} /><KV k="Address" v={s.address} /></div></div>
      <div className="card"><h2>Guardian</h2><div className="kv"><KV k="Name" v={s.guardian_name} /><KV k="Relationship" v={s.guardian_relationship} /><KV k="Phone" v={s.guardian_phone} /></div></div>
      <div className="card"><h2>Academic</h2><div className="kv">
        <KV k="Course" v={s.course_name} /><KV k="Intake" v={s.intake_name} /><KV k="Trainer" v={s.trainer_name} />
        <KV k="Registered" v={fdate(s.registration_date)} /><KV k="Expected completion" v={fdate(s.expected_completion)} />
        {s.completed_on && <KV k="Completed on" v={fdate(s.completed_on)} />}</div></div>
      <div className="card"><h2>Attendance</h2><div className="kv">
        <KV k="Attendance rate" v={s.attendance.percent != null ? s.attendance.percent + "%" : "No records"} /><KV k="Present" v={s.attendance.present} /><KV k="Late" v={s.attendance.late} /><KV k="Absent" v={s.attendance.absent} /></div></div>
    </div>
  );
}

function Fees({ s, onChange }) {
  const f = s.fees;
  const [pay, setPay] = useState(false);
  return (
    <>
      <div className="grid stats">
        <div className="stat"><div className="l">Total fees payable</div><div className="v">{money(f.total_payable)}</div></div>
        <div className="stat green"><div className="l">Total fees paid</div><div className="v">{money(f.total_paid)}</div></div>
        <div className="stat red"><div className="l">Outstanding balance</div><div className="v">{money(f.balance)}</div></div>
      </div>
      <div className="card flush">
        <div className="card-head"><h2>Installment schedule</h2>{f.balance > 0 && <button className="btn primary" onClick={() => setPay(true)}>+ Record payment</button>}</div>
        <div className="table-wrap"><table><thead><tr><th>#</th><th>Installment</th><th>Due date</th><th className="right">Amount</th><th className="right">Cumulative</th><th>Status</th></tr></thead>
          <tbody>{f.schedule.map((i) => <tr key={i.no}><td>{i.no}</td><td>{i.label}</td><td>{fdate(i.due_date)} {i.overdue && <span className="badge red">Overdue</span>}</td><td className="right">{money(i.amount)}</td><td className="right">{money(i.cumulative)}</td><td><Badge text={i.status} /></td></tr>)}</tbody></table></div>
      </div>
      {pay && <PaymentForm student={s} onClose={() => setPay(false)} onSaved={onChange} />}
    </>
  );
}

function StudentPayments({ s, onChange }) {
  const toast = useToast();
  const { data, loading, reload } = useApi("/payments", { student_id: s.id, per_page: 100 });
  const [pay, setPay] = useState(false);
  const act = (fn) => fn().catch((e) => toast(errMsg(e), "err"));
  return (
    <div className="card flush">
      <div className="card-head"><h2>Payment history</h2>{s.balance > 0 && <button className="btn primary" onClick={() => setPay(true)}>+ Record payment</button>}</div>
      {loading ? <Loading /> : !data.items.length ? <Empty>No payments recorded.</Empty> : (
        <div className="table-wrap"><table><thead><tr><th>Receipt</th><th>Date</th><th>Method</th><th>M-Pesa code</th><th className="right">Amount</th><th /></tr></thead>
          <tbody>{data.items.map((p) => <tr key={p.id}><td>{p.receipt_number}</td><td>{fdate(p.payment_date)}</td><td>{p.method}</td><td>{p.mpesa_code || "—"}</td><td className="right">{money(p.amount)}</td>
            <td><div className="row-actions"><button className="btn sm" onClick={() => act(() => viewPdf(`/payments/${p.id}/receipt`))}>View / Download</button><button className="btn sm" onClick={() => act(() => printPdf(`/payments/${p.id}/receipt`))}>Print</button></div></td></tr>)}</tbody></table></div>)}
      {pay && <PaymentForm student={s} onClose={() => setPay(false)} onSaved={() => { reload(); onChange(); }} />}
    </div>
  );
}

function ProgressTab({ s, onChange }) {
  const toast = useToast();
  const [p, setP] = useState(s.progress_detail);
  const locked = ["Suspended", "Withdrawn"].includes(s.status);
  const toggle = async (m) => {
    try {
      const r = await api.put(`/students/${s.id}/progress`, { module_id: m.id, completed: !m.completed });
      setP(r.data.progress);
      if (r.data.newly_cleared) toast("🎉 All modules complete — student is now Cleared (Completed)");
      onChange();
    } catch (e) { toast(errMsg(e), "err"); }
  };
  return (
    <div className="card">
      <div className="grid stats" style={{ marginBottom: "1rem" }}>
        <div className="stat green"><div className="l">Modules completed</div><div className="v">{p.completed}</div></div>
        <div className="stat amber"><div className="l">Modules remaining</div><div className="v">{p.remaining}</div></div>
        <div className="stat"><div className="l">Overall progress</div><div className="v">{p.percent}%</div></div>
      </div>
      {locked && <div className="alert info">Progress is locked while the student is {s.status}.</div>}
      {!p.modules.length && <Empty>This course has no modules defined yet.</Empty>}
      {p.modules.map((m) => (
        <div key={m.id} className={`module-row ${m.completed ? "done" : ""}`}>
          <input type="checkbox" checked={m.completed} disabled={locked} onChange={() => toggle(m)} style={{ width: 20, height: 20 }} />
          <div style={{ flex: 1 }}><b>{m.position}. {m.name}</b>{m.completed_on && <div className="muted">Completed {fdate(m.completed_on)}</div>}</div>
          {m.completed ? <Badge text="Paid" /> : null}
        </div>))}
    </div>
  );
}

function AttendanceTab({ s, onChange }) {
  const toast = useToast();
  const { data, loading, reload } = useApi(`/attendance/student/${s.id}`);
  const change = async (a, status) => {
    try { await api.put(`/attendance/${a.id}`, { status }); toast("Attendance updated"); reload(); onChange(); } catch (e) { toast(errMsg(e), "err"); }
  };
  if (loading) return <Loading />;
  const st = data.stats;
  return (
    <>
      <div className="grid stats">
        <div className="stat"><div className="l">Attendance %</div><div className="v">{st.percent ?? "—"}{st.percent != null && "%"}</div></div>
        <div className="stat green"><div className="l">Present</div><div className="v">{st.present}</div></div>
        <div className="stat amber"><div className="l">Late</div><div className="v">{st.late}</div></div>
        <div className="stat red"><div className="l">Absent</div><div className="v">{st.absent}</div></div>
      </div>
      <div className="card flush">
        {!data.items.length ? <Empty>No attendance recorded yet.</Empty> : (
          <div className="table-wrap"><table><thead><tr><th>Date</th><th>Status</th><th>Edit</th></tr></thead>
            <tbody>{data.items.map((a) => <tr key={a.id}><td>{fdate(a.date)}</td><td><Badge text={a.status} /></td>
              <td><select style={{ width: 130 }} value={a.status} onChange={(e) => change(a, e.target.value)}>{["Present", "Late", "Absent"].map((x) => <option key={x}>{x}</option>)}</select></td></tr>)}</tbody></table></div>)}
      </div>
    </>
  );
}

function Remarks({ s }) {
  const toast = useToast();
  const { data, loading, reload } = useApi(`/students/${s.id}/remarks`);
  const [text, setText] = useState("");
  const add = async (e) => {
    e.preventDefault();
    try { await api.post(`/students/${s.id}/remarks`, { text }); setText(""); reload(); toast("Remark added"); } catch (x) { toast(errMsg(x), "err"); }
  };
  return (
    <div className="card">
      <form onSubmit={add} style={{ display: "flex", gap: ".6rem", flexWrap: "wrap", marginBottom: "1rem" }}>
        <textarea rows="2" style={{ flex: 1, minWidth: 220 }} required placeholder="Add a remark on the student's performance…" value={text} onChange={(e) => setText(e.target.value)} />
        <button className="btn primary">Add remark</button>
      </form>
      {loading ? <Loading /> : !data.items.length ? <Empty>No remarks yet.</Empty> : data.items.map((r) => (
        <div className="list-row" key={r.id}><div>{r.text}</div><div className="muted nowrap" style={{ textAlign: "right" }}>{r.author}<br /><small>{fdatetime(r.created_at)}</small></div></div>))}
    </div>
  );
}

function Documents({ s }) {
  return (
    <div className="grid two">
      {[["National ID (front)", s.id_front], ["National ID (back)", s.id_back]].map(([l, f]) => (
        <div className="card" key={l}><h2>{l}</h2>{f ? (f.endsWith(".pdf") ? <DocLink path={f} /> : <AuthImage src={f} className="" alt={l} fallback={<Loading />} />) : <Empty>Not uploaded</Empty>}</div>))}
    </div>
  );
}
function DocLink({ path }) {
  return <button className="btn" onClick={() => api.get(`/files/${path}`, { responseType: "blob" }).then((r) => window.open(URL.createObjectURL(r.data)))}>Open PDF</button>;
}
