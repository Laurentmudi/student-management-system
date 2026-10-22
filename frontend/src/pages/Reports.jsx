import { useState } from "react";
import api, { downloadFile, errMsg } from "../api";
import { Empty, ErrorBox, Loading, PageHeader, useApi, useToast } from "../components/ui.jsx";

const USES = {
  students: ["course_id", "intake_id", "status"], "fee-collection": ["date_from", "date_to"], outstanding: ["course_id", "intake_id"],
  "payment-history": ["course_id", "date_from", "date_to"], attendance: ["course_id", "intake_id", "date_from", "date_to"],
  progress: ["course_id", "intake_id", "status"], enrolment: ["course_id"], completion: ["course_id", "intake_id"], certificates: ["course_id", "date_from", "date_to"],
};

export default function Reports() {
  const toast = useToast();
  const { data: list } = useApi("/reports");
  const { data: courses } = useApi("/courses");
  const { data: intakes } = useApi("/intakes");
  const [key, setKey] = useState("students");
  const [f, setF] = useState({});
  const [res, setRes] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const uses = USES[key] || [];
  const params = Object.fromEntries(Object.entries(f).filter(([k, v]) => v && uses.includes(k)));
  const run = async () => {
    setLoading(true); setErr("");
    try { setRes((await api.get(`/reports/${key}`, { params })).data); } catch (e) { setErr(errMsg(e)); } finally { setLoading(false); }
  };
  const dl = (fmt) => downloadFile(`/reports/${key}`, `${key}.${fmt === "pdf" ? "pdf" : "xlsx"}`, { ...params, format: fmt }).catch((e) => toast(errMsg(e), "err"));
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));
  return (
    <>
      <PageHeader title="Reports" sub="Generate on screen, or download as PDF / Excel" />
      <div className="report-cards">{list?.items.map((r) => <button key={r.key} className={`report-card ${key === r.key ? "on" : ""}`} onClick={() => { setKey(r.key); setRes(null); }}>{r.title}</button>)}</div>
      <div className="card">
        <div className="filters" style={{ marginBottom: 0 }}>
          {uses.includes("course_id") && <select value={f.course_id || ""} onChange={set("course_id")}><option value="">All courses</option>{courses?.items.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select>}
          {uses.includes("intake_id") && <select value={f.intake_id || ""} onChange={set("intake_id")}><option value="">All intakes</option>{intakes?.items.filter((i) => !f.course_id || String(i.course_id) === String(f.course_id)).map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}</select>}
          {uses.includes("status") && <select value={f.status || ""} onChange={set("status")}><option value="">All statuses</option>{["Active", "In Progress", "Cleared (Completed)", "Suspended", "Withdrawn"].map((s) => <option key={s}>{s}</option>)}</select>}
          {uses.includes("date_from") && <input type="date" value={f.date_from || ""} onChange={set("date_from")} title="From date" />}
          {uses.includes("date_to") && <input type="date" value={f.date_to || ""} onChange={set("date_to")} title="To date" />}
          <button className="btn primary" style={{ flex: "0 0 auto" }} onClick={run}>Generate</button>
          <button className="btn" style={{ flex: "0 0 auto" }} onClick={() => dl("pdf")}>⬇ PDF</button>
          <button className="btn" style={{ flex: "0 0 auto" }} onClick={() => dl("xlsx")}>⬇ Excel</button>
        </div>
      </div>
      <ErrorBox msg={err} />
      {loading ? <Loading /> : res && (
        <div className="card flush">
          <div className="card-head"><h2>{res.title}</h2><span className="muted">{Object.entries(res.summary || {}).map(([k, v]) => `${k}: ${v}`).join("  ·  ")}</span></div>
          {!res.rows.length ? <Empty>No records for these filters.</Empty> : (
            <div className="table-wrap"><table><thead><tr>{res.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
              <tbody>{res.rows.map((r, i) => <tr key={i}>{r.map((v, j) => <td key={j}>{v === "" || v == null ? "—" : String(v)}</td>)}</tr>)}</tbody></table></div>)}
        </div>)}
    </>
  );
}
