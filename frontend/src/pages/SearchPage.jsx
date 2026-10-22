import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { Badge, Empty, Loading, PageHeader, fdate, money, useApi } from "../components/ui.jsx";

export default function SearchPage() {
  const [sp] = useSearchParams();
  const q = sp.get("q") || "";
  const { isAdmin } = useAuth();
  const { data, loading } = useApi("/search", { q });
  if (loading) return <Loading />;
  const none = !data.students.length && !data.payments.length && !data.certificates.length;
  return (
    <>
      <PageHeader title={`Search: “${q}”`} />
      {none && <div className="card"><Empty>No results found.</Empty></div>}
      {data.students.length > 0 && <div className="card flush"><div className="card-head"><h2>Students</h2></div><div className="table-wrap"><table><thead><tr><th>Name</th><th>Number</th><th>Phone</th><th>Course</th><th>Status</th></tr></thead>
        <tbody>{data.students.map((s) => <tr key={s.id}><td><Link to={`/students/${s.id}`}>{s.name}</Link></td><td>{s.student_number}</td><td>{s.phone}</td><td>{s.course_name}</td><td><Badge text={s.status} /></td></tr>)}</tbody></table></div></div>}
      {isAdmin && data.payments.length > 0 && <div className="card flush"><div className="card-head"><h2>Payments</h2></div><div className="table-wrap"><table><thead><tr><th>Receipt</th><th>M-Pesa code</th><th>Student</th><th>Date</th><th className="right">Amount</th></tr></thead>
        <tbody>{data.payments.map((p) => <tr key={p.id}><td><Link to={`/students/${p.student_id}?tab=payments`}>{p.receipt_number}</Link></td><td>{p.mpesa_code || "—"}</td><td>{p.student_name}</td><td>{fdate(p.payment_date)}</td><td className="right">{money(p.amount)}</td></tr>)}</tbody></table></div></div>}
      {isAdmin && data.certificates.length > 0 && <div className="card flush"><div className="card-head"><h2>Certificates</h2></div><div className="table-wrap"><table><thead><tr><th>Certificate no.</th><th>Student</th></tr></thead>
        <tbody>{data.certificates.map((c) => <tr key={c.id}><td><Link to="/certificates">{c.certificate_number}</Link></td><td>{c.student_name}</td></tr>)}</tbody></table></div></div>}
    </>
  );
}
