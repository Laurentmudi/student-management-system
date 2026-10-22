import { useState } from "react";
import api, { errMsg } from "../api";
import { Confirm, ErrorBox, Field, Loading, Modal, PageHeader, Empty, fdate, money, useApi, useToast } from "../components/ui.jsx";

export default function Courses() {
  const [tab, setTab] = useState("courses");
  return (
    <>
      <PageHeader title="Courses & Intakes" sub="Define courses, modules, fee structures and intakes" />
      <div className="tabs"><button className={tab === "courses" ? "on" : ""} onClick={() => setTab("courses")}>Courses</button><button className={tab === "intakes" ? "on" : ""} onClick={() => setTab("intakes")}>Intakes</button></div>
      {tab === "courses" ? <CourseList /> : <IntakeList />}
    </>
  );
}

function CourseList() {
  const toast = useToast();
  const { data, loading, error, reload } = useApi("/courses");
  const [edit, setEdit] = useState(null);
  const [del, setDel] = useState(null);
  const remove = async () => {
    try { await api.delete(`/courses/${del.id}`); toast("Course deleted"); setDel(null); reload(); } catch (e) { toast(errMsg(e), "err"); setDel(null); }
  };
  return (
    <>
      <div className="actions" style={{ marginBottom: "1rem" }}><button className="btn primary" onClick={() => setEdit({})}>+ New course</button></div>
      <ErrorBox msg={error} />
      {loading ? <Loading /> : !data.items.length ? <div className="card"><Empty>No courses yet. Create your first course.</Empty></div> : (
        <div className="grid two">{data.items.map((c) => (
          <div className="card" key={c.id}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: ".5rem" }}><div><span className="badge blue">{c.code}</span><h3 style={{ marginTop: ".4rem" }}>{c.name}</h3></div><div style={{ textAlign: "right" }}><b style={{ fontSize: "1.1rem" }}>{money(c.total_fee)}</b><div className="muted">{c.duration_weeks} weeks</div></div></div>
            <p className="muted">{c.description || "No description"}</p>
            <div className="kv" style={{ marginBottom: ".8rem" }}><div><small>Lead trainer</small><span>{c.trainer_name || "—"}</span></div><div><small>Modules</small><span>{c.modules.length}</span></div><div><small>Students</small><span>{c.student_count}</span></div></div>
            <details><summary className="muted" style={{ cursor: "pointer" }}>Modules & fee structure</summary>
              <ol>{c.modules.map((m) => <li key={m.id}>{m.name}</li>)}</ol>
              <ul>{c.installments.map((i) => <li key={i.id}>{i.label}: {money(i.amount)} (due {i.due_after_days === 0 ? "at registration" : `after ${i.due_after_days} days`})</li>)}{!c.installments.length && <li>Single payment of the full fee</li>}</ul></details>
            <div className="row-actions" style={{ marginTop: ".8rem", display: "flex", gap: ".4rem" }}><button className="btn sm" onClick={() => setEdit(c)}>Edit</button><button className="btn sm" onClick={() => setDel(c)}>Delete</button></div>
          </div>))}</div>)}
      {edit && <CourseForm course={edit} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); reload(); }} />}
      {del && <Confirm title="Delete course" message={`Delete "${del.name}"? This cannot be undone. Courses with registered students cannot be deleted.`} onYes={remove} onNo={() => setDel(null)} />}
    </>
  );
}

