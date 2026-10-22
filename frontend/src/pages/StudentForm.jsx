import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api, { errMsg } from "../api";
import { ErrorBox, Field, Loading, PageHeader, useApi, useToast } from "../components/ui.jsx";

const EMPTY = { first_name: "", last_name: "", gender: "", date_of_birth: "", national_id: "", phone: "", alt_phone: "", email: "", address: "",
  guardian_name: "", guardian_relationship: "", guardian_phone: "", course_id: "", intake_id: "", trainer_id: "",
  registration_date: new Date().toISOString().slice(0, 10), expected_completion: "", status: "Active", fee_payable: "" };

export default function StudentForm() {
  const { id } = useParams();
  const nav = useNavigate();
  const toast = useToast();
  const [f, setF] = useState(EMPTY);
  const [files, setFiles] = useState({});
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(!id);
  const { data: courses } = useApi("/courses");
  const { data: intakes } = useApi("/intakes");
  const { data: trainers } = useApi("/users", { role: "trainer" });
  const [existing, setExisting] = useState(null);

  useEffect(() => {
    if (!id) return;
    api.get(`/students/${id}`).then((r) => {
      const s = r.data.student;
      setExisting(s);
      setF({ ...EMPTY, ...Object.fromEntries(Object.keys(EMPTY).map((k) => [k, s[k] ?? ""])), fee_payable: s.fee_payable ?? "" });
      setLoaded(true);
    }).catch((e) => setErr(errMsg(e)));
  }, [id]);

  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));
  const course = courses?.items.find((c) => String(c.id) === String(f.course_id));
  const courseIntakes = intakes?.items.filter((i) => String(i.course_id) === String(f.course_id)) || [];

  const onCourse = (e) => {
    const c = courses.items.find((x) => String(x.id) === e.target.value);
    setF((x) => ({ ...x, course_id: e.target.value, intake_id: "", fee_payable: c ? c.total_fee : "", trainer_id: x.trainer_id || c?.trainer_id || "" }));
  };
  const onIntake = (e) => {
    const i = intakes.items.find((x) => String(x.id) === e.target.value);
    setF((x) => ({ ...x, intake_id: e.target.value, trainer_id: i?.trainer_id || x.trainer_id }));
  };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    const fd = new FormData();
    Object.entries(f).forEach(([k, v]) => { if (v !== "" && v != null) fd.append(k, v); });
    Object.entries(files).forEach(([k, v]) => v && fd.append(k, v));
    try {
      const r = id ? await api.put(`/students/${id}`, fd) : await api.post("/students", fd);
      toast(id ? "Student updated" : `Student registered: ${r.data.student.student_number}`);
      nav(`/students/${r.data.student.id}`);
    } catch (x) { setErr(errMsg(x)); window.scrollTo({ top: 0, behavior: "smooth" }); }
    finally { setBusy(false); }
  };

  if (!loaded || !courses || !intakes || !trainers) return err ? <ErrorBox msg={err} /> : <Loading />;
  const file = (k, accept) => <input type="file" accept={accept} onChange={(e) => setFiles((x) => ({ ...x, [k]: e.target.files[0] }))} />;
  return (
    <form onSubmit={submit}>
      <PageHeader title={id ? `Edit ${existing?.full_name}` : "Register Student"} sub={id ? existing?.student_number : "Student number is generated automatically"} />
      <ErrorBox msg={err} />
      <fieldset><legend>Personal details</legend><div className="form-grid">
        <Field label="First name" required><input required value={f.first_name} onChange={set("first_name")} /></Field>
        <Field label="Last name" required><input required value={f.last_name} onChange={set("last_name")} /></Field>
        <Field label="Gender"><select value={f.gender} onChange={set("gender")}><option value="">Select…</option><option>Male</option><option>Female</option><option>Other</option></select></Field>
        <Field label="Date of birth"><input type="date" max={new Date().toISOString().slice(0, 10)} value={f.date_of_birth} onChange={set("date_of_birth")} /></Field>
        <Field label="National ID number"><input value={f.national_id} onChange={set("national_id")} /></Field>
        <Field label="Passport photo" hint={existing?.photo ? "A photo exists — choose a file to replace it" : "JPG / PNG"}>{file("photo", "image/*")}</Field>
      </div></fieldset>
      <fieldset><legend>Contact details</legend><div className="form-grid">
        <Field label="Phone number" required hint="Used for SMS / WhatsApp reminders"><input required placeholder="07XX XXX XXX" value={f.phone} onChange={set("phone")} /></Field>
        <Field label="Alternative phone"><input value={f.alt_phone} onChange={set("alt_phone")} /></Field>
        <Field label="Email address"><input type="email" value={f.email} onChange={set("email")} /></Field>
        <Field label="Physical address"><input value={f.address} onChange={set("address")} /></Field>
      </div></fieldset>
      <fieldset><legend>Parent / Guardian</legend><div className="form-grid">
        <Field label="Name"><input value={f.guardian_name} onChange={set("guardian_name")} /></Field>
        <Field label="Relationship"><input placeholder="e.g. Mother" value={f.guardian_relationship} onChange={set("guardian_relationship")} /></Field>
        <Field label="Phone number"><input value={f.guardian_phone} onChange={set("guardian_phone")} /></Field>
      </div></fieldset>
      <fieldset><legend>Academic details</legend><div className="form-grid">
        <Field label="Course" required><select required value={f.course_id} onChange={onCourse}><option value="">Select course…</option>{courses.items.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
        <Field label="Intake"><select value={f.intake_id} onChange={onIntake} disabled={!f.course_id}><option value="">{f.course_id ? "No intake" : "Select a course first"}</option>{courseIntakes.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}</select></Field>
        <Field label="Assigned trainer"><select value={f.trainer_id} onChange={set("trainer_id")}><option value="">Auto (intake / course trainer)</option>{trainers.items.filter((t) => t.is_active).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></Field>
        <Field label="Registration date"><input type="date" value={f.registration_date} onChange={set("registration_date")} /></Field>
        <Field label="Expected completion" hint={course ? `Defaults to ${course.duration_weeks} weeks after registration` : ""}><input type="date" value={f.expected_completion} onChange={set("expected_completion")} /></Field>
        {id && <Field label="Student status" hint="Progress moves Active → In Progress → Cleared automatically. Set Suspended/Withdrawn manually."><select value={f.status} onChange={set("status")}>{["Active", "In Progress", "Cleared (Completed)", "Suspended", "Withdrawn"].map((s) => <option key={s}>{s}</option>)}</select></Field>}
        <Field label="Fee payable (KES)" hint="Defaults to the course fee. Change only for discounts/scholarships."><input type="number" min="0" step="0.01" value={f.fee_payable} onChange={set("fee_payable")} /></Field>
      </div></fieldset>
      <fieldset><legend>Student documents</legend><div className="form-grid">
        <Field label="National ID (front)" hint={existing?.has_id_front ? "Uploaded — choose a file to replace" : "Image or PDF"}>{file("id_front", "image/*,.pdf")}</Field>
        <Field label="National ID (back)" hint={existing?.has_id_back ? "Uploaded — choose a file to replace" : "Image or PDF"}>{file("id_back", "image/*,.pdf")}</Field>
      </div></fieldset>
      <div className="form-actions"><button type="button" className="btn" onClick={() => nav(-1)}>Cancel</button><button className="btn primary" disabled={busy}>{busy ? "Saving…" : id ? "Save changes" : "Register student"}</button></div>
    </form>
  );
}
