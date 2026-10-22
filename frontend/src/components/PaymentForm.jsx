import { useEffect, useState } from "react";
import api, { errMsg, printPdf, viewPdf } from "../api";
import { ErrorBox, Field, Modal, money, useDebounce, useToast } from "./ui.jsx";

const METHODS = ["M-Pesa", "Cash", "Bank Transfer", "Cheque", "Card"];

// Used from the Payments page (student picker) and from a student's profile (student fixed).
export default function PaymentForm({ payment, student: fixed, onClose, onSaved }) {
  const toast = useToast();
  const today = new Date().toISOString().slice(0, 10);
  const [student, setStudent] = useState(fixed || null);
  const [fees, setFees] = useState(null);
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const dq = useDebounce(q);
  const [f, setF] = useState({ amount: payment?.amount ?? "", method: payment?.method ?? "M-Pesa", mpesa_code: payment?.mpesa_code ?? "", payment_date: payment?.payment_date ?? today, notes: payment?.notes ?? "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(null);

  useEffect(() => {
    if (student || dq.length < 2) { setResults([]); return; }
    api.get("/students", { params: { q: dq, per_page: 8 } }).then((r) => setResults(r.data.items));
  }, [dq, student]);
  useEffect(() => {
    const sid = student?.id || payment?.student_id;
    if (sid) api.get(`/students/${sid}/fees`).then((r) => setFees(r.data.fees));
  }, [student, payment]);

  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const body = { ...f, amount: Number(f.amount), student_id: student?.id || payment.student_id };
      const r = payment ? await api.put(`/payments/${payment.id}`, body) : await api.post("/payments", body);
      toast(payment ? "Payment updated" : `Payment recorded · ${r.data.payment.receipt_number}`);
      onSaved?.();
      if (payment) onClose(); else setSaved(r.data.payment);
    } catch (x) { setErr(errMsg(x)); } finally { setBusy(false); }
  };

  if (saved) return (
    <Modal title="Payment recorded ✔" onClose={onClose}>
      <p>Receipt <b>{saved.receipt_number}</b> for <b>{money(saved.amount)}</b> has been generated.</p>
      <div className="form-actions" style={{ justifyContent: "flex-start" }}>
        <button className="btn primary" onClick={() => viewPdf(`/payments/${saved.id}/receipt`).catch((e) => toast(errMsg(e), "err"))}>Open / Download receipt</button>
        <button className="btn" onClick={() => printPdf(`/payments/${saved.id}/receipt`).catch((e) => toast(errMsg(e), "err"))}>Print</button>
        <button className="btn" onClick={onClose}>Done</button>
      </div>
    </Modal>
  );

  const left = fees ? fees.balance + (payment ? payment.amount : 0) : null;
  return (
    <Modal title={payment ? `Edit payment ${payment.receipt_number}` : "Record payment"} onClose={onClose}>
      <form onSubmit={submit}>
        <ErrorBox msg={err} />
        {!student && !payment && (
          <Field label="Student" required hint="Search by name, student number or phone">
            <input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Start typing…" />
            {results.length > 0 && <div className="card flush" style={{ margin: 0 }}>{results.map((s) => (
              <div key={s.id} className="notif" onClick={() => setStudent(s)}><div><b>{s.full_name}</b> <small className="muted">{s.student_number}</small><br /><small className="muted">{s.course_name} · balance {money(s.balance)}</small></div></div>))}</div>}
          </Field>
        )}
        {(student || payment) && (
          <div className="alert info" style={{ display: "flex", justifyContent: "space-between", gap: ".5rem", flexWrap: "wrap" }}>
            <span><b>{student?.full_name || payment.student_name}</b> · {student?.student_number || payment.student_number}</span>
            {fees && <span>Payable {money(fees.total_payable)} · Paid {money(fees.total_paid)} · <b>Balance {money(fees.balance)}</b></span>}
            {!fixed && !payment && <button type="button" className="btn sm" onClick={() => setStudent(null)}>Change</button>}
          </div>
        )}
        {(student || payment) && (<>
          <div className="form-grid">
            <Field label="Amount paid (KES)" required hint={left != null ? `Maximum ${money(left)}` : ""}><input type="number" required min="1" step="0.01" max={left ?? undefined} value={f.amount} onChange={set("amount")} /></Field>
            <Field label="Payment date" required><input type="date" required max={today} value={f.payment_date} onChange={set("payment_date")} /></Field>
            <Field label="Payment method" required><select value={f.method} onChange={set("method")}>{METHODS.map((m) => <option key={m}>{m}</option>)}</select></Field>
            <Field label="M-Pesa transaction code" required={f.method === "M-Pesa"}><input value={f.mpesa_code} onChange={set("mpesa_code")} required={f.method === "M-Pesa"} placeholder="e.g. QJK7H2ABCD" style={{ textTransform: "uppercase" }} /></Field>
            <Field label="Notes" full><input value={f.notes} onChange={set("notes")} /></Field>
          </div>
          <div className="form-actions"><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn primary" disabled={busy}>{busy ? "Saving…" : payment ? "Save changes" : "Record & generate receipt"}</button></div>
        </>)}
      </form>
    </Modal>
  );
}
