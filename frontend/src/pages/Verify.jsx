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

  const Row = ({ label, value }) => (
    <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", padding: ".55rem 0", borderTop: "1px solid #eeeeee" }}>
      <span style={{ color: "#666666" }}>{label}</span>
      <b style={{ textAlign: "right" }}>{value}</b>
    </div>
  );

  return (
    <div className="auth-wrap">
      <div className="auth-card" style={{ maxWidth: 480 }}>
        <LogoImg />
        <h1>{kind === "certificate" ? "Certificate Verification" : "Receipt Verification"}</h1>
        <p className="muted">{d?.display_number || number}</p>
        {!d && !bad && <p>Checking...</p>}
        {bad && (
          <div className="alert err">
            <i className="bi bi-x-circle-fill"></i> <b>Not found.</b> This {kind} number is not in our records. It may be forged.
          </div>
        )}
        {d && kind === "certificate" && (
          <div className="verify-ok">
            <div style={{ display: "flex", alignItems: "center", gap: ".6rem", marginBottom: ".8rem" }}>
              <i className="bi bi-patch-check-fill" style={{ fontSize: "1.8rem", color: "#F7B500" }}></i>
              <div>
                <b style={{ color: "#1D2245", fontSize: "1.05rem" }}>Valid certificate</b>
                <div style={{ color: "#666666", fontSize: ".85rem" }}>Issued by {d.academy}</div>
              </div>
            </div>
            <div style={{ textAlign: "center", padding: ".6rem 0 1rem" }}>
              <div style={{ color: "#666666", fontSize: ".8rem", textTransform: "uppercase", letterSpacing: ".08em" }}>Awarded to</div>
              <div style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontStyle: "italic", fontWeight: 700, fontSize: "1.7rem", color: "#1D2245" }}>{d.student_name}</div>
              <div style={{ height: 3, width: 70, background: "#F7B500", margin: ".5rem auto 0", borderRadius: 2 }}></div>
            </div>
            <Row label="Course" value={d.course} />
            <Row label="Completed" value={fdate(d.completion_date)} />
            <Row label="Issued" value={fdate(d.issue_date)} />
            <Row label="Certificate No." value={d.display_number || d.certificate_number} />
          </div>
        )}
        {d && kind === "receipt" && (
          <div className="verify-ok">
            <div style={{ display: "flex", alignItems: "center", gap: ".6rem", marginBottom: ".8rem" }}>
              <i className="bi bi-patch-check-fill" style={{ fontSize: "1.8rem", color: "#F7B500" }}></i>
              <div>
                <b style={{ color: "#1D2245", fontSize: "1.05rem" }}>Genuine receipt</b>
                <div style={{ color: "#666666", fontSize: ".85rem" }}>Issued by {d.academy}</div>
              </div>
            </div>
            <Row label="Student" value={d.student_name} />
            <Row label="Amount" value={money(d.amount)} />
            <Row label="Date" value={fdate(d.payment_date)} />
            <Row label="Receipt No." value={d.receipt_number} />
          </div>
        )}
      </div>
    </div>
  );
}