function CourseForm({ course, onClose, onSaved }) {
  const toast = useToast();
  const { data: trainers } = useApi("/users", { role: "trainer" });
  const [f, setF] = useState({ code: course.code || "", name: course.name || "", description: course.description || "", duration_weeks: course.duration_weeks || 12, total_fee: course.total_fee ?? "", trainer_id: course.trainer_id || "" });
  const [modules, setModules] = useState(course.modules?.length ? course.modules.map((m) => ({ ...m })) : [{ name: "" }]);
  const [inst, setInst] = useState(course.installments?.length ? course.installments.map((i) => ({ ...i })) : []);
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));
  const sum = inst.reduce((a, i) => a + Number(i.amount || 0), 0);
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErr("");
    const body = { ...f, total_fee: Number(f.total_fee || 0), duration_weeks: Number(f.duration_weeks), trainer_id: f.trainer_id || null,
      modules: modules.filter((m) => m.name.trim()), installments: inst.map((i) => ({ ...i, amount: Number(i.amount || 0), due_after_days: Number(i.due_after_days || 0) })) };
    try {
      course.id ? await api.put(`/courses/${course.id}`, body) : await api.post("/courses", body);
      toast("Course saved"); onSaved();
    } catch (x) { setErr(errMsg(x)); } finally { setBusy(false); }
  };
  const upd = (arr, setArr, i, k, v) => setArr(arr.map((x, j) => (j === i ? { ...x, [k]: v } : x)));
  return (
    <Modal title={course.id ? "Edit course" : "New course"} onClose={onClose} wide>
      <form onSubmit={submit}>
        <ErrorBox msg={err} />
        <div className="form-grid">
          <Field label="Course code" required><input required value={f.code} onChange={set("code")} placeholder="e.g. WDEV" /></Field>
          <Field label="Course name" required><input required value={f.name} onChange={set("name")} /></Field>
          <Field label="Duration (weeks)" required><input type="number" min="1" required value={f.duration_weeks} onChange={set("duration_weeks")} /></Field>
          <Field label="Total course fee (KES)" required><input type="number" min="0" step="0.01" required value={f.total_fee} onChange={set("total_fee")} /></Field>
          <Field label="Lead trainer"><select value={f.trainer_id} onChange={set("trainer_id")}><option value="">None</option>{trainers?.items.filter((t) => t.is_active).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></Field>
          <Field label="Description" full><textarea rows="2" value={f.description} onChange={set("description")} /></Field>
        </div>
        <h2 style={{ marginTop: "1.2rem" }}>Course modules</h2>
        {modules.map((m, i) => (
          <div key={i} style={{ display: "flex", gap: ".5rem", marginBottom: ".5rem" }}>
            <span style={{ width: 24, paddingTop: ".6rem" }}>{i + 1}.</span>
            <input placeholder="Module name" value={m.name} onChange={(e) => upd(modules, setModules, i, "name", e.target.value)} />
            <button type="button" className="btn sm" onClick={() => setModules(modules.filter((_, j) => j !== i))}>✕</button>
          </div>))}
        <button type="button" className="btn sm" onClick={() => setModules([...modules, { name: "" }])}>+ Add module</button>
        <h2 style={{ marginTop: "1.2rem" }}>Fee structure (installments)</h2>
        <p className="muted" style={{ marginTop: 0 }}>Optional. If you add installments they must add up to the total fee. Leave empty for one full payment at registration.</p>
        {inst.map((i, k) => (
          <div key={k} style={{ display: "grid", gridTemplateColumns: "2fr 1.2fr 1.2fr auto", gap: ".5rem", marginBottom: ".5rem" }}>
            <input placeholder="Label (e.g. Deposit)" value={i.label} onChange={(e) => upd(inst, setInst, k, "label", e.target.value)} />
            <input type="number" min="0" placeholder="Amount" value={i.amount} onChange={(e) => upd(inst, setInst, k, "amount", e.target.value)} />
            <input type="number" min="0" placeholder="Due after (days)" title="Days after registration" value={i.due_after_days} onChange={(e) => upd(inst, setInst, k, "due_after_days", e.target.value)} />
            <button type="button" className="btn sm" onClick={() => setInst(inst.filter((_, j) => j !== k))}>✕</button>
          </div>))}
        <div style={{ display: "flex", gap: "1rem", alignItems: "center", flexWrap: "wrap" }}>
          <button type="button" className="btn sm" onClick={() => setInst([...inst, { label: `Installment ${inst.length + 1}`, amount: "", due_after_days: inst.length * 30 }])}>+ Add installment</button>
          {inst.length > 0 && <span className={sum === Number(f.total_fee) ? "badge green" : "badge red"}>Installments total {money(sum)} / {money(f.total_fee)}</span>}
        </div>
        <div className="form-actions"><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn primary" disabled={busy}>{busy ? "Saving…" : "Save course"}</button></div>
      </form>
    </Modal>
  );
}

