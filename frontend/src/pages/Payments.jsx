import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { errMsg, printPdf, viewPdf, downloadFile } from "../api";
import PaymentForm from "../components/PaymentForm.jsx";
import { Empty, ErrorBox, Loading, PageHeader, Pagination, fdate, money, useApi, useDebounce, useToast } from "../components/ui.jsx";

export default function Payments() {
  const toast = useToast();
  const [sp] = useSearchParams();
  const [q, setQ] = useState("");
  const [method, setMethod] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [page, setPage] = useState(1);
  const [form, setForm] = useState(sp.get("new") ? {} : null);
  const dq = useDebounce(q);
  const { data, loading, error, reload } = useApi("/payments", { q: dq, method: method || undefined, date_from: from || undefined, date_to: to || undefined, page });
  const act = (fn) => fn().catch((e) => toast(errMsg(e), "err"));
  const reset = (fn) => (e) => { fn(e.target.value); setPage(1); };
  return (
    <>
      <PageHeader title="Payments" sub="Record, search and reprint receipts"><button className="btn primary" onClick={() => setForm({})}>+ Record payment</button></PageHeader>
      <div className="filters">
        <input className="grow" placeholder="Search receipt no., M-Pesa code, student name/number/phone…" value={q} onChange={reset(setQ)} />
        <select value={method} onChange={reset(setMethod)}><option value="">All methods</option>{["M-Pesa", "Cash", "Bank Transfer", "Cheque", "Card"].map((m) => <option key={m}>{m}</option>)}</select>
        <input type="date" value={from} onChange={reset(setFrom)} title="From" /><input type="date" value={to} onChange={reset(setTo)} title="To" />
      </div>
      <ErrorBox msg={error} />
      <div className="card flush">
        {data && <div className="card-head"><span className="muted">{data.total} payment(s)</span><b>Total: {money(data.total_amount)}</b></div>}
        {loading ? <Loading /> : !data.items.length ? <Empty>No payments found.</Empty> : (
          <div className="table-wrap"><table><thead><tr><th>Receipt</th><th>Date</th><th>Student</th><th>Method</th><th>M-Pesa code</th><th className="right">Amount</th><th /></tr></thead>
            <tbody>{data.items.map((p) => <tr key={p.id}><td><b>{p.receipt_number}</b></td><td>{fdate(p.payment_date)}</td><td>{p.student_name}<br /><small className="muted">{p.student_number} · {p.course_name}</small></td><td>{p.method}</td><td>{p.mpesa_code || "—"}</td><td className="right">{money(p.amount)}</td>
              <td><div className="row-actions">
                <button className="btn sm" onClick={() => act(() => viewPdf(`/payments/${p.id}/receipt`))}>View</button>
                <button className="btn sm" onClick={() => act(() => downloadFile(`/payments/${p.id}/receipt`, `${p.receipt_number}.pdf`, { download: 1 }))}>Download</button>
                <button className="btn sm" onClick={() => act(() => printPdf(`/payments/${p.id}/receipt`))}>Print</button>
                <button className="btn sm" onClick={() => setForm(p)}>Edit</button></div></td></tr>)}</tbody></table></div>)}
        <Pagination meta={data} onPage={setPage} />
      </div>
      {form && <PaymentForm payment={form.id ? form : null} onClose={() => setForm(null)} onSaved={reload} />}
    </>
  );
}
