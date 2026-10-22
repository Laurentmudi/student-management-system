import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { Avatar, Badge, Empty, ErrorBox, Loading, PageHeader, Pagination, Progress, money, useApi, useDebounce } from "../components/ui.jsx";

export default function Students() {
  const { isAdmin } = useAuth();
  const [sp] = useSearchParams();
  const [q, setQ] = useState(sp.get("q") || "");
  const [course, setCourse] = useState("");
  const [status, setStatus] = useState("");
  const [trainer, setTrainer] = useState("");
  const [page, setPage] = useState(1);
  const dq = useDebounce(q);
  const { data: courses } = useApi("/courses");
  const { data: trainers } = useApi(isAdmin ? "/users" : null, { role: "trainer" });
  const { data, loading, error } = useApi("/students", { q: dq, course_id: course || undefined, status: status || undefined, trainer_id: trainer || undefined, page });
  const reset = (fn) => (e) => { fn(e.target.value); setPage(1); };
  return (
    <>
      <PageHeader title={isAdmin ? "Students" : "My Students"} sub={isAdmin ? "Register and manage all students" : "Students assigned to you"}>
        {isAdmin && <Link className="btn primary" to="/students/new">+ Register student</Link>}
      </PageHeader>
      <div className="filters">
        <input className="grow" placeholder="Search name, student no., phone, course…" value={q} onChange={reset(setQ)} />
        <select value={course} onChange={reset(setCourse)}><option value="">All courses</option>{courses?.items.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select>
        <select value={status} onChange={reset(setStatus)}><option value="">All statuses</option>{["Active", "In Progress", "Cleared (Completed)", "Suspended", "Withdrawn"].map((s) => <option key={s}>{s}</option>)}</select>
        {isAdmin && <select value={trainer} onChange={reset(setTrainer)}><option value="">All trainers</option>{trainers?.items?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select>}
      </div>
      <ErrorBox msg={error} />
      <div className="card flush">
        {loading ? <Loading /> : !data?.items.length ? <Empty>No students match your search.</Empty> : (
          <div className="table-wrap"><table>
            <thead><tr><th>Student</th><th>Course / Intake</th><th>Phone</th><th>Status</th><th>Progress</th>{isAdmin && <th className="right">Balance</th>}<th /></tr></thead>
            <tbody>{data.items.map((s) => (
              <tr key={s.id}>
                <td><div className="person"><Avatar photo={s.photo} name={s.full_name} /><div><b><Link to={`/students/${s.id}`}>{s.full_name}</Link></b><small>{s.student_number}</small></div></div></td>
                <td>{s.course_name}<br /><small className="muted">{s.intake_name || "No intake"}</small></td>
                <td className="nowrap">{s.phone}</td>
                <td><Badge text={s.status} /></td>
                <td style={{ minWidth: 130 }}><Progress value={s.progress.percent} small /></td>
                {isAdmin && <td className="right nowrap" style={{ color: s.balance > 0 ? "var(--red)" : "var(--green)", fontWeight: 600 }}>{money(s.balance)}</td>}
                <td><div className="row-actions"><Link className="btn sm" to={`/students/${s.id}`}>Open</Link>{isAdmin && <Link className="btn sm" to={`/students/${s.id}/edit`}>Edit</Link>}</div></td>
              </tr>))}</tbody>
          </table></div>
        )}
        <Pagination meta={data} onPage={setPage} />
      </div>
    </>
  );
}
