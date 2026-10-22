import { useState } from "react";
import api, { downloadFile, errMsg, printPdf, viewPdf } from "../api";
import { Empty, Loading, PageHeader, Pagination, fdate, useApi, useDebounce, useToast } from "../components/ui.jsx";

export default function Certificates() {
  const toast = useToast();
  const [tab, setTab] = useState("eligible");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const dq = useDebounce(q);
  const elig = useApi("/certificates/eligible");
  const issued = useApi("/certificates", { q: dq, page });
  const act = (fn) => fn().catch((e) => toast(errMsg(e), "err"));
  const generate = async (s) => {
    try { const r = await api.post("/certificates", { student_id: s.id }); toast(`Certificate ${r.data.certificate.certificate_number} generated`); elig.reload(); issued.reload(); setTab("issued"); }
    catch (e) { toast(errMsg(e), "err"); }
  };
  return (
    <>
      <PageHeader title="Certificates" sub="Only students with status Cleared (Completed) are eligible" />
      <div className="tabs">
        <button className={tab === "eligible" ? "on" : ""} onClick={() => setTab("eligible")}>Ready to issue {elig.data ? `(${elig.data.items.length})` : ""}</button>
        <button className={tab === "issued" ? "on" : ""} onClick={() => setTab("issued")}>Issued certificates</button>
      </div>
      {tab === "eligible" ? (
        <div className="card flush">
          {elig.loading ? <Loading /> : !elig.data.items.length ? <Empty>No completed students are waiting for a certificate.</Empty> : (
            <div className="table-wrap"><table><thead><tr><th>Student</th><th>Course</th><th>Completed</th><th /></tr></thead>
              <tbody>{elig.data.items.map((s) => <tr key={s.id}><td><b>{s.name}</b><br /><small className="muted">{s.student_number}</small></td><td>{s.course_name}</td><td>{fdate(s.completed_on)}</td><td><button className="btn primary sm" onClick={() => generate(s)}>Generate certificate</button></td></tr>)}</tbody></table></div>)}
        </div>
      ) : (
        <>
          <div className="filters"><input className="grow" placeholder="Search certificate no., student name or number…" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} /></div>
          <div className="card flush">
            {issued.loading ? <Loading /> : !issued.data.items.length ? <Empty>No certificates issued yet.</Empty> : (
              <div className="table-wrap"><table><thead><tr><th>Certificate no.</th><th>Student</th><th>Course</th><th>Completed</th><th>Issued</th><th /></tr></thead>
                <tbody>{issued.data.items.map((c) => <tr key={c.id}><td><b>{c.certificate_number}</b></td><td>{c.student_name}<br /><small className="muted">{c.student_number}</small></td><td>{c.course_name}</td><td>{fdate(c.completion_date)}</td><td>{fdate(c.issue_date)}</td>
                  <td><div className="row-actions">
                    <button className="btn sm" onClick={() => act(() => viewPdf(`/certificates/${c.id}/pdf`))}>View</button>
                    <button className="btn sm" onClick={() => act(() => downloadFile(`/certificates/${c.id}/pdf`, `${c.certificate_number}.pdf`, { download: 1 }))}>Download</button>
                    <button className="btn sm" onClick={() => act(() => printPdf(`/certificates/${c.id}/pdf`))}>Print / Reprint</button></div></td></tr>)}</tbody></table></div>)}
            <Pagination meta={issued.data} onPage={setPage} />
          </div>
        </>
      )}
    </>
  );
}
