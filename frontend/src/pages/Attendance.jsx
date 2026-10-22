import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errMsg } from "../api";
import { Avatar, Empty, Loading, PageHeader, useApi, useToast } from "../components/ui.jsx";

export default function Attendance() {
  const toast = useToast();
  const today = new Date().toISOString().slice(0, 10);
  const { data: classes } = useApi("/classes");
  const [intake, setIntake] = useState("");
  const [date, setDate] = useState(today);
  const { data, loading, reload } = useApi("/attendance/sheet", { intake_id: intake || undefined, date });
  const [rows, setRows] = useState({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!data) return;
    setRows(Object.fromEntries(data.items.map((s) => [s.student_id, { status: s.status, note: s.note || "" }])));
  }, [data]);

  const mark = (id, status) => setRows((r) => ({ ...r, [id]: { ...r[id], status } }));
  const all = (status) => setRows((r) => Object.fromEntries(Object.entries(r).map(([k, v]) => [k, { ...v, status }])));
  const save = async () => {
    const records = Object.entries(rows).filter(([, v]) => v.status).map(([id, v]) => ({ student_id: Number(id), status: v.status, note: v.note }));
    if (!records.length) return toast("Mark at least one student", "err");
    setBusy(true);
    try { const r = await api.post("/attendance/bulk", { date, records }); toast(`Saved attendance for ${r.data.saved} student(s)`); reload(); }
    catch (e) { toast(errMsg(e), "err"); } finally { setBusy(false); }
  };
  const pending = Object.values(rows).filter((v) => !v.status).length;
  return (
    <>
      <PageHeader title="Attendance" sub="Record or edit attendance for a class and date" />
      <div className="filters">
        <select value={intake} onChange={(e) => setIntake(e.target.value)}>
          <option value="">All my students</option>
          {classes?.items.map((c) => <option key={c.id} value={c.id}>{c.name} — {c.course_name} ({c.students})</option>)}
          {classes?.no_intake_students > 0 && <option value="none">Students without an intake ({classes.no_intake_students})</option>}
        </select>
        <input type="date" value={date} max={today} onChange={(e) => setDate(e.target.value || today)} />
        <div style={{ display: "flex", gap: ".4rem", flex: "0 0 auto" }}><button className="btn" onClick={() => all("Present")}>All present</button><button className="btn" onClick={() => all("Absent")}>All absent</button></div>
      </div>
      <div className="card flush">
        {loading && !data ? <Loading /> : !data?.items.length ? <Empty>No active students in this class.</Empty> : (
          <div className="table-wrap"><table><thead><tr><th>Student</th><th>Overall %</th><th>Status on {date}</th><th>Note</th></tr></thead>
            <tbody>{data.items.map((s) => (
              <tr key={s.student_id}>
                <td><div className="person"><Avatar photo={s.photo} name={s.name} /><div><b><Link to={`/students/${s.student_id}?tab=attendance`}>{s.name}</Link></b><small>{s.student_number}</small></div></div></td>
                <td>{s.attendance_percent != null ? s.attendance_percent + "%" : "—"}</td>
                <td><div className="seg">{[["Present", "P"], ["Late", "L"], ["Absent", "A"]].map(([st, c]) => <button key={st} type="button" className={rows[s.student_id]?.status === st ? c : ""} onClick={() => mark(s.student_id, st)}>{st}</button>)}</div></td>
                <td style={{ minWidth: 160 }}><input value={rows[s.student_id]?.note || ""} placeholder="Optional" onChange={(e) => setRows((r) => ({ ...r, [s.student_id]: { ...r[s.student_id], note: e.target.value } }))} /></td>
              </tr>))}</tbody></table></div>)}
        {data?.items.length > 0 && <div className="pager"><span className="muted">{pending ? `${pending} not marked yet` : "All marked"}</span><button className="btn primary" disabled={busy} onClick={save}>{busy ? "Saving…" : "Save attendance"}</button></div>}
      </div>
    </>
  );
}
