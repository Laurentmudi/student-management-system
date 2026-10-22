import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Empty, Loading, PageHeader, Pagination, Progress, useApi, useDebounce } from "../components/ui.jsx";

export default function ProgressPage() {
  const [q, setQ] = useState("");
  const [course, setCourse] = useState("");
  const [page, setPage] = useState(1);
  const dq = useDebounce(q);
  const { data: courses } = useApi("/courses");
  const { data, loading } = useApi("/progress/overview", { q: dq, course_id: course || undefined, page });
  return (
    <>
      <PageHeader title="Student Progress" sub="Modules completed, remaining and overall percentage" />
      <div className="filters">
        <input className="grow" placeholder="Search student…" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
        <select value={course} onChange={(e) => { setCourse(e.target.value); setPage(1); }}><option value="">All courses</option>{courses?.items.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select>
      </div>
      <div className="card flush">
        {loading ? <Loading /> : !data.items.length ? <Empty>No students to show.</Empty> : (
          <div className="table-wrap"><table><thead><tr><th>Student</th><th>Course</th><th>Completed</th><th>Remaining</th><th>Progress</th><th>Status</th><th /></tr></thead>
            <tbody>{data.items.map((s) => <tr key={s.id}><td><b>{s.name}</b><br /><small className="muted">{s.student_number}</small></td><td>{s.course_name}</td><td>{s.completed}</td><td>{s.remaining}</td>
              <td style={{ minWidth: 150 }}><Progress value={s.percent} small /></td><td><Badge text={s.status} />{s.behind && <> <span className="badge red">Behind</span></>}</td>
              <td><Link className="btn sm" to={`/students/${s.id}?tab=progress`}>Update</Link></td></tr>)}</tbody></table></div>)}
        <Pagination meta={data} onPage={setPage} />
      </div>
    </>
  );
}