function IntakeList() {
  const toast = useToast();
  const { data, loading, reload } = useApi("/intakes");
  const [edit, setEdit] = useState(null);
  const [del, setDel] = useState(null);
  const remove = async () => { try { await api.delete(`/intakes/${del.id}`); toast("Intake deleted"); reload(); } catch (e) { toast(errMsg(e), "err"); } setDel(null); };
  return (
    <>
      <div className="actions" style={{ marginBottom: "1rem" }}><button className="btn primary" onClick={() => setEdit({})}>+ New intake</button></div>
      <div className="card flush">
        {loading ? <Loading /> : !data.items.length ? <Empty>No intakes yet.</Empty> : (
          <div className="table-wrap"><table><thead><tr><th>Intake</th><th>Course</th><th>Start</th><th>End</th><th>Trainer</th><th>Students</th><th /></tr></thead>
            <tbody>{data.items.map((i) => <tr key={i.id}><td><b>{i.name}</b></td><td>{i.course_name}</td><td>{fdate(i.start_date)}</td><td>{fdate(i.end_date)}</td><td>{i.trainer_name || "—"}</td><td>{i.student_count}</td>
              <td><div className="row-actions"><button className="btn sm" onClick={() => setEdit(i)}>Edit</button><button className="btn sm" onClick={() => setDel(i)}>Delete</button></div></td></tr>)}</tbody></table></div>)}
      </div>
      {edit && <IntakeForm intake={edit} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); reload(); }} />}
      {del && <Confirm title="Delete intake" message={`Delete intake "${del.name}"?`} onYes={remove} onNo={() => setDel(null)} />}
    </>
  );
}

function IntakeForm({ intake, onClose, onSaved }) {
  const toast = useToast();
  const { data: courses } = useApi("/courses");
  const { data: trainers } = useApi("/users", { role: "trainer" });
  const [f, setF] = useState({ course_id: intake.course_id || "", name: intake.name || "", start_date: intake.start_date || "", end_date: intake.end_date || "", trainer_id: intake.trainer_id || "" });
  const [err, setErr] = useState("");
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));
  const submit = async (e) => {
    e.preventDefault();
    const body = { ...f, course_id: Number(f.course_id), trainer_id: f.trainer_id ? Number(f.trainer_id) : null, end_date: f.end_date || null };
    try { intake.id ? await api.put(`/intakes/${intake.id}`, body) : await api.post("/intakes", body); toast("Intake saved"); onSaved(); } catch (x) { setErr(errMsg(x)); }
  };
  return (
    <Modal title={intake.id ? "Edit intake" : "New intake"} onClose={onClose}>
      <form onSubmit={submit}><ErrorBox msg={err} /><div className="form-grid">
        <Field label="Course" required><select required value={f.course_id} onChange={set("course_id")}><option value="">Select…</option>{courses?.items.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
        <Field label="Intake name" required><input required placeholder="e.g. January 2027" value={f.name} onChange={set("name")} /></Field>
        <Field label="Start date" required><input type="date" required value={f.start_date} onChange={set("start_date")} /></Field>
        <Field label="End date"><input type="date" value={f.end_date} onChange={set("end_date")} /></Field>
        <Field label="Assigned trainer"><select value={f.trainer_id} onChange={set("trainer_id")}><option value="">None</option>{trainers?.items.filter((t) => t.is_active).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></Field>
      </div><div className="form-actions"><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn primary">Save intake</button></div></form>
    </Modal>
  );
}
