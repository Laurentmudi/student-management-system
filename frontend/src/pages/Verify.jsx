import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api from "../api";
import { LogoImg, fdate, money } from "../components/ui.jsx";

// Public page opened when someone scans the QR code on a receipt or certificate.
export default function Verify() {
  const { kind, number } = useParams();
  const [d, setD] = useState(null);
  const [bad, setBad] = useState(false);
  useEffect(() => {
    api.get(`/public/verify/${kind}/${number}`).then((r) => setD(r.data)).catch(() => setBad(true));
  }, [kind, number]);
  return (
    <div className="auth-wrap">
      <div className="auth-card" style={{ maxWidth: 480 }}>
        <LogoImg />
        <h1>{kind === "certificate" ? "Certificate Verification" : "Receipt Verification"}</h1>
        <p className="muted">{number}</p>
        {!d && !bad && <p>Checking…</p>}
        {bad && <div className="alert err"><b>Not found.</b> This {kind} number is not in our records. It may be forged.</div>}
        {d && kind === "certificate" && (
          <div className="verify-ok">
            <b style={{ color: "#166534" }}>✔ Valid certificate issued by {d.academy}</b>
            <p style={{ textAlign: "left" }}>Awarded to <b>{d.student_name}</b><br />Course: <b>{d.course}</b><br />Completed: {fdate(d.completion_date)}<br />Issued: {fdate(d.issue_date)}</p>
          </div>
        )}
        {d && kind === "receipt" && (
          <div className="verify-ok">
            <b style={{ color: "#166534" }}>✔ Genuine receipt issued by {d.academy}</b>
            <p style={{ textAlign: "left" }}>Student: <b>{d.student_name}</b><br />Amount: <b>{money(d.amount)}</b><br />Date: {fdate(d.payment_date)}</p>
          </div>
        )}
      </div>
    </div>
  );
}
